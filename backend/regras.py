"""Regras de negócio do validador (funções puras, sem Flask nem banco)."""
from decimal import ROUND_HALF_UP, Decimal


def calcular_margem(preco_venda, custo_unitario):
    """Margem unitária (R$) e percentual (0 a 1) de um produto.

    O custo_unitario já deve incluir produto, frete, taxas da plataforma e impostos.
    margem_percentual é None quando o preço é zero (divisão por zero).
    """
    margem_unitaria = round(preco_venda - custo_unitario, 2)
    if preco_venda == 0:
        margem_percentual = None
    else:
        margem_percentual = margem_unitaria / preco_venda
    return {"margem_unitaria": margem_unitaria, "margem_percentual": margem_percentual}


def calcular_comissao(preco_venda, taxa_comissao):
    """Afiliado: comissão por venda (R$) = preço × taxa (%). Ela faz o papel da margem unitária.
    Conta em Decimal para arredondar meio centavo para cima (34,95 × 30% = 10,485 -> 10,49)."""
    comissao = (Decimal(str(preco_venda)) * Decimal(str(taxa_comissao)) / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"margem_unitaria": float(comissao), "margem_percentual": taxa_comissao / 100}


def calcular_margem_produto(produto):
    """Margem do produto conforme o modelo: vendedor (preço − custo) ou afiliado (comissão)."""
    if produto.get("modelo") == "afiliado":
        return calcular_comissao(produto["preco_venda"], produto["taxa_comissao"] or 0)
    return calcular_margem(produto["preco_venda"], produto["custo_unitario"])


# Pontuação: 5 critérios com nota de 1 a 5, total até 25.
FAIXAS_NOTA_MARGEM = [(0.50, 5), (0.40, 4), (0.30, 3), (0.20, 2)]
TOTAL_MINIMO_VALE_TESTAR = 18
TOTAL_MINIMO_TESTAR_COM_CAUTELA = 13


def nota_margem(margem_percentual):
    """Nota automática da margem: ≥50% = 5; ≥40% = 4; ≥30% = 3; ≥20% = 2; abaixo = 1."""
    if margem_percentual is None:
        return 1
    margem = round(margem_percentual, 4)  # evita que 0.2999999 perca uma nota
    for minimo, nota in FAIXAS_NOTA_MARGEM:
        if margem >= minimo:
            return nota
    return 1


# Afiliado: nota pela comissão em R$ (o que paga o anúncio é o valor, não o percentual).
FAIXAS_NOTA_COMISSAO = [(20, 5), (10, 4), (5, 3), (2, 2)]


def nota_comissao(comissao):
    """Comissão por venda (R$) -> nota de 1 a 5: ≥ 20 = 5; ≥ 10 = 4; ≥ 5 = 3; ≥ 2 = 2; abaixo = 1."""
    for minimo, nota in FAIXAS_NOTA_COMISSAO:
        if round(comissao, 2) >= minimo:
            return nota
    return 1


def nota_margem_produto(modelo, margem):
    """Nota automática da margem conforme o modelo. margem: resultado de calcular_margem_produto."""
    if modelo == "afiliado":
        return nota_comissao(margem["margem_unitaria"])
    return nota_margem(margem["margem_percentual"])


def calcular_pontuacao(demanda, concorrencia, margem, frete, facilidade_explicar):
    """Soma as cinco notas (total até 25) e define o veredito."""
    total = demanda + concorrencia + margem + frete + facilidade_explicar
    if total >= TOTAL_MINIMO_VALE_TESTAR:
        veredito = "vale_testar"
    elif total >= TOTAL_MINIMO_TESTAR_COM_CAUTELA:
        veredito = "testar_com_cautela"
    else:
        veredito = "descartar"
    return {"total": total, "veredito": veredito}


# Validação manual: as 8 etapas do checklist de cada produto (número, título, dica).
ETAPAS_VALIDACAO = [
    (1, "Escolher 1 produto e 1 público", "Nicho definido em uma frase."),
    (2, "Pesquisar demanda", "Mais vendidos (Mercado Livre, Shopee), Google Trends, volume de buscas."),
    (3, "Analisar concorrentes", "Biblioteca de Anúncios da Meta, preços praticados."),
    (4, "Montar oferta mínima", "Landing page simples com link para o produto na plataforma."),
    (5, "Gerar links com UTM", "Um link para cada canal. Use o gerador de links desta página."),
    (6, "Rodar teste com verba pequena",
     "R$ 30 a 50/dia por 7 dias, ou canal orgânico (WhatsApp, grupos)."),
    (7, "Registrar métricas diariamente", "Investimento, cliques, visitas, carrinhos e vendas de cada dia."),
    (8, "Tomar a decisão", "Escalar, ajustar ou trocar de produto."),
]


def calcular_progresso(etapas_concluidas):
    """Quantas das 8 etapas estão concluídas. Recebe os números das etapas concluídas."""
    numeros_validos = {numero for numero, _, _ in ETAPAS_VALIDACAO}
    concluidas = len(set(etapas_concluidas) & numeros_validos)
    return {"concluidas": concluidas, "total": len(ETAPAS_VALIDACAO)}


# Teste de venda: funil, indicadores e veredito (somando todos os dias do teste).
CAMPOS_METRICAS = ["investimento", "impressoes", "cliques", "visitas", "carrinhos", "vendas", "receita"]
ETAPAS_FUNIL = [("impressoes", "Impressões"), ("cliques", "Cliques"), ("visitas", "Visitas"),
                ("carrinhos", "Carrinhos"), ("vendas", "Vendas")]
# Afiliado não vê carrinho; a "visita" é o clique no link de afiliado e a venda é o pedido.
ETAPAS_FUNIL_AFILIADO = [("impressoes", "Impressões"), ("cliques", "Cliques no anúncio"),
                         ("visitas", "Cliques no link de afiliado"), ("vendas", "Pedidos")]
LIMITE_ESCALAR = 0.70   # CPA até 70% da margem unitária
LIMITE_AJUSTAR = 1.00   # CPA até 100% da margem unitária

# Status que o produto assume conforme o veredito do teste.
STATUS_POR_VEREDITO = {"escalar": "escalar", "ajustar": "ajustar",
                       "trocar": "descartado", "continue_testando": "em_teste"}


def dividir(numerador, denominador):
    """Divisão que devolve None quando o denominador é zero (a tela mostra "–")."""
    if not denominador:
        return None
    return numerador / denominador


def somar_metricas(metricas):
    """Soma as métricas diárias. Valores em R$ arredondados em centavos."""
    totais = {campo: sum(m[campo] for m in metricas) for campo in CAMPOS_METRICAS}
    totais["investimento"] = round(totais["investimento"], 2)
    totais["receita"] = round(totais["receita"], 2)
    return totais


def calcular_indicadores(totais, margem_unitaria, modelo="vendedor"):
    """CTR, conversão, abandono de carrinho, CPA e lucro do teste.

    Afiliado: a "receita" lançada é a comissão recebida, então lucro = comissão − investimento
    (a comissão real varia: vale para tudo o que o cliente comprar em até 7 dias após o clique)."""
    vendas_por_carrinho = dividir(totais["vendas"], totais["carrinhos"])
    return {
        "ctr": dividir(totais["cliques"], totais["impressoes"]),
        "taxa_conversao": dividir(totais["vendas"], totais["visitas"]),
        "abandono_carrinho": None if vendas_por_carrinho is None else 1 - vendas_por_carrinho,
        "cpa": dividir(totais["investimento"], totais["vendas"]),
        "lucro": round(totais["receita"] - totais["investimento"], 2) if modelo == "afiliado"
                 else round(totais["vendas"] * margem_unitaria - totais["investimento"], 2),
    }


def calcular_funil(totais, modelo="vendedor"):
    """Impressões → cliques → visitas → carrinhos → vendas, com a taxa em relação à etapa anterior.
    Afiliado: impressões → cliques no anúncio → cliques no link de afiliado → pedidos."""
    funil, anterior = [], None
    for campo, rotulo in (ETAPAS_FUNIL_AFILIADO if modelo == "afiliado" else ETAPAS_FUNIL):
        valor = totais[campo]
        taxa = None if anterior is None else dividir(valor, anterior)
        funil.append({"etapa": campo, "rotulo": rotulo, "valor": valor, "taxa": taxa})
        anterior = valor
    return funil


def calcular_veredito_teste(investimento, vendas, margem_unitaria):
    """Veredito pelo CPA em relação à margem unitária.

    CPA ≤ 70% da margem = escalar; até 100% = ajustar; acima = trocar.
    Sem vendas: investimento maior que a margem = trocar; senão = continue_testando.
    razao_cpa_margem (CPA ÷ margem) alimenta a barra da tela; None quando não dá para calcular.
    """
    if vendas == 0:
        codigo = "trocar" if investimento > margem_unitaria else "continue_testando"
        return {"codigo": codigo, "razao_cpa_margem": None}
    if margem_unitaria <= 0:  # sem margem, qualquer venda dá prejuízo
        return {"codigo": "trocar", "razao_cpa_margem": None}

    razao = round((investimento / vendas) / margem_unitaria, 6)  # evita 0.7000001
    if razao <= LIMITE_ESCALAR:
        codigo = "escalar"
    elif razao <= LIMITE_AJUSTAR:
        codigo = "ajustar"
    else:
        codigo = "trocar"
    return {"codigo": codigo, "razao_cpa_margem": razao}


# Alertas do teste (Etapa 7).
QUEDA_MAXIMA_CONVERSAO = 0.30  # alerta quando a conversão do último dia cai mais de 30%


def _reais(valor):
    """90 -> 'R$ 90,00' (para as mensagens de alerta)."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _percentual(valor, casas=1):
    """0.04 -> '4,0%'"""
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def calcular_alertas(metricas, margem_unitaria, modelo="vendedor"):
    """Alertas do teste: CPA acima da margem e queda de conversão no último dia lançado.

    metricas: dias do teste (com data, investimento, visitas e vendas).
    A queda compara a conversão do último dia com visitas lançadas com a média dos dias anteriores
    (vendas ÷ visitas somadas). Dias sem visitas ficam de fora: um dia que só recebeu vendas pelo
    webhook, sem as visitas lançadas ainda, não tem conversão para comparar.
    """
    alertas = []
    totais = somar_metricas(metricas)
    cpa = dividir(totais["investimento"], totais["vendas"])
    if cpa is not None and cpa > margem_unitaria:
        alertas.append({
            "codigo": "cpa_acima_da_margem",
            "mensagem": (f"O CPA ({_reais(cpa)}) passou da "
                         f"{'comissão' if modelo == 'afiliado' else 'margem'} por venda ({_reais(margem_unitaria)})."),
        })

    dias = sorted((m for m in metricas if m["visitas"] > 0), key=lambda m: m["data"])
    if len(dias) >= 2:
        ultimo, anteriores = dias[-1], dias[:-1]
        conversao_ultimo = dividir(ultimo["vendas"], ultimo["visitas"])
        media = dividir(sum(d["vendas"] for d in anteriores), sum(d["visitas"] for d in anteriores))
        if conversao_ultimo is not None and media:
            queda = round(1 - conversao_ultimo / media, 6)
            if queda > QUEDA_MAXIMA_CONVERSAO:
                alertas.append({
                    "codigo": "conversao_caiu",
                    "mensagem": (f"A conversão do último dia ({_percentual(conversao_ultimo)}) caiu "
                                 f"{_percentual(queda, 0)} em relação à média dos dias anteriores "
                                 f"({_percentual(media)})."),
                })
    return alertas
