import os

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from banco import PASTA_PROJETO, iniciar_banco
from rotas.auth import bp as bp_auth
from rotas.integracoes import bp as bp_integracoes
from rotas.painel import bp as bp_painel
from rotas.pontuacao import bp as bp_pontuacao
from rotas.produtos import bp as bp_produtos
from rotas.testes import bp as bp_testes
from rotas.validacao import bp as bp_validacao

load_dotenv(os.path.join(PASTA_PROJETO, ".env"))

# Build do React (npm run build). Em produção o Flask serve esta pasta.
PASTA_DIST = os.path.join(PASTA_PROJETO, "..", "frontend", "dist")

CHAVE_DE_EXEMPLO = "troque-esta-chave"  # a do .env.example: não serve para assinar sessões


class ChaveSecretaAusente(RuntimeError):
    """O .env não existe ou o SECRET_KEY ainda é o de exemplo."""


def criar_app(config_extra=None):
    app = Flask(__name__, static_folder=None)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "").strip()
    app.config["CAMINHO_BANCO"] = os.path.join(
        PASTA_PROJETO, os.getenv("CAMINHO_BANCO", "validador.db")
    )
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024  # uploads de CSV (o limite do arquivo é 2 MB)
    if config_extra:
        app.config.update(config_extra)
    if app.config["SECRET_KEY"] in ("", CHAVE_DE_EXEMPLO):
        if not app.config.get("TESTING"):
            raise ChaveSecretaAusente(
                "SECRET_KEY não configurado. Copie backend/.env.example para backend/.env e troque o SECRET_KEY "
                "por uma chave aleatória (gere com: python -c \"import secrets; print(secrets.token_hex(32))\").")
        app.config["SECRET_KEY"] = "chave-so-para-os-testes"

    iniciar_banco(app)

    for bp in (bp_auth, bp_produtos, bp_pontuacao, bp_validacao,
               bp_testes, bp_painel, bp_integracoes):
        app.register_blueprint(bp)

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        """Erros da API (404, 405...) em JSON; fora da API, a página padrão."""
        if request.path.startswith("/api/"):
            if erro.code == 413:
                return jsonify(erros=["Arquivo grande demais (máximo de 2 MB)."]), 413
            return jsonify(erros=[erro.description]), erro.code
        return erro

    @app.route("/", defaults={"caminho": ""})
    @app.route("/<path:caminho>")
    def frontend(caminho):
        """Serve o build do React; rotas do React (/produtos, /login...) caem no index.html."""
        if caminho.startswith("api/"):
            abort(404)
        if caminho and os.path.isfile(os.path.join(PASTA_DIST, caminho)):
            return send_from_directory(PASTA_DIST, caminho)
        if not os.path.isfile(os.path.join(PASTA_DIST, "index.html")):
            return ("Frontend não compilado. Em desenvolvimento, abra o Vite em "
                    "http://localhost:5173; para produção, rode 'npm run build' em frontend/."), 404
        return send_from_directory(PASTA_DIST, "index.html")

    return app


if __name__ == "__main__":
    criar_app().run(debug=True)
