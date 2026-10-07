"""Leitura de CSV (funções puras de importacao_csv.py)."""
import unittest
from datetime import date

from importacao_csv import (CONTAR_LINHAS, ErroCsv, converter_data, converter_numero, converter_registros,
                            ler_csv, sugerir_mapeamento, validar_mapeamento)

# Exportação típica do Gerenciador de Anúncios da Meta em português (separador ;, números brasileiros).
CSV_META = (
    "Início dos relatórios;Término dos relatórios;Nome do anúncio;Valor usado (BRL);Impressões;"
    "Cliques no link;CPC (custo por clique no link) (BRL);Visualizações da página de destino;"
    "Adições ao carrinho;Compras;Valor de conversão de compras\n"
    "2026-10-01;2026-10-01;Anúncio A;15,50;2.500;40;0,39;30;3;1;200,00\n"
    "2026-10-01;2026-10-01;Anúncio B;14,50;2.500;35;0,41;25;2;0;0\n"
    "2026-10-02;2026-10-02;Anúncio A;30,00;5.000;80;0,38;60;4;1;200,00\n"
    ";;Total;60,00;10.000;155;;115;9;2;400,00\n"
)


class TestLerCsv(unittest.TestCase):

    def test_le_csv_com_ponto_e_virgula(self):
        colunas, registros = ler_csv(CSV_META.encode("utf-8"))
        self.assertEqual(colunas[0], "Início dos relatórios")
        self.assertEqual(len(registros), 4)
        self.assertEqual(registros[0][0], 2)  # número da linha no arquivo
        self.assertEqual(registros[0][1]["Valor usado (BRL)"], "15,50")

    def test_le_csv_do_excel_em_latin1_com_virgula(self):
        conteudo = "Data,Vendas,Receita\n06/10/2026,2,\"350,00\"\n".encode("latin-1")
        colunas, registros = ler_csv(conteudo)
        self.assertEqual(colunas, ["Data", "Vendas", "Receita"])
        self.assertEqual(registros[0][1]["Receita"], "350,00")

    def test_acentos_em_latin1(self):
        colunas, _ = ler_csv("Dia;Impressões\n2026-10-01;10\n".encode("latin-1"))
        self.assertEqual(colunas[1], "Impressões")

    def test_ignora_linhas_em_branco_e_nomeia_colunas_vazias_ou_repetidas(self):
        colunas, registros = ler_csv(b"Data;;Data\n2026-10-01;1;2\n;;\n\n2026-10-02;3;4\n")
        self.assertEqual(colunas, ["Data", "Coluna 2", "Data (2)"])
        self.assertEqual([numero for numero, _ in registros], [2, 5])

    def test_arquivo_vazio_ou_so_cabecalho(self):
        with self.assertRaises(ErroCsv):
            ler_csv(b"   ")
        with self.assertRaises(ErroCsv):
            ler_csv(b"Data;Vendas\n")


class TestSugestaoDeColunas(unittest.TestCase):

    def test_sugere_colunas_do_meta(self):
        """Dado um CSV do Meta, Então cada campo é sugerido na coluna certa,
        sem confundir 'Valor de conversão de compras' com vendas nem o CPC com cliques."""
        colunas, _ = ler_csv(CSV_META.encode("utf-8"))
        self.assertEqual(sugerir_mapeamento(colunas), {
            "data": "Início dos relatórios",
            "investimento": "Valor usado (BRL)",
            "impressoes": "Impressões",
            "cliques": "Cliques no link",
            "visitas": "Visualizações da página de destino",
            "carrinhos": "Adições ao carrinho",
            "vendas": "Compras",
            "receita": "Valor de conversão de compras",
        })

    def test_sugere_colunas_de_planilha_de_pedidos(self):
        sugestao = sugerir_mapeamento(["Número do pedido", "Data", "Cliente", "Total"])
        self.assertEqual(sugestao["data"], "Data")
        self.assertEqual(sugestao["receita"], "Total")
        self.assertIsNone(sugestao["vendas"])
        self.assertIsNone(sugestao["investimento"])

    def test_nao_confunde_midia_com_dia(self):
        self.assertIsNone(sugerir_mapeamento(["Mídia", "Impressões"])["data"])


class TestConversoes(unittest.TestCase):

    def test_datas(self):
        self.assertEqual(converter_data("2026-10-06"), date(2026, 10, 6))
        self.assertEqual(converter_data("06/10/2026"), date(2026, 10, 6))
        self.assertEqual(converter_data("6/10/2026 14:33"), date(2026, 10, 6))
        self.assertEqual(converter_data("2026-10-06 00:00:00"), date(2026, 10, 6))
        self.assertIsNone(converter_data("31/02/2026"))
        self.assertIsNone(converter_data("Total"))
        self.assertIsNone(converter_data(""))

    def test_numeros_em_reais(self):
        self.assertEqual(converter_numero("R$ 1.234,56"), 1234.56)
        self.assertEqual(converter_numero("1234.56"), 1234.56)
        self.assertEqual(converter_numero("1,234.56"), 1234.56)
        self.assertEqual(converter_numero("15,5"), 15.5)
        self.assertEqual(converter_numero(""), 0)
        self.assertEqual(converter_numero("-"), 0)
        self.assertIsNone(converter_numero("abc"))
        self.assertIsNone(converter_numero("-10"))

    def test_numeros_inteiros(self):
        self.assertEqual(converter_numero("10.000", inteiro=True), 10000)
        self.assertEqual(converter_numero("10,000", inteiro=True), 10000)
        self.assertEqual(converter_numero("42", inteiro=True), 42)
        self.assertIsNone(converter_numero("2.500,5", inteiro=True))  # contagem não tem fração


class TestConverterRegistros(unittest.TestCase):

    def setUp(self):
        colunas, self.registros = ler_csv(CSV_META.encode("utf-8"))
        self.mapeamento = validar_mapeamento(sugerir_mapeamento(colunas), colunas)

    def test_soma_linhas_do_mesmo_dia_e_ignora_linha_de_total(self):
        """Dado um CSV do Meta com 2 anúncios no dia 01/10 e uma linha de Total sem data,
        Então o dia 01/10 soma os dois anúncios e a linha de Total é ignorada."""
        dias, ignoradas = converter_registros(self.registros, self.mapeamento)
        self.assertEqual(dias[0], {"data": "2026-10-01", "investimento": 30.0, "impressoes": 5000,
                                   "cliques": 75, "visitas": 55, "carrinhos": 5, "vendas": 1,
                                   "receita": 200.0})
        self.assertEqual(dias[1]["data"], "2026-10-02")
        self.assertEqual(ignoradas, [{"linha": 5, "motivo": 'Data inválida ou vazia: ""'}])

    def test_so_traz_os_campos_escolhidos(self):
        mapeamento = dict(self.mapeamento, vendas=None, receita=None, visitas=None, carrinhos=None)
        dias, _ = converter_registros(self.registros, mapeamento)
        self.assertEqual(set(dias[0]), {"data", "investimento", "impressoes", "cliques"})

    def test_numero_invalido_ignora_a_linha(self):
        colunas, registros = ler_csv(b"Data;Vendas\n2026-10-01;2\n2026-10-02;dois\n")
        dias, ignoradas = converter_registros(registros, {"data": "Data", "vendas": "Vendas"})
        self.assertEqual(dias, [{"data": "2026-10-01", "vendas": 2}])
        self.assertEqual(ignoradas, [{"linha": 3, "motivo": 'Vendas inválido: "dois"'}])

    def test_contar_linhas_como_vendas(self):
        """Dada uma planilha de pedidos (1 linha por pedido), Quando escolho 'contar 1 por linha',
        Então cada dia tem a quantidade de pedidos e a soma dos totais."""
        conteudo = ("Pedido;Data;Total\n101;06/10/2026 09:10;199,90\n102;06/10/2026 15:42;199,90\n"
                    "103;07/10/2026 11:00;399,80\n").encode("utf-8")
        colunas, registros = ler_csv(conteudo)
        mapeamento = validar_mapeamento({"data": "Data", "vendas": CONTAR_LINHAS, "receita": "Total"}, colunas)
        dias, _ = converter_registros(registros, mapeamento)
        self.assertEqual(dias, [{"data": "2026-10-06", "vendas": 2, "receita": 399.8},
                                {"data": "2026-10-07", "vendas": 1, "receita": 399.8}])

    def test_mapeamento_invalido(self):
        colunas = ["Data", "Vendas"]
        with self.assertRaisesRegex(ErroCsv, "Escolha a coluna da data"):
            validar_mapeamento({"vendas": "Vendas"}, colunas)
        with self.assertRaisesRegex(ErroCsv, "pelo menos uma métrica"):
            validar_mapeamento({"data": "Data"}, colunas)
        with self.assertRaisesRegex(ErroCsv, "não existe"):
            validar_mapeamento({"data": "Data", "vendas": "Pedidos"}, colunas)


if __name__ == "__main__":
    unittest.main()
