"""Leitura de CSV de métricas diárias (Etapa 6). Funções puras, sem Flask nem banco."""
import csv
import io
import re
import unicodedata
from datetime import date

CAMPOS_METRICAS = ["investimento", "impressoes", "cliques", "visitas", "carrinhos", "vendas", "receita"]
CAMPOS_REAIS = {"investimento", "receita"}
CONTAR_LINHAS = "__contar_linhas__"  # vendas: cada linha do arquivo conta como 1 venda
TAMANHO_MAXIMO = 2 * 1024 * 1024    # 2 MB
LINHAS_MAXIMAS = 5000
ROTULOS = {"data": "Data", "investimento": "Investimento", "impressoes": "Impressões", "cliques": "Cliques",
           "visitas": "Visitas", "carrinhos": "Carrinhos", "vendas": "Vendas", "receita": "Receita"}

# Palavras procuradas no nome da coluna, na ordem em que os campos são sugeridos.
# Receita vem antes de vendas para "Valor de conversão de compras" não virar vendas.
SUGESTOES = [
    ("data", ["inicio dos relatorios", "reporting starts", "data", "dia", "date", "day"]),
    ("receita", ["valor de conversao", "conversion value", "receita", "faturamento", "revenue", "total"]),
    ("investimento", ["valor usado", "valor gasto", "amount spent", "investimento", "gasto", "spend"]),
    ("carrinhos", ["carrinho", "add to cart", "adds to cart"]),
    ("visitas", ["visualizacoes da pagina de destino", "landing page views", "visitas", "sessoes",
                 "sessions", "visits"]),
    ("impressoes", ["impress"]),
    ("cliques", ["cliques no link", "link clicks", "cliques", "clicks"]),
    ("vendas", ["compras", "vendas", "pedidos", "purchases", "orders", "sales"]),
]
# Colunas derivadas (custo por, taxas) nunca são sugeridas.
NUNCA_SUGERIR = ["custo por", "cost per", "cpc", "cpm", "ctr", "taxa", "rate", "%", "frequencia",
                 "termino dos relatorios", "fim dos relatorios", "reporting ends"]


class ErroCsv(Exception):
    """Problema no arquivo ou na correspondência das colunas (mensagem para o usuário)."""


def normalizar(texto):
    """'Início dos Relatórios' -> 'inicio dos relatorios'"""
    sem_acento = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def decodificar(conteudo):
    """UTF-8 (com ou sem BOM) ou, se falhar, Latin-1 (Excel em português)."""
    try:
        return conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return conteudo.decode("latin-1")


def ler_csv(conteudo):
    """Lê o arquivo. Retorna (colunas, registros); cada registro é (número da linha, {coluna: valor})."""
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ErroCsv("Arquivo grande demais (máximo de 2 MB).")
    texto = decodificar(conteudo)
    if not texto.strip():
        raise ErroCsv("O arquivo está vazio.")

    primeira = texto.lstrip().splitlines()[0]
    separador = max([";", ",", "\t"], key=primeira.count)
    linhas = list(csv.reader(io.StringIO(texto.lstrip()), delimiter=separador))
    if len(linhas) < 2:
        raise ErroCsv("O arquivo precisa ter o cabeçalho e pelo menos uma linha de dados.")
    if len(linhas) - 1 > LINHAS_MAXIMAS:
        raise ErroCsv(f"O arquivo tem mais de {LINHAS_MAXIMAS} linhas.")

    colunas, vistas = [], {}
    for indice, nome in enumerate(linhas[0]):
        nome = nome.strip() or f"Coluna {indice + 1}"
        vistas[nome] = vistas.get(nome, 0) + 1
        colunas.append(nome if vistas[nome] == 1 else f"{nome} ({vistas[nome]})")

    registros = []
    for numero, linha in enumerate(linhas[1:], start=2):
        if not any(celula.strip() for celula in linha):
            continue  # linha em branco
        valores = linha + [""] * (len(colunas) - len(linha))
        registros.append((numero, dict(zip(colunas, valores))))
    return colunas, registros


def sugerir_mapeamento(colunas):
    """Sugere a coluna de cada campo pelo nome. Campo sem coluna parecida fica None."""
    mapeamento, usadas = {}, set()
    for campo, palavras in SUGESTOES:
        mapeamento[campo] = None
        for palavra in palavras:
            padrao = r"\b" + re.escape(palavra)
            escolhida = next((c for c in colunas if c not in usadas
                              and re.search(padrao, normalizar(c))
                              and not any(n in normalizar(c) for n in NUNCA_SUGERIR)), None)
            if escolhida:
                mapeamento[campo] = escolhida
                usadas.add(escolhida)
                break
    return {campo: mapeamento[campo] for campo in ["data"] + CAMPOS_METRICAS}


def validar_mapeamento(mapeamento, colunas):
    """Confere se as colunas escolhidas existem. Retorna o mapeamento limpo (só campos conhecidos)."""
    limpo = {}
    for campo in ["data"] + CAMPOS_METRICAS:
        coluna = mapeamento.get(campo) or None
        if coluna is not None and coluna not in colunas and not (campo == "vendas" and coluna == CONTAR_LINHAS):
            raise ErroCsv(f'A coluna "{coluna}" não existe no arquivo.')
        limpo[campo] = coluna
    if not limpo["data"]:
        raise ErroCsv("Escolha a coluna da data.")
    if not any(limpo[campo] for campo in CAMPOS_METRICAS):
        raise ErroCsv("Escolha pelo menos uma métrica para importar.")
    return limpo


def converter_data(texto):
    """'2026-10-06', '06/10/2026' ou com hora ('06/10/2026 14:33'). Retorna date ou None."""
    texto = str(texto or "").strip()
    try:
        if partes := re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", texto):
            return date(int(partes[1]), int(partes[2]), int(partes[3]))
        if partes := re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", texto):
            return date(int(partes[3]), int(partes[2]), int(partes[1]))
    except ValueError:  # ex.: 31/02/2026
        return None
    return None


def converter_numero(texto, inteiro=False):
    """'R$ 1.234,56', '1234.56', '1,234.56', '1.200' (inteiro). Vazio ou '-' vale 0.
    Retorna o número ou None se inválido ou negativo."""
    texto = str(texto or "").replace("R$", "").replace("BRL", "").replace("\xa0", "").replace(" ", "").strip()
    if texto in ("", "-", "–"):
        return 0
    if "," in texto and "." in texto:
        # O separador que aparece por último é o decimal.
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", "") if inteiro else texto.replace(",", ".")
    elif "." in texto and inteiro:
        texto = texto.replace(".", "")  # 1.200 impressões
    try:
        valor = float(texto)
    except ValueError:
        return None
    if valor < 0:
        return None
    if inteiro:
        return int(valor) if valor.is_integer() else None
    return valor


def converter_registros(registros, mapeamento):
    """Converte e soma por data. Retorna (dias, ignoradas).

    dias: lista ordenada de {"data": "AAAA-MM-DD", <só os campos importados>}.
    ignoradas: [{"linha": n, "motivo": "..."}] das linhas com data ou número inválido.
    """
    campos = [campo for campo in CAMPOS_METRICAS if mapeamento.get(campo)]
    por_data, ignoradas = {}, []
    for numero, registro in registros:
        bruto_data = registro.get(mapeamento["data"], "")
        dia = converter_data(bruto_data)
        if dia is None:
            ignoradas.append({"linha": numero, "motivo": f'Data inválida ou vazia: "{bruto_data.strip()}"'})
            continue

        valores, problema = {}, None
        for campo in campos:
            coluna = mapeamento[campo]
            if campo == "vendas" and coluna == CONTAR_LINHAS:
                valores[campo] = 1
                continue
            valor = converter_numero(registro.get(coluna, ""), inteiro=campo not in CAMPOS_REAIS)
            if valor is None:
                problema = f'{ROTULOS[campo]} inválido: "{registro.get(coluna, "").strip()}"'
                break
            valores[campo] = valor
        if problema:
            ignoradas.append({"linha": numero, "motivo": problema})
            continue

        soma = por_data.setdefault(dia, dict.fromkeys(campos, 0))
        for campo, valor in valores.items():
            soma[campo] += valor

    dias = []
    for dia in sorted(por_data):
        valores = por_data[dia]
        for campo in CAMPOS_REAIS & valores.keys():
            valores[campo] = round(valores[campo], 2)
        dias.append({"data": dia.isoformat(), **valores})
    return dias, ignoradas
