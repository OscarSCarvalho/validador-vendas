"""Integrações com plataformas (Etapa 7): webhooks de pedidos pagos da Nuvemshop e da Shopify.

Os webhooks não usam login: a origem é conferida pela assinatura (HMAC-SHA256) com o segredo do .env.
O pedido é ligado ao teste pela utm_campaign e soma 1 venda e o valor no dia (origem = 'webhook').
O cancelamento avisado pela loja desconta a venda e o valor do mesmo dia.
"""
import base64
import hashlib
import hmac
import json
import math
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote_plus

from flask import Blueprint, jsonify, request, session

from banco import obter_conexao
from rotas.auth import login_obrigatorio
from rotas.testes import atualizar_status_pelo_teste

bp = Blueprint("integracoes", __name__, url_prefix="/api/integracoes")

API_NUVEMSHOP = "https://api.nuvemshop.com.br/v1"
# O dia do pedido é sempre o de Brasília, mesmo num servidor em UTC (sem horário de verão desde 2019).
FUSO_BRASIL = timezone(timedelta(hours=-3), "Brasília")
PADRAO_UTM_CAMPANHA = re.compile(r"utm_campaign=([^&#\s\"'<>]+)", re.IGNORECASE)


# ---------- Funções puras ----------

def assinatura_valida_hex(segredo, corpo, assinatura):
    """Nuvemshop: HMAC-SHA256 do corpo em hexadecimal."""
    esperada = hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, (assinatura or "").strip().lower())


def assinatura_valida_base64(segredo, corpo, assinatura):
    """Shopify: HMAC-SHA256 do corpo em base64."""
    esperada = base64.b64encode(hmac.new(segredo.encode(), corpo, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(esperada, (assinatura or "").strip())


def extrair_utm_campanha(pedido, campos_preferidos=()):
    """Procura utm_campaign primeiro nos campos indicados (ex.: landing_url) e depois no pedido inteiro.
    Retorna a campanha em minúsculas ou None."""
    def procurar(valor):
        if isinstance(valor, str):
            achado = PADRAO_UTM_CAMPANHA.search(valor)
            return unquote_plus(achado.group(1)).strip().lower() if achado else None
        if isinstance(valor, dict):
            valor = list(valor.values())
        if isinstance(valor, list):
            for item in valor:
                if campanha := procurar(item):
                    return campanha
        return None

    for campo in campos_preferidos:
        if campanha := procurar(pedido.get(campo)):
            return campanha
    return procurar(pedido)


def hoje_no_brasil():
    return datetime.now(FUSO_BRASIL).date().isoformat()


def data_do_pedido(texto):
    """'2026-10-07T02:30:00+0000' -> dia em Brasília ('2026-10-06'), em qualquer fuso do servidor.
    Data sem fuso já é considerada de Brasília."""
    texto = str(texto or "").strip()
    texto = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", texto).replace("Z", "+00:00")
    try:
        momento = datetime.fromisoformat(texto)
    except ValueError:  # pedido sem data reconhecível: conta no dia em que chegou
        return hoje_no_brasil()
    if momento.tzinfo is not None:
        momento = momento.astimezone(FUSO_BRASIL)
    return momento.date().isoformat()


def ler_valor(texto):
    """'199.90' -> 199.9; None se não for um número finito."""
    try:
        valor = float(texto or 0)
    except (TypeError, ValueError):
        return None
    return round(valor, 2) if math.isfinite(valor) else None


def ler_aviso(corpo):
    """Corpo JSON do webhook como dict; None se não for um objeto JSON."""
    try:
        aviso = json.loads(corpo or b"{}")
    except ValueError:
        return None
    return aviso if isinstance(aviso, dict) else None


def numero_valido(valor):
    """Número do pedido ou da loja: inteiro positivo, em número ou texto."""
    return not isinstance(valor, bool) and str(valor or "").strip().isdigit()


# ---------- Registro do pedido ----------

def usuario_pelo_email(variavel):
    email = (os.getenv(variavel) or "").strip().lower()
    if not email:
        return None
    linha = obter_conexao().execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()
    return linha["id"] if linha else None


def registrar_pedido(usuario_id, plataforma, pedido_id, data, valor, utm_campanha):
    """Grava o pedido (uma vez só) e soma 1 venda e o valor no dia do teste com essa campanha.
    Um pedido já cancelado (o cancelamento chegou antes do pagamento) também conta como repetido."""
    conexao = obter_conexao()
    if conexao.execute("SELECT 1 FROM pedidos_webhook WHERE plataforma = ? AND pedido_id = ?",
                       (plataforma, pedido_id)).fetchone():
        return {"situacao": "repetido"}

    teste = None
    if utm_campanha:
        # Mesmo nome de campanha em mais de um teste: prefere o que cobre a data, depois o em andamento.
        teste = conexao.execute(
            """SELECT t.id FROM testes_venda t JOIN produtos p ON p.id = t.produto_id
               WHERE p.usuario_id = ? AND t.utm_campanha = ?
               ORDER BY (? BETWEEN t.data_inicio AND t.data_fim) DESC, (t.status = 'em_andamento') DESC,
                        t.data_inicio DESC, t.id DESC
               LIMIT 1""",
            (usuario_id, utm_campanha, data),
        ).fetchone()
    teste_id = teste["id"] if teste else None

    conexao.execute(
        """INSERT INTO pedidos_webhook (usuario_id, plataforma, pedido_id, teste_id, utm_campanha, data, valor)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (usuario_id, plataforma, pedido_id, teste_id, utm_campanha, data, valor),
    )
    if teste_id:
        conexao.execute(
            """INSERT INTO metricas_diarias (teste_id, data, vendas, receita, origem)
               VALUES (?, ?, 1, ?, 'webhook')
               ON CONFLICT (teste_id, data) DO UPDATE SET
                   vendas = vendas + 1, receita = round(receita + excluded.receita, 2)""",
            (teste_id, data, valor),
        )
    conexao.commit()
    if teste_id:
        atualizar_status_pelo_teste(teste_id)
    return {"situacao": "registrado", "teste_id": teste_id}


def cancelar_pedido(usuario_id, plataforma, pedido_id):
    """Marca o pedido como cancelado e desconta 1 venda e o valor do dia em que ele foi somado.

    Cancelamento de pedido que nunca chegou: fica gravado já cancelado (valor 0), para que um
    aviso de pagamento atrasado desse pedido seja tratado como repetido e não conte.
    """
    conexao = obter_conexao()
    pedido = conexao.execute("SELECT * FROM pedidos_webhook WHERE plataforma = ? AND pedido_id = ?",
                             (plataforma, pedido_id)).fetchone()
    if pedido is None:
        conexao.execute(
            """INSERT INTO pedidos_webhook (usuario_id, plataforma, pedido_id, data, valor, cancelado_em)
               VALUES (?, ?, ?, ?, 0, datetime('now', 'localtime'))""",
            (usuario_id, plataforma, pedido_id, hoje_no_brasil()),
        )
        conexao.commit()
        return {"situacao": "cancelado_sem_pagamento"}
    if pedido["cancelado_em"]:
        return {"situacao": "repetido"}

    conexao.execute("UPDATE pedidos_webhook SET cancelado_em = datetime('now', 'localtime') WHERE id = ?",
                    (pedido["id"],))
    if pedido["teste_id"]:
        conexao.execute(
            """UPDATE metricas_diarias SET vendas = max(vendas - 1, 0), receita = max(round(receita - ?, 2), 0)
               WHERE teste_id = ? AND data = ?""",
            (pedido["valor"], pedido["teste_id"], pedido["data"]),
        )
    conexao.commit()
    if pedido["teste_id"]:
        atualizar_status_pelo_teste(pedido["teste_id"])
    return {"situacao": "cancelado", "teste_id": pedido["teste_id"]}


def buscar_pedido_nuvemshop(loja_id, pedido_id):
    """Busca o pedido completo na API da Nuvemshop (o webhook só traz o número)."""
    requisicao = urllib.request.Request(
        f"{API_NUVEMSHOP}/{int(loja_id)}/orders/{int(pedido_id)}",
        headers={"Authentication": f"bearer {os.getenv('NUVEMSHOP_TOKEN_ACESSO', '')}",
                 "User-Agent": f"Validador de Vendas ({os.getenv('NUVEMSHOP_EMAIL_USUARIO', '')})"},
    )
    with urllib.request.urlopen(requisicao, timeout=10) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


# ---------- Rotas ----------

AVISO_INVALIDO = "Aviso inválido: falta o número do pedido ou o corpo não é JSON."


@bp.route("/nuvemshop/webhook", methods=["POST"])
def webhook_nuvemshop():
    segredo = os.getenv("NUVEMSHOP_SEGREDO_APP")
    if not segredo or not os.getenv("NUVEMSHOP_TOKEN_ACESSO"):
        return jsonify(erros=["Integração com a Nuvemshop não configurada no .env."]), 503
    corpo = request.get_data()
    if not assinatura_valida_hex(segredo, corpo, request.headers.get("x-linkedstore-hmac-sha256")):
        return jsonify(erros=["Assinatura inválida."]), 401

    aviso = ler_aviso(corpo)
    if aviso is None or not numero_valido(aviso.get("id")):
        return jsonify(erros=[AVISO_INVALIDO]), 400
    evento = aviso.get("event")
    if evento not in ("order/paid", "order/cancelled"):
        return jsonify(ignorado=f"Evento {evento!r} não é pagamento nem cancelamento."), 200
    usuario_id = usuario_pelo_email("NUVEMSHOP_EMAIL_USUARIO")
    if usuario_id is None:
        return jsonify(erros=["NUVEMSHOP_EMAIL_USUARIO não corresponde a nenhuma conta do sistema."]), 503
    if evento == "order/cancelled":
        return jsonify(cancelar_pedido(usuario_id, "nuvemshop", str(aviso["id"]))), 200

    if not numero_valido(aviso.get("store_id")):
        return jsonify(erros=["Aviso inválido: falta o número da loja."]), 400
    try:
        pedido = buscar_pedido_nuvemshop(aviso["store_id"], aviso["id"])
    except (urllib.error.URLError, TimeoutError, ValueError) as erro:
        # 502 faz a Nuvemshop tentar de novo mais tarde.
        return jsonify(erros=[f"Não foi possível buscar o pedido na Nuvemshop: {erro}"]), 502
    valor = ler_valor(pedido.get("total"))
    if valor is None:
        return jsonify(erros=["A Nuvemshop devolveu um pedido com valor inválido."]), 502

    resultado = registrar_pedido(
        usuario_id, "nuvemshop", str(pedido.get("id", aviso["id"])),
        data_do_pedido(pedido.get("paid_at") or pedido.get("created_at")),
        valor,
        extrair_utm_campanha(pedido, ("landing_url",)),
    )
    return jsonify(resultado), 200


@bp.route("/shopify/webhook", methods=["POST"])
def webhook_shopify():
    segredo = os.getenv("SHOPIFY_SEGREDO_WEBHOOK")
    if not segredo:
        return jsonify(erros=["Integração com a Shopify não configurada no .env."]), 503
    corpo = request.get_data()
    if not assinatura_valida_base64(segredo, corpo, request.headers.get("X-Shopify-Hmac-Sha256")):
        return jsonify(erros=["Assinatura inválida."]), 401

    pedido = ler_aviso(corpo)
    if pedido is None or not numero_valido(pedido.get("id")):
        return jsonify(erros=[AVISO_INVALIDO]), 400
    topico = request.headers.get("X-Shopify-Topic", "orders/paid")
    if topico not in ("orders/paid", "orders/cancelled"):
        return jsonify(ignorado=f"Evento {topico!r} não é pagamento nem cancelamento."), 200
    usuario_id = usuario_pelo_email("SHOPIFY_EMAIL_USUARIO")
    if usuario_id is None:
        return jsonify(erros=["SHOPIFY_EMAIL_USUARIO não corresponde a nenhuma conta do sistema."]), 503
    if topico == "orders/cancelled":
        return jsonify(cancelar_pedido(usuario_id, "shopify", str(pedido["id"]))), 200

    valor = ler_valor(pedido.get("total_price"))
    if valor is None:
        return jsonify(erros=["Valor do pedido inválido."]), 400
    resultado = registrar_pedido(
        usuario_id, "shopify", str(pedido["id"]),
        data_do_pedido(pedido.get("processed_at") or pedido.get("created_at")),
        valor,
        extrair_utm_campanha(pedido, ("landing_site",)),
    )
    return jsonify(resultado), 200


@bp.route("/pedidos")
@login_obrigatorio
def listar_pedidos():
    """Últimos 50 pedidos recebidos pelos webhooks, com o teste a que foram ligados."""
    linhas = obter_conexao().execute(
        """SELECT w.plataforma, w.pedido_id, w.data, w.valor, w.utm_campanha, w.recebido_em, w.teste_id,
                  w.cancelado_em, t.canal, p.nome AS produto_nome
           FROM pedidos_webhook w
           LEFT JOIN testes_venda t ON t.id = w.teste_id
           LEFT JOIN produtos p ON p.id = t.produto_id
           WHERE w.usuario_id = ? ORDER BY w.recebido_em DESC, w.id DESC LIMIT 50""",
        (session["usuario_id"],),
    ).fetchall()
    return jsonify([dict(linha) for linha in linhas])
