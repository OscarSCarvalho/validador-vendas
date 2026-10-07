"""CRUD de produtos do usuário logado (API JSON)."""
from flask import Blueprint, abort, jsonify, session

from banco import obter_conexao
from regras import calcular_margem_produto
from rotas.auth import ler_json, login_obrigatorio, texto

bp = Blueprint("produtos", __name__, url_prefix="/api/produtos")

MODELOS = ("vendedor", "afiliado")


def converter_valor(valor):
    """Aceita 200, 200.5, '200,50' e '1.234,56'. Retorna float ou None."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    valor = str(valor or "").strip().replace("R$", "").strip()
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except ValueError:
        return None


def validar_produto():
    """Lê e valida o JSON do produto. Retorna (dados, erros)."""
    corpo = ler_json()
    modelo = texto(corpo, "modelo") or "vendedor"
    afiliado = modelo == "afiliado"
    dados = {
        "nome": texto(corpo, "nome"),
        "plataforma": texto(corpo, "plataforma"),
        "url_produto": texto(corpo, "url_produto"),
        "preco_venda": converter_valor(corpo.get("preco_venda")),
        # Afiliado não tem custo: ganha a comissão sobre o preço.
        "custo_unitario": 0.0 if afiliado else converter_valor(corpo.get("custo_unitario")),
        "modelo": modelo,
        "taxa_comissao": converter_valor(corpo.get("taxa_comissao")) if afiliado else None,
    }
    erros = []
    if modelo not in MODELOS:
        erros.append("Modelo inválido: use vendedor ou afiliado.")
    if not dados["nome"]:
        erros.append("Informe o nome do produto.")
    if not dados["plataforma"]:
        erros.append("Informe a plataforma.")
    if dados["url_produto"] and not dados["url_produto"].startswith(("http://", "https://")):
        erros.append("A URL do produto deve começar com http:// ou https://.")
    if dados["preco_venda"] is None or dados["preco_venda"] <= 0:
        erros.append("O preço de venda deve ser um número maior que zero.")
    if dados["custo_unitario"] is None or dados["custo_unitario"] < 0:
        erros.append("O custo unitário deve ser um número igual ou maior que zero.")
    if afiliado and (dados["taxa_comissao"] is None or not 0 < dados["taxa_comissao"] <= 100):
        erros.append("A comissão deve ser um percentual maior que 0 e até 100.")
    return dados, erros


def produto_json(linha):
    """Produto com a margem calculada pelo backend (no afiliado, a margem é a comissão por venda)."""
    produto = dict(linha)
    produto.pop("usuario_id", None)
    produto.update(calcular_margem_produto(produto))
    return produto


def buscar_produto(produto_id):
    """Busca um produto do usuário logado; 404 se não existir ou for de outro usuário."""
    produto = obter_conexao().execute(
        "SELECT * FROM produtos WHERE id = ? AND usuario_id = ?",
        (produto_id, session["usuario_id"]),
    ).fetchone()
    if produto is None:
        abort(404, description="Produto não encontrado.")
    return produto


@bp.route("")
@login_obrigatorio
def listar():
    linhas = obter_conexao().execute(
        "SELECT * FROM produtos WHERE usuario_id = ? ORDER BY criado_em DESC, id DESC",
        (session["usuario_id"],),
    ).fetchall()
    return jsonify([produto_json(linha) for linha in linhas])


@bp.route("", methods=["POST"])
@login_obrigatorio
def criar():
    dados, erros = validar_produto()
    if erros:
        return jsonify(erros=erros), 400
    conexao = obter_conexao()
    cursor = conexao.execute(
        """INSERT INTO produtos (usuario_id, nome, plataforma, url_produto,
                                 preco_venda, custo_unitario, modelo, taxa_comissao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (session["usuario_id"], dados["nome"], dados["plataforma"], dados["url_produto"],
         dados["preco_venda"], dados["custo_unitario"], dados["modelo"], dados["taxa_comissao"]),
    )
    conexao.commit()
    return jsonify(produto_json(buscar_produto(cursor.lastrowid))), 201


@bp.route("/<int:produto_id>")
@login_obrigatorio
def detalhar(produto_id):
    return jsonify(produto_json(buscar_produto(produto_id)))


@bp.route("/<int:produto_id>", methods=["PUT"])
@login_obrigatorio
def atualizar(produto_id):
    buscar_produto(produto_id)
    dados, erros = validar_produto()
    if erros:
        return jsonify(erros=erros), 400
    conexao = obter_conexao()
    conexao.execute(
        """UPDATE produtos
           SET nome = ?, plataforma = ?, url_produto = ?, preco_venda = ?, custo_unitario = ?,
               modelo = ?, taxa_comissao = ?
           WHERE id = ? AND usuario_id = ?""",
        (dados["nome"], dados["plataforma"], dados["url_produto"], dados["preco_venda"],
         dados["custo_unitario"], dados["modelo"], dados["taxa_comissao"], produto_id, session["usuario_id"]),
    )
    conexao.commit()
    return jsonify(produto_json(buscar_produto(produto_id)))


@bp.route("/<int:produto_id>", methods=["DELETE"])
@login_obrigatorio
def excluir(produto_id):
    buscar_produto(produto_id)
    conexao = obter_conexao()
    conexao.execute("DELETE FROM produtos WHERE id = ? AND usuario_id = ?",
                    (produto_id, session["usuario_id"]))
    conexao.commit()
    return "", 204
