CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS produtos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    nome            TEXT NOT NULL,
    plataforma      TEXT NOT NULL,
    url_produto     TEXT,
    preco_venda     REAL NOT NULL CHECK (preco_venda > 0),
    custo_unitario  REAL NOT NULL CHECK (custo_unitario >= 0),
    status          TEXT NOT NULL DEFAULT 'ideia'
                    CHECK (status IN ('ideia','pontuado','em_validacao','em_teste',
                                      'escalar','ajustar','descartado')),
    criado_em       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    -- Etapa 8: 'vendedor' (preço − custo) ou 'afiliado' (comissão = preço × taxa_comissao %)
    modelo          TEXT NOT NULL DEFAULT 'vendedor' CHECK (modelo IN ('vendedor', 'afiliado')),
    taxa_comissao   REAL CHECK (taxa_comissao IS NULL OR (taxa_comissao > 0 AND taxa_comissao <= 100))
);

CREATE TABLE IF NOT EXISTS pontuacoes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id           INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    demanda              INTEGER NOT NULL CHECK (demanda BETWEEN 1 AND 5),
    concorrencia         INTEGER NOT NULL CHECK (concorrencia BETWEEN 1 AND 5),
    margem               INTEGER NOT NULL CHECK (margem BETWEEN 1 AND 5),
    frete                INTEGER NOT NULL CHECK (frete BETWEEN 1 AND 5),
    facilidade_explicar  INTEGER NOT NULL CHECK (facilidade_explicar BETWEEN 1 AND 5),
    total                INTEGER NOT NULL CHECK (total BETWEEN 5 AND 25),
    veredito             TEXT NOT NULL
                         CHECK (veredito IN ('vale_testar','testar_com_cautela','descartar')),
    criado_em            TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS validacao_manual (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id      INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    etapa           INTEGER NOT NULL CHECK (etapa BETWEEN 1 AND 8),
    concluida       INTEGER NOT NULL DEFAULT 0 CHECK (concluida IN (0, 1)),
    observacao      TEXT,
    link_evidencia  TEXT,
    atualizado_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (produto_id, etapa)
);

CREATE TABLE IF NOT EXISTS testes_venda (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id    INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    canal         TEXT NOT NULL,
    utm_campanha  TEXT NOT NULL,
    verba_diaria  REAL NOT NULL CHECK (verba_diaria >= 0),
    data_inicio   TEXT NOT NULL,
    data_fim      TEXT NOT NULL CHECK (data_fim >= data_inicio),
    status        TEXT NOT NULL DEFAULT 'em_andamento'
                  CHECK (status IN ('em_andamento', 'encerrado'))
);

CREATE TABLE IF NOT EXISTS metricas_diarias (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    teste_id      INTEGER NOT NULL REFERENCES testes_venda(id) ON DELETE CASCADE,
    data          TEXT NOT NULL,
    investimento  REAL NOT NULL DEFAULT 0 CHECK (investimento >= 0),
    impressoes    INTEGER NOT NULL DEFAULT 0 CHECK (impressoes >= 0),
    cliques       INTEGER NOT NULL DEFAULT 0 CHECK (cliques >= 0),
    visitas       INTEGER NOT NULL DEFAULT 0 CHECK (visitas >= 0),
    carrinhos     INTEGER NOT NULL DEFAULT 0 CHECK (carrinhos >= 0),
    vendas        INTEGER NOT NULL DEFAULT 0 CHECK (vendas >= 0),
    receita       REAL NOT NULL DEFAULT 0 CHECK (receita >= 0),
    origem        TEXT NOT NULL DEFAULT 'manual' CHECK (origem IN ('manual', 'csv', 'webhook')),
    UNIQUE (teste_id, data)
);

CREATE TABLE IF NOT EXISTS pedidos_webhook (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    plataforma    TEXT NOT NULL CHECK (plataforma IN ('nuvemshop', 'shopify')),
    pedido_id     TEXT NOT NULL,
    teste_id      INTEGER REFERENCES testes_venda(id) ON DELETE SET NULL,
    utm_campanha  TEXT,
    data          TEXT NOT NULL,
    valor         REAL NOT NULL,
    recebido_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    -- Preenchido quando a loja avisa o cancelamento: o pedido deixa de contar como venda.
    cancelado_em  TEXT,
    UNIQUE (plataforma, pedido_id)
);
