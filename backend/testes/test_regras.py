import unittest

from regras import (calcular_comissao, calcular_margem_produto, nota_comissao, nota_margem_produto,
                    ETAPAS_VALIDACAO, calcular_alertas, calcular_funil, calcular_indicadores, calcular_margem,
                    calcular_pontuacao, calcular_progresso, calcular_veredito_teste, nota_margem,
                    somar_metricas)


class TestCalcularMargem(unittest.TestCase):

    def test_margem_preco_200_custo_110(self):
        """Dado preço 200 e custo 110, Quando calculo a margem, Então é R$ 90 e 45%."""
        resultado = calcular_margem(200, 110)
        self.assertEqual(resultado["margem_unitaria"], 90)
        self.assertAlmostEqual(resultado["margem_percentual"], 0.45)

    def test_margem_negativa_quando_custo_maior_que_preco(self):
        resultado = calcular_margem(100, 130)
        self.assertEqual(resultado["margem_unitaria"], -30)
        self.assertAlmostEqual(resultado["margem_percentual"], -0.30)

    def test_margem_com_centavos_sem_erro_de_arredondamento(self):
        resultado = calcular_margem(59.90, 32.45)
        self.assertEqual(resultado["margem_unitaria"], 27.45)

    def test_preco_zero_nao_divide_por_zero(self):
        resultado = calcular_margem(0, 10)
        self.assertIsNone(resultado["margem_percentual"])


class TestNotaMargem(unittest.TestCase):

    def test_faixas_da_margem(self):
        """Dada a margem percentual, Então a nota segue: ≥50% = 5; ≥40% = 4; ≥30% = 3; ≥20% = 2; abaixo = 1."""
        casos = [(0.60, 5), (0.50, 5), (0.45, 4), (0.40, 4), (0.35, 3), (0.30, 3),
                 (0.25, 2), (0.20, 2), (0.19, 1), (0.0, 1), (-0.30, 1), (None, 1)]
        for margem, nota in casos:
            with self.subTest(margem=margem):
                self.assertEqual(nota_margem(margem), nota)

    def test_margem_calculada_no_limite_nao_perde_nota(self):
        """Dado preço 59,90 e custo 41,93 (margem de 30% com centavos), Então a nota é 3."""
        margem = calcular_margem(59.90, 41.93)["margem_percentual"]
        self.assertEqual(nota_margem(margem), 3)

    def test_produto_200_custo_110_tem_nota_4(self):
        """Dado o leitor com preço 200 e custo 110 (45%), Então a nota da margem é 4."""
        self.assertEqual(nota_margem(calcular_margem(200, 110)["margem_percentual"]), 4)


class TestCalcularPontuacao(unittest.TestCase):

    def test_total_maximo_e_minimo(self):
        self.assertEqual(calcular_pontuacao(5, 5, 5, 5, 5), {"total": 25, "veredito": "vale_testar"})
        self.assertEqual(calcular_pontuacao(1, 1, 1, 1, 1), {"total": 5, "veredito": "descartar"})

    def test_limites_do_veredito(self):
        """Total 18 = Vale testar; 17 e 13 = Testar com cautela; 12 = Descartar."""
        self.assertEqual(calcular_pontuacao(4, 4, 4, 3, 3)["veredito"], "vale_testar")
        self.assertEqual(calcular_pontuacao(4, 4, 3, 3, 3)["veredito"], "testar_com_cautela")
        self.assertEqual(calcular_pontuacao(3, 3, 3, 2, 2)["veredito"], "testar_com_cautela")
        self.assertEqual(calcular_pontuacao(3, 3, 2, 2, 2)["veredito"], "descartar")


class TestValidacaoManual(unittest.TestCase):

    def test_sao_8_etapas_em_ordem(self):
        self.assertEqual([numero for numero, _, _ in ETAPAS_VALIDACAO], list(range(1, 9)))

    def test_progresso(self):
        """Dadas as etapas 1, 2 e 5 concluídas, Então o progresso é 3 de 8."""
        self.assertEqual(calcular_progresso([1, 2, 5]), {"concluidas": 3, "total": 8})
        self.assertEqual(calcular_progresso([]), {"concluidas": 0, "total": 8})

    def test_progresso_ignora_repetidas_e_inexistentes(self):
        self.assertEqual(calcular_progresso([1, 1, 9]), {"concluidas": 1, "total": 8})


TOTAIS_EXEMPLO = {"investimento": 210.0, "impressoes": 10000, "cliques": 200, "visitas": 150,
                  "carrinhos": 12, "vendas": 3, "receita": 600.0}


class TestIndicadoresDoTeste(unittest.TestCase):

    def test_somar_metricas_de_varios_dias(self):
        dias = [{"investimento": 30.1, "impressoes": 1000, "cliques": 20, "visitas": 15,
                 "carrinhos": 2, "vendas": 1, "receita": 200.0},
                {"investimento": 30.2, "impressoes": 500, "cliques": 10, "visitas": 5,
                 "carrinhos": 0, "vendas": 0, "receita": 0.0}]
        totais = somar_metricas(dias)
        self.assertEqual(totais["investimento"], 60.3)
        self.assertEqual(totais["impressoes"], 1500)
        self.assertEqual(totais["vendas"], 1)

    def test_indicadores(self):
        """Dado 10.000 impressões, 200 cliques, 150 visitas, 12 carrinhos, 3 vendas e R$ 210 investidos,
        com margem de R$ 90, Então CTR 2%, conversão 2%, abandono 75%, CPA R$ 70 e lucro R$ 60."""
        indicadores = calcular_indicadores(TOTAIS_EXEMPLO, 90)
        self.assertAlmostEqual(indicadores["ctr"], 0.02)
        self.assertAlmostEqual(indicadores["taxa_conversao"], 0.02)
        self.assertAlmostEqual(indicadores["abandono_carrinho"], 0.75)
        self.assertAlmostEqual(indicadores["cpa"], 70)
        self.assertEqual(indicadores["lucro"], 60)

    def test_divisao_por_zero_devolve_none(self):
        """Dado um teste sem nenhum dado, Então CTR, conversão, abandono e CPA ficam vazios ("–")."""
        zerado = dict.fromkeys(TOTAIS_EXEMPLO, 0)
        indicadores = calcular_indicadores(zerado, 90)
        for campo in ("ctr", "taxa_conversao", "abandono_carrinho", "cpa"):
            self.assertIsNone(indicadores[campo], campo)
        self.assertEqual(indicadores["lucro"], 0)

    def test_funil_com_taxa_entre_etapas(self):
        funil = calcular_funil(TOTAIS_EXEMPLO)
        self.assertEqual([e["etapa"] for e in funil],
                         ["impressoes", "cliques", "visitas", "carrinhos", "vendas"])
        self.assertIsNone(funil[0]["taxa"])
        self.assertAlmostEqual(funil[1]["taxa"], 0.02)    # 200 / 10.000
        self.assertAlmostEqual(funil[2]["taxa"], 0.75)    # 150 / 200
        self.assertAlmostEqual(funil[4]["taxa"], 0.25)    # 3 / 12


class TestVereditoDoTeste(unittest.TestCase):
    """Margem unitária de R$ 90 (preço 200, custo 110)."""

    def veredito(self, investimento, vendas, margem=90):
        return calcular_veredito_teste(investimento, vendas, margem)["codigo"]

    def test_cpa_ate_70_por_cento_escalar(self):
        self.assertEqual(self.veredito(60, 1), "escalar")      # CPA 60 = 66,7%
        self.assertEqual(self.veredito(63, 1), "escalar")      # CPA 63 = 70% exato

    def test_cpa_entre_70_e_100_por_cento_ajustar(self):
        self.assertEqual(self.veredito(63.9, 1), "ajustar")    # 71%
        self.assertEqual(self.veredito(180, 2), "ajustar")     # CPA 90 = 100% exato

    def test_cpa_acima_de_100_por_cento_trocar(self):
        self.assertEqual(self.veredito(181, 2), "trocar")

    def test_sem_vendas(self):
        """Sem vendas: investimento acima da margem = trocar; senão = continue testando."""
        self.assertEqual(self.veredito(50, 0), "continue_testando")
        self.assertEqual(self.veredito(90, 0), "continue_testando")
        self.assertEqual(self.veredito(90.01, 0), "trocar")

    def test_razao_cpa_margem_para_a_barra(self):
        self.assertAlmostEqual(calcular_veredito_teste(45, 1, 90)["razao_cpa_margem"], 0.5)
        self.assertIsNone(calcular_veredito_teste(10, 0, 90)["razao_cpa_margem"])

    def test_produto_sem_margem_com_venda_trocar(self):
        self.assertEqual(self.veredito(10, 1, margem=-5), "trocar")



def dia(data, investimento=0, visitas=0, vendas=0):
    return {"data": data, "investimento": investimento, "impressoes": 0, "cliques": 0, "visitas": visitas,
            "carrinhos": 0, "vendas": vendas, "receita": 0}


class TestAlertas(unittest.TestCase):
    """Margem unitária de R$ 90."""

    def codigos(self, metricas):
        return [a["codigo"] for a in calcular_alertas(metricas, 90)]

    def test_sem_alertas(self):
        self.assertEqual(self.codigos([]), [])
        self.assertEqual(self.codigos([dia("2026-10-01", 30, 100, 2), dia("2026-10-02", 30, 100, 2)]), [])

    def test_cpa_acima_da_margem(self):
        """Dado R$ 100 investidos e 1 venda (CPA 100 > margem 90), Então aparece o alerta de CPA."""
        alertas = calcular_alertas([dia("2026-10-01", 100, 50, 1)], 90)
        self.assertEqual([a["codigo"] for a in alertas], ["cpa_acima_da_margem"])
        self.assertEqual(alertas[0]["mensagem"], "O CPA (R$ 100,00) passou da margem por venda (R$ 90,00).")

    def test_cpa_igual_a_margem_nao_alerta(self):
        self.assertEqual(self.codigos([dia("2026-10-01", 90, 50, 1)]), [])

    def test_conversao_caiu_mais_de_30_por_cento(self):
        """Dado 4% de conversão nos dias anteriores e 2% no último (queda de 50%), Então aparece o alerta."""
        alertas = calcular_alertas([dia("2026-10-01", 10, 100, 4), dia("2026-10-02", 10, 100, 4),
                                    dia("2026-10-03", 10, 100, 2)], 90)
        self.assertEqual([a["codigo"] for a in alertas], ["conversao_caiu"])
        self.assertIn("caiu 50%", alertas[0]["mensagem"])

    def test_queda_de_exatos_30_por_cento_nao_alerta(self):
        self.assertEqual(self.codigos([dia("2026-10-01", 10, 100, 10), dia("2026-10-02", 10, 100, 7)]), [])
        self.assertEqual(self.codigos([dia("2026-10-01", 10, 100, 10), dia("2026-10-02", 10, 100, 6)]),
                         ["conversao_caiu"])

    def test_usa_o_ultimo_dia_pela_data(self):
        self.assertEqual(self.codigos([dia("2026-10-02", 10, 100, 1), dia("2026-10-01", 10, 100, 4)]),
                         ["conversao_caiu"])

    def test_dia_so_com_vendas_do_webhook_nao_esconde_a_queda(self):
        """Dado 4% e depois 1% de conversão, e hoje 1 venda pelo webhook sem visitas lançadas,
        Então a queda continua sendo avisada (compara o último dia com visitas)."""
        self.assertEqual(self.codigos([dia("2026-10-01", 10, 100, 4), dia("2026-10-02", 10, 100, 1),
                                       dia("2026-10-03", 0, 0, 1)]), ["conversao_caiu"])

    def test_sem_visitas_nao_compara(self):
        self.assertEqual(self.codigos([dia("2026-10-01", 10, 0, 0), dia("2026-10-02", 10, 100, 1)]), [])
        self.assertEqual(self.codigos([dia("2026-10-01", 10, 100, 4), dia("2026-10-02", 10, 0, 0)]), [])


class TestModoAfiliado(unittest.TestCase):

    def test_comissao_e_a_margem_do_afiliado(self):
        """Dado um produto de R$ 34,95 com comissão de 3%, Então a comissão por venda é R$ 1,05."""
        self.assertEqual(calcular_comissao(34.95, 3), {"margem_unitaria": 1.05, "margem_percentual": 0.03})

    def test_meio_centavo_arredonda_para_cima(self):
        """34,95 × 30% = 10,485 -> R$ 10,49 (não 10,48)."""
        self.assertEqual(calcular_comissao(34.95, 30)["margem_unitaria"], 10.49)

    def test_margem_pelo_modelo(self):
        afiliado = {"modelo": "afiliado", "preco_venda": 199.90, "custo_unitario": 0, "taxa_comissao": 12.5}
        vendedor = {"modelo": "vendedor", "preco_venda": 200, "custo_unitario": 110, "taxa_comissao": None}
        self.assertEqual(calcular_margem_produto(afiliado)["margem_unitaria"], 24.99)
        self.assertEqual(calcular_margem_produto(vendedor)["margem_unitaria"], 90)

    def test_nota_pela_comissao_em_reais(self):
        """≥ R$ 20 = 5; ≥ R$ 10 = 4; ≥ R$ 5 = 3; ≥ R$ 2 = 2; abaixo = 1."""
        casos = [(25, 5), (20, 5), (19.99, 4), (10, 4), (5, 3), (4.99, 2), (2, 2), (1.05, 1), (0, 1)]
        for comissao, nota in casos:
            with self.subTest(comissao=comissao):
                self.assertEqual(nota_comissao(comissao), nota)

    def test_nota_da_margem_segue_o_modelo(self):
        """Uma comissão de 30% sobre R$ 34,95 (R$ 10,49) vale nota 4 pelo valor, não pelo percentual."""
        self.assertEqual(nota_margem_produto("afiliado", calcular_comissao(34.95, 30)), 4)
        self.assertEqual(nota_margem_produto("vendedor", {"margem_unitaria": 90, "margem_percentual": 0.45}), 4)

    def test_lucro_do_afiliado_usa_a_comissao_recebida(self):
        """Dado R$ 60 investidos e R$ 9,50 de comissão recebida, Então o lucro é −R$ 50,50."""
        totais = dict(TOTAIS_EXEMPLO, investimento=60, vendas=3, receita=9.5, carrinhos=0)
        self.assertEqual(calcular_indicadores(totais, 3.15, "afiliado")["lucro"], -50.5)
        self.assertIsNone(calcular_indicadores(totais, 3.15, "afiliado")["abandono_carrinho"])

    def test_funil_do_afiliado_sem_carrinho(self):
        funil = calcular_funil(TOTAIS_EXEMPLO, "afiliado")
        self.assertEqual([e["rotulo"] for e in funil],
                         ["Impressões", "Cliques no anúncio", "Cliques no link de afiliado", "Pedidos"])
        self.assertAlmostEqual(funil[3]["taxa"], 3 / 150)  # pedidos ÷ cliques no link

    def test_alerta_fala_em_comissao(self):
        alertas = calcular_alertas([dia("2026-10-01", 30, 50, 1)], 10.49, "afiliado")
        self.assertEqual(alertas[0]["mensagem"], "O CPA (R$ 30,00) passou da comissão por venda (R$ 10,49).")


if __name__ == "__main__":
    unittest.main()
