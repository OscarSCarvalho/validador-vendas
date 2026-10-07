"""Validação manual guiada (Etapa 3): checklist das 8 etapas por produto."""
from flask import Blueprint, abort, jsonify, session

from banco import obter_conexao
from regras import ETAPAS_VALIDACAO, calcular_progresso
from rotas.auth import ler_json, login_obrigatorio, texto
from rotas.produtos import buscar_produto, produto_json

bp = Blueprint("validacao", __name__, url_prefix="/api/validacao")

NUMEROS_ETAPAS = {numero for numero, _, _ in ETAPAS_VALIDACAO}


def montar_checklist(produto_id):
    """As 8 etapas com o que já foi salvo. Etapa sem linha no banco = não concluída."""
    linhas = obter_conexao().execute(
        "SELECT * FROM validacao_manual WHERE produto_id = ?", (produto_id,)
    ).fetchall()
    salvas = {linha["etapa"]: linha for linha in linhas}

    etapas = []
    for numero, titulo, dica in ETAPAS_VALIDACAO:
        salva = salvas.get(numero)
        etapas.append({
            "etapa": numero,
            "titulo": titulo,
            "dica": dica,
            "concluida": bool(salva and salva["concluida"]),
            "observacao": (salva and salva["observacao"]) or "",
            "link_evidencia": (salva and salva["link_evidencia"]) or "",
            "atualizado_em": salva["atualizado_em"] if salva else None,
        })
    progresso = calcular_progresso(e["etapa"] for e in etapas if e["concluida"])
    return etapas, progresso


def validar_etapa():
    """Lê e valida o JSON da etapa. Retorna (dados, erros)."""
    corpo = ler_json()
    concluida = corpo.get("concluida", False)
    dados = {
        "concluida": concluida,
        "observacao": texto(corpo, "observacao"),
        "link_evidencia": texto(corpo, "link_evidencia"),
    }
    erros = []
    if concluida not in (True, False, 0, 1):
        erros.append("Informe se a etapa está concluída.")
    if dados["link_evidencia"] and not dados["link_evidencia"].startswith(("http://", "https://")):
        erros.append("O link de evidência deve começar com http:// ou https://.")
    return dados, erros


@bp.route("/<int:produto_id>")
@login_obrigatorio
def detalhar(produto_id):
    produto = produto_json(buscar_produto(produto_id))
    etapas, progresso = montar_checklist(produto_id)
    return jsonify(produto=produto, etapas=etapas, progresso=progresso)


@bp.route("/<int:produto_id>/<int:etapa>", methods=["PUT"])
@login_obrigatorio
def salvar_etapa(produto_id, etapa):
    buscar_produto(produto_id)
    if etapa not in NUMEROS_ETAPAS:
        abort(404, description="Etapa não encontrada.")
    dados, erros = validar_etapa()
    if erros:
        return jsonify(erros=erros), 400

    conexao = obter_conexao()
    conexao.execute(
        """INSERT INTO validacao_manual (produto_id, etapa, concluida, observacao, link_evidencia)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (produto_id, etapa) DO UPDATE SET
               concluida = excluded.concluida, observacao = excluded.observacao,
               link_evidencia = excluded.link_evidencia,
               atualizado_em = datetime('now', 'localtime')""",
        (produto_id, etapa, int(dados["concluida"]), dados["observacao"], dados["link_evidencia"]),
    )
    if dados["concluida"]:
        # Primeira etapa concluída leva o produto para "em validação"; nunca rebaixa status.
        conexao.execute(
            """UPDATE produtos SET status = 'em_validacao'
               WHERE id = ? AND usuario_id = ? AND status IN ('ideia', 'pontuado')""",
            (produto_id, session["usuario_id"]),
        )
    conexao.commit()

    etapas, progresso = montar_checklist(produto_id)
    status = buscar_produto(produto_id)["status"]
    return jsonify(etapa=etapas[etapa - 1], progresso=progresso, status=status)
