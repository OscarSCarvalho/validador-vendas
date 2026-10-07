"""Cadastro, login e logout com sessão do Flask (API JSON)."""
import sqlite3
from functools import wraps

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from banco import obter_conexao

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

TAMANHO_MINIMO_SENHA = 6


def login_obrigatorio(funcao):
    @wraps(funcao)
    def envolvida(*args, **kwargs):
        if not session.get("usuario_id"):
            return jsonify(erros=["Faça login para continuar."]), 401
        return funcao(*args, **kwargs)
    return envolvida


def ler_json():
    """Corpo da requisição como dict (vazio se não vier JSON)."""
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def texto(dados, campo):
    return str(dados.get(campo) or "").strip()


def usuario_json(usuario):
    return {"id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"]}


def iniciar_sessao(usuario):
    session.clear()
    session["usuario_id"] = usuario["id"]


@bp.route("/cadastro", methods=["POST"])
def cadastro():
    dados = ler_json()
    nome = texto(dados, "nome")
    email = texto(dados, "email").lower()
    senha = str(dados.get("senha") or "")

    erros = []
    if not nome:
        erros.append("Informe seu nome.")
    if not email or "@" not in email:
        erros.append("Informe um e-mail válido.")
    if len(senha) < TAMANHO_MINIMO_SENHA:
        erros.append(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
    if erros:
        return jsonify(erros=erros), 400

    conexao = obter_conexao()
    try:
        cursor = conexao.execute(
            "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
            (nome, email, generate_password_hash(senha)),
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        return jsonify(erros=["Este e-mail já está cadastrado."]), 409

    usuario = {"id": cursor.lastrowid, "nome": nome, "email": email}
    iniciar_sessao(usuario)  # já entra logado após o cadastro
    return jsonify(usuario), 201


@bp.route("/login", methods=["POST"])
def login():
    dados = ler_json()
    email = texto(dados, "email").lower()
    senha = str(dados.get("senha") or "")
    usuario = obter_conexao().execute(
        "SELECT * FROM usuarios WHERE email = ?", (email,)
    ).fetchone()

    if usuario is None or not check_password_hash(usuario["senha_hash"], senha):
        return jsonify(erros=["E-mail ou senha incorretos."]), 401

    iniciar_sessao(usuario)
    return jsonify(usuario_json(usuario))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return "", 204


@bp.route("/eu")
@login_obrigatorio
def eu():
    usuario = obter_conexao().execute(
        "SELECT * FROM usuarios WHERE id = ?", (session["usuario_id"],)
    ).fetchone()
    if usuario is None:  # sessão de um usuário que não existe mais
        session.clear()
        return jsonify(erros=["Faça login para continuar."]), 401
    return jsonify(usuario_json(usuario))
