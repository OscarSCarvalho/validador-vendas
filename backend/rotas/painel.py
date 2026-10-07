"""Painel comparativo (Etapa 5): todos os produtos com pontuação e o teste mais recente."""
from flask import Blueprint, jsonify, session

from banco import obter_conexao
from rotas.auth import login_obrigatorio
from rotas.produtos import produto_json
from rotas.testes import resumir_teste

bp = Blueprint("painel", __name__, url_prefix="/api/painel")


def ultima_pontuacao(produto_id):
    linha = obter_conexao().execute(
        """SELECT total, veredito, criado_em FROM pontuacoes WHERE produto_id = ?
           ORDER BY criado_em DESC, id DESC LIMIT 1""",
        (produto_id,),
    ).fetchone()
    return dict(linha) if linha else None


def resumo_do_teste(teste):
    """O que o painel mostra de um teste: período, totais, CPA, lucro e veredito."""
    resumo = resumir_teste(teste)
    return {
        "id": teste["id"],
        "canal": teste["canal"],
        "utm_campanha": teste["utm_campanha"],
        "data_inicio": teste["data_inicio"],
        "data_fim": teste["data_fim"],
        "status": teste["status"],
        "totais": resumo["totais"],
        "cpa": resumo["indicadores"]["cpa"],
        "lucro": resumo["indicadores"]["lucro"],
        "veredito": resumo["veredito"],
        "alertas": resumo["alertas"],
    }


@bp.route("")
@login_obrigatorio
def painel():
    conexao = obter_conexao()
    linhas = conexao.execute(
        "SELECT * FROM produtos WHERE usuario_id = ? ORDER BY criado_em DESC, id DESC",
        (session["usuario_id"],),
    ).fetchall()

    produtos = []
    for linha in linhas:
        produto = produto_json(linha)
        # O painel mostra o teste mais recente (data de início mais nova).
        testes = conexao.execute(
            "SELECT * FROM testes_venda WHERE produto_id = ? ORDER BY data_inicio DESC, id DESC",
            (produto["id"],),
        ).fetchall()
        produtos.append({
            "id": produto["id"],
            "nome": produto["nome"],
            "plataforma": produto["plataforma"],
            "status": produto["status"],
            "modelo": produto["modelo"],
            "margem_unitaria": produto["margem_unitaria"],
            "margem_percentual": produto["margem_percentual"],
            "pontuacao": ultima_pontuacao(produto["id"]),
            "teste": resumo_do_teste(testes[0]) if testes else None,
            "quantidade_testes": len(testes),
        })

    # Todos os testes do usuário, para o seletor do gráfico (mais recente primeiro).
    testes = conexao.execute(
        """SELECT t.id, t.produto_id, p.nome AS produto_nome, p.modelo, t.canal, t.utm_campanha,
                  t.data_inicio, t.data_fim
           FROM testes_venda t JOIN produtos p ON p.id = t.produto_id
           WHERE p.usuario_id = ? ORDER BY t.data_inicio DESC, t.id DESC""",
        (session["usuario_id"],),
    ).fetchall()
    return jsonify(produtos=produtos, testes=[dict(t) for t in testes])
