"""Testes de venda e métricas diárias (Etapa 4) e importação de CSV (Etapa 6)."""
import json
from datetime import date

from flask import Blueprint, abort, jsonify, request, session

from banco import obter_conexao
from importacao_csv import (CAMPOS_METRICAS, ErroCsv, converter_registros, ler_csv, sugerir_mapeamento,
                            validar_mapeamento)
from regras import (STATUS_POR_VEREDITO, calcular_alertas, calcular_funil, calcular_indicadores,
                    calcular_margem_produto, calcular_veredito_teste, somar_metricas)
from rotas.auth import ler_json, login_obrigatorio, texto
from rotas.produtos import buscar_produto, converter_valor, produto_json

bp = Blueprint("testes", __name__, url_prefix="/api/testes")

STATUS_TESTE = ("em_andamento", "encerrado")
CAMPOS_INTEIROS = ["impressoes", "cliques", "visitas", "carrinhos", "vendas"]
CAMPOS_REAIS = ["investimento", "receita"]
ROTULOS_METRICAS = {"investimento": "Investimento", "impressoes": "Impressões", "cliques": "Cliques",
                    "visitas": "Visitas", "carrinhos": "Carrinhos", "vendas": "Vendas",
                    "receita": "Receita"}


def ler_data(valor):
    """'2026-10-06' -> date; None se inválida."""
    try:
        return date.fromisoformat(str(valor or "").strip())
    except ValueError:
        return None


def converter_inteiro(valor):
    """Aceita 1200, '1200' e '1.200'. Vazio vale 0. Retorna int ou None se inválido."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    valor = str(valor if valor is not None else "").strip().replace(".", "")
    if valor == "":
        return 0
    return int(valor) if valor.isdigit() else None


def buscar_teste(teste_id):
    """Teste de um produto do usuário logado; 404 se não existir ou for de outro usuário."""
    teste = obter_conexao().execute(
        """SELECT t.* FROM testes_venda t JOIN produtos p ON p.id = t.produto_id
           WHERE t.id = ? AND p.usuario_id = ?""",
        (teste_id, session["usuario_id"]),
    ).fetchone()
    if teste is None:
        abort(404, description="Teste não encontrado.")
    return teste


def validar_teste(corpo, status_atual="em_andamento"):
    """Lê e valida os dados do teste. Retorna (dados, erros)."""
    inicio, fim = ler_data(corpo.get("data_inicio")), ler_data(corpo.get("data_fim"))
    dados = {
        "canal": texto(corpo, "canal"),
        "utm_campanha": texto(corpo, "utm_campanha").lower(),
        "verba_diaria": converter_valor(corpo.get("verba_diaria")),
        "data_inicio": inicio.isoformat() if inicio else None,
        "data_fim": fim.isoformat() if fim else None,
        "status": texto(corpo, "status") or status_atual,
    }
    erros = []
    if not dados["canal"]:
        erros.append("Informe o canal.")
    if not dados["utm_campanha"]:
        erros.append("Informe a campanha (utm_campaign).")
    if dados["verba_diaria"] is None or dados["verba_diaria"] < 0:
        erros.append("A verba diária deve ser um número igual ou maior que zero.")
    if inicio is None:
        erros.append("Informe a data de início.")
    if fim is None:
        erros.append("Informe a data de fim.")
    if inicio and fim and fim < inicio:
        erros.append("A data de fim não pode ser antes da data de início.")
    if dados["status"] not in STATUS_TESTE:
        erros.append("Status do teste inválido.")
    return dados, erros


def validar_metricas(corpo):
    """Lê e valida as métricas de um dia. Campos vazios valem 0. Retorna (dados, erros)."""
    dados, erros = {}, []
    for campo in CAMPOS_REAIS:
        bruto = corpo.get(campo)
        valor = 0.0 if bruto in (None, "") else converter_valor(bruto)
        if valor is None or valor < 0:
            erros.append(f"{ROTULOS_METRICAS[campo]} deve ser um valor igual ou maior que zero.")
        dados[campo] = valor
    for campo in CAMPOS_INTEIROS:
        valor = converter_inteiro(corpo.get(campo))
        if valor is None or valor < 0:
            erros.append(f"{ROTULOS_METRICAS[campo]} deve ser um número inteiro igual ou maior que zero.")
        dados[campo] = valor
    return dados, erros


def metricas_do_teste(teste_id):
    return [dict(linha) for linha in obter_conexao().execute(
        "SELECT * FROM metricas_diarias WHERE teste_id = ? ORDER BY data", (teste_id,)
    ).fetchall()]


def resumir_teste(teste):
    """Teste com produto, métricas por dia, totais, indicadores, funil, veredito e alertas."""
    produto = produto_json(buscar_produto(teste["produto_id"]))
    metricas = metricas_do_teste(teste["id"])
    totais = somar_metricas(metricas)
    margem = produto["margem_unitaria"]
    modelo = produto["modelo"]
    return {
        "teste": dict(teste),
        "produto": produto,
        "metricas": metricas,
        "totais": totais,
        "indicadores": calcular_indicadores(totais, margem, modelo),
        "funil": calcular_funil(totais, modelo),
        "veredito": calcular_veredito_teste(totais["investimento"], totais["vendas"], margem),
        "alertas": calcular_alertas(metricas, margem, modelo),
    }


def atualizar_status_pelo_teste(teste_id):
    """O produto segue o veredito do teste mexido por último. Não depende de login
    (também é chamado pelo webhook). Retorna o novo status."""
    conexao = obter_conexao()
    linha = conexao.execute(
        """SELECT p.* FROM testes_venda t
           JOIN produtos p ON p.id = t.produto_id WHERE t.id = ?""",
        (teste_id,),
    ).fetchone()
    margem = calcular_margem_produto(dict(linha))["margem_unitaria"]
    totais = somar_metricas(metricas_do_teste(teste_id))
    status = STATUS_POR_VEREDITO[calcular_veredito_teste(totais["investimento"], totais["vendas"], margem)["codigo"]]
    conexao.execute("UPDATE produtos SET status = ? WHERE id = ?", (status, linha["id"]))
    conexao.commit()
    return status


def resumo_com_status(teste_id):
    """Recalcula o teste, atualiza o status do produto e devolve o resumo."""
    buscar_teste(teste_id)  # confere se o teste é do usuário logado
    atualizar_status_pelo_teste(teste_id)
    return resumir_teste(buscar_teste(teste_id))


@bp.route("")
@login_obrigatorio
def listar():
    produto_id = request.args.get("produto_id", type=int)
    if produto_id is None:
        return jsonify(erros=["Informe o produto_id."]), 400
    buscar_produto(produto_id)
    testes = obter_conexao().execute(
        "SELECT * FROM testes_venda WHERE produto_id = ? ORDER BY data_inicio DESC, id DESC",
        (produto_id,),
    ).fetchall()
    lista = []
    for teste in testes:
        resumo = resumir_teste(teste)
        lista.append({**resumo["teste"], "totais": resumo["totais"],
                      "lucro": resumo["indicadores"]["lucro"], "veredito": resumo["veredito"]})
    return jsonify(lista)


@bp.route("", methods=["POST"])
@login_obrigatorio
def criar():
    corpo = ler_json()
    produto_id = corpo.get("produto_id")
    if not isinstance(produto_id, int) or isinstance(produto_id, bool):
        return jsonify(erros=["Informe o produto do teste."]), 400
    buscar_produto(produto_id)
    dados, erros = validar_teste(corpo)
    if erros:
        return jsonify(erros=erros), 400

    conexao = obter_conexao()
    cursor = conexao.execute(
        """INSERT INTO testes_venda (produto_id, canal, utm_campanha, verba_diaria,
                                     data_inicio, data_fim, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (produto_id, dados["canal"], dados["utm_campanha"], dados["verba_diaria"],
         dados["data_inicio"], dados["data_fim"], dados["status"]),
    )
    conexao.commit()
    return jsonify(resumo_com_status(cursor.lastrowid)), 201


@bp.route("/<int:teste_id>")
@login_obrigatorio
def detalhar(teste_id):
    return jsonify(resumir_teste(buscar_teste(teste_id)))


@bp.route("/<int:teste_id>", methods=["PUT"])
@login_obrigatorio
def atualizar(teste_id):
    teste = buscar_teste(teste_id)
    dados, erros = validar_teste(ler_json(), status_atual=teste["status"])
    if erros:
        return jsonify(erros=erros), 400
    conexao = obter_conexao()
    conexao.execute(
        """UPDATE testes_venda SET canal = ?, utm_campanha = ?, verba_diaria = ?,
                                   data_inicio = ?, data_fim = ?, status = ?
           WHERE id = ?""",
        (dados["canal"], dados["utm_campanha"], dados["verba_diaria"], dados["data_inicio"],
         dados["data_fim"], dados["status"], teste_id),
    )
    conexao.commit()
    return jsonify(resumir_teste(buscar_teste(teste_id)))


@bp.route("/<int:teste_id>", methods=["DELETE"])
@login_obrigatorio
def excluir(teste_id):
    buscar_teste(teste_id)
    conexao = obter_conexao()
    conexao.execute("DELETE FROM testes_venda WHERE id = ?", (teste_id,))
    conexao.commit()
    return "", 204


@bp.route("/<int:teste_id>/metricas/<data_metrica>", methods=["PUT"])
@login_obrigatorio
def salvar_metricas(teste_id, data_metrica):
    buscar_teste(teste_id)
    dia = ler_data(data_metrica)
    if dia is None:
        return jsonify(erros=["Data inválida. Use o formato AAAA-MM-DD."]), 400
    dados, erros = validar_metricas(ler_json())
    if erros:
        return jsonify(erros=erros), 400

    conexao = obter_conexao()
    conexao.execute(
        """INSERT INTO metricas_diarias (teste_id, data, investimento, impressoes, cliques,
                                         visitas, carrinhos, vendas, receita, origem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')
           ON CONFLICT (teste_id, data) DO UPDATE SET
               investimento = excluded.investimento, impressoes = excluded.impressoes,
               cliques = excluded.cliques, visitas = excluded.visitas,
               carrinhos = excluded.carrinhos, vendas = excluded.vendas,
               receita = excluded.receita, origem = 'manual'""",
        (teste_id, dia.isoformat(), dados["investimento"], dados["impressoes"], dados["cliques"],
         dados["visitas"], dados["carrinhos"], dados["vendas"], dados["receita"]),
    )
    conexao.commit()
    return jsonify(resumo_com_status(teste_id))


@bp.route("/<int:teste_id>/metricas/<data_metrica>", methods=["DELETE"])
@login_obrigatorio
def excluir_metricas(teste_id, data_metrica):
    buscar_teste(teste_id)
    dia = ler_data(data_metrica)
    conexao = obter_conexao()
    cursor = conexao.execute("DELETE FROM metricas_diarias WHERE teste_id = ? AND data = ?",
                             (teste_id, dia.isoformat() if dia else data_metrica))
    conexao.commit()
    if cursor.rowcount == 0:
        abort(404, description="Não há métricas nesse dia.")
    return jsonify(resumo_com_status(teste_id))


def ler_importacao(teste):
    """Lê o arquivo enviado e a correspondência das colunas. Retorna o que a prévia e a importação usam."""
    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        raise ErroCsv("Envie um arquivo CSV.")
    colunas, registros = ler_csv(arquivo.read())

    bruto = request.form.get("mapeamento")
    if bruto:
        try:
            mapeamento = json.loads(bruto)
        except ValueError:
            raise ErroCsv("Correspondência de colunas inválida.")
        if not isinstance(mapeamento, dict):
            raise ErroCsv("Correspondência de colunas inválida.")
    else:
        mapeamento = sugerir_mapeamento(colunas)

    sugestao = mapeamento
    try:
        mapeamento = validar_mapeamento(mapeamento, colunas)
    except ErroCsv as erro:
        if bruto:
            raise
        # Sem correspondência enviada e a sugestão não basta: devolve as colunas para o usuário escolher.
        return {"colunas": colunas, "mapeamento": sugestao, "dias": [], "ignoradas": [],
                "total_linhas": len(registros), "aviso": str(erro)}

    dias, ignoradas = converter_registros(registros, mapeamento)
    ja_lancadas = {linha["data"] for linha in obter_conexao().execute(
        "SELECT data FROM metricas_diarias WHERE teste_id = ?", (teste["id"],)).fetchall()}
    for dia in dias:
        dia["situacao"] = "atualiza" if dia["data"] in ja_lancadas else "novo"
        dia["fora_do_periodo"] = not teste["data_inicio"] <= dia["data"] <= teste["data_fim"]
    return {"colunas": colunas, "mapeamento": mapeamento, "dias": dias, "ignoradas": ignoradas,
            "total_linhas": len(registros), "aviso": None}


@bp.route("/<int:teste_id>/csv/previa", methods=["POST"])
@login_obrigatorio
def previa_csv(teste_id):
    teste = buscar_teste(teste_id)
    try:
        return jsonify(ler_importacao(teste))
    except ErroCsv as erro:
        return jsonify(erros=[str(erro)]), 400


@bp.route("/<int:teste_id>/csv/importar", methods=["POST"])
@login_obrigatorio
def importar_csv(teste_id):
    teste = buscar_teste(teste_id)
    try:
        importacao = ler_importacao(teste)
    except ErroCsv as erro:
        return jsonify(erros=[str(erro)]), 400
    if importacao["aviso"]:
        return jsonify(erros=[importacao["aviso"]]), 400
    if not importacao["dias"]:
        return jsonify(erros=["Nenhum dia válido para importar."]), 400

    # Só os campos escolhidos são gravados; os outros dados do dia continuam como estavam.
    campos = [campo for campo in CAMPOS_METRICAS if importacao["mapeamento"][campo]]
    conexao = obter_conexao()
    for dia in importacao["dias"]:
        valores = [dia[campo] for campo in campos]
        if dia["situacao"] == "atualiza":
            atribuicoes = ", ".join(f"{campo} = ?" for campo in campos)
            conexao.execute(
                f"UPDATE metricas_diarias SET {atribuicoes}, origem = 'csv' WHERE teste_id = ? AND data = ?",
                (*valores, teste_id, dia["data"]),
            )
        else:
            colunas = ", ".join(campos)
            marcadores = ", ".join("?" for _ in campos)
            conexao.execute(
                f"INSERT INTO metricas_diarias (teste_id, data, {colunas}, origem) VALUES (?, ?, {marcadores}, 'csv')",
                (teste_id, dia["data"], *valores),
            )
    conexao.commit()

    novos = sum(1 for dia in importacao["dias"] if dia["situacao"] == "novo")
    return jsonify(importados=len(importacao["dias"]), novos=novos,
                   atualizados=len(importacao["dias"]) - novos, resumo=resumo_com_status(teste_id))
