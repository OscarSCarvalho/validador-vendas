"""Pontuação do produto (Etapa 2): notas de 1 a 5, total até 25 e veredito, com histórico."""
from flask import Blueprint, jsonify, session

from banco import obter_conexao
from regras import calcular_pontuacao, nota_margem_produto
from rotas.auth import ler_json, login_obrigatorio
from rotas.produtos import buscar_produto, produto_json

bp = Blueprint("pontuacao", __name__, url_prefix="/api/pontuacao")

# A margem não está aqui: é sempre calculada pelo backend a partir do produto.
CRITERIOS_MANUAIS = {
    "demanda": "Demanda",
    "concorrencia": "Concorrência",
    "frete": "Frete",
    "facilidade_explicar": "Facilidade de explicar",
}


def ler_notas():
    """Lê as notas manuais do JSON. Retorna (notas, erros)."""
    corpo = ler_json()
    notas, erros = {}, []
    for campo, rotulo in CRITERIOS_MANUAIS.items():
        valor = corpo.get(campo)
        if isinstance(valor, str) and valor.strip().isdigit():
            valor = int(valor)
        if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 5:
            erros.append(f"Escolha uma nota de 1 a 5 para {rotulo}.")
        notas[campo] = valor
    return notas, erros


def historico_do_produto(produto_id):
    linhas = obter_conexao().execute(
        "SELECT * FROM pontuacoes WHERE produto_id = ? ORDER BY criado_em DESC, id DESC",
        (produto_id,),
    ).fetchall()
    return [dict(linha) for linha in linhas]


@bp.route("/<int:produto_id>")
@login_obrigatorio
def detalhar(produto_id):
    produto = produto_json(buscar_produto(produto_id))
    historico = historico_do_produto(produto_id)
    return jsonify(
        produto=produto,
        nota_margem=nota_margem_produto(produto["modelo"], produto),
        ultima=historico[0] if historico else None,
        historico=historico,
    )


@bp.route("/<int:produto_id>", methods=["POST"])
@login_obrigatorio
def pontuar(produto_id):
    produto = produto_json(buscar_produto(produto_id))
    notas, erros = ler_notas()
    if erros:
        return jsonify(erros=erros), 400

    notas["margem"] = nota_margem_produto(produto["modelo"], produto)
    resultado = calcular_pontuacao(**notas)

    conexao = obter_conexao()
    cursor = conexao.execute(
        """INSERT INTO pontuacoes (produto_id, demanda, concorrencia, margem, frete,
                                   facilidade_explicar, total, veredito)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (produto_id, notas["demanda"], notas["concorrencia"], notas["margem"], notas["frete"],
         notas["facilidade_explicar"], resultado["total"], resultado["veredito"]),
    )
    # Só avança quem ainda é ideia; não rebaixa produtos que já estão em etapas seguintes.
    conexao.execute(
        "UPDATE produtos SET status = 'pontuado' WHERE id = ? AND usuario_id = ? AND status = 'ideia'",
        (produto_id, session["usuario_id"]),
    )
    conexao.commit()

    pontuacao = conexao.execute(
        "SELECT * FROM pontuacoes WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(dict(pontuacao)), 201
