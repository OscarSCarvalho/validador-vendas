"""Conexão com o SQLite (sqlite3 puro) e criação do schema."""
import os
import sqlite3

from flask import current_app, g

PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))


def obter_conexao():
    """Retorna a conexão da requisição atual (uma por requisição)."""
    if "conexao" not in g:
        g.conexao = sqlite3.connect(current_app.config["CAMINHO_BANCO"])
        g.conexao.row_factory = sqlite3.Row
        g.conexao.execute("PRAGMA foreign_keys = ON")
    return g.conexao


def fechar_conexao(erro=None):
    conexao = g.pop("conexao", None)
    if conexao is not None:
        conexao.close()


# Colunas criadas depois da tabela existir. Bancos antigos ganham a coluna no próximo início.
COLUNAS_ADICIONADAS = {
    "produtos": [
        ("modelo", "TEXT NOT NULL DEFAULT 'vendedor' CHECK (modelo IN ('vendedor', 'afiliado'))"),
        ("taxa_comissao", "REAL CHECK (taxa_comissao IS NULL OR (taxa_comissao > 0 AND taxa_comissao <= 100))"),
    ],
}


def migrar(conexao):
    """Acrescenta as colunas novas que faltarem (ALTER TABLE ADD COLUMN)."""
    for tabela, colunas in COLUNAS_ADICIONADAS.items():
        existentes = {linha[1] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}
        for nome, definicao in colunas:
            if nome not in existentes:
                conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}")


def criar_schema(caminho_banco):
    """Executa o schema.sql e as migrações. Seguro rodar várias vezes."""
    with open(os.path.join(PASTA_PROJETO, "schema.sql"), encoding="utf-8") as arquivo:
        script = arquivo.read()
    conexao = sqlite3.connect(caminho_banco)
    try:
        conexao.executescript(script)
        migrar(conexao)
        conexao.commit()
    finally:
        conexao.close()


def iniciar_banco(app):
    criar_schema(app.config["CAMINHO_BANCO"])
    app.teardown_appcontext(fechar_conexao)
