# Projeto: Validador de Vendas (sistema para impulsionar vendas)

## Contexto
Sou iniciante no mercado digital de produtos físicos. Quero um sistema que me ajude a validar, passo a passo, se vale a pena vender um produto que está hospedado em uma plataforma ou SaaS (Nuvemshop, Shopify, Mercado Livre etc.).

A regra principal: **primeiro valido manualmente, depois automatizo**. O sistema deve funcionar desde o primeiro dia com lançamento manual de dados. Integrações automáticas vêm só nas últimas etapas.

Primeiro caso de uso real: hardware da Yep Solutions (ex.: leitor de código de barras) revendido pelo site da Athos Tecnologia.

**Atualização:** sou **afiliado da Shopee, pessoa física**. Não tenho estoque nem pago taxas de vendedor: divulgo produtos
de outros vendedores com meu link de afiliado e ganho **comissão** sobre as compras feitas até **7 dias após o clique**
(comissão padrão de 3%; até 30% em produtos com Comissão Extra; calculada sobre o valor líquido, sem frete e cupons).
O rastreio de campanha na Shopee é feito pelo **Sub_id** do link de afiliado (a UTM não chega ao pedido).
O sistema deve suportar os dois modelos (`vendedor` e `afiliado`), com foco no afiliado.

## Stack obrigatória (não trocar)
- Python + Flask
- sqlite3 puro (sem SQLAlchemy, sem ORM)
- Autenticação por sessão com Werkzeug (`generate_password_hash` / `check_password_hash`). Sem JWT.
- Backend Flask funciona só como **API JSON** (rotas em `/api/...`).
- Frontend em **React com JavaScript** (sem TypeScript), criado com Vite.
  - Rotas com `react-router-dom`; estilo com Bootstrap 5 (importar o CSS, sem react-bootstrap); gráficos com `chart.js` + `react-chartjs-2`.
  - Estado com `useState`/`useEffect` e Context só para o usuário logado. Sem Redux ou outra lib de estado.
  - Chamadas à API com `fetch` e `credentials: "include"`, centralizadas em `src/api.js`.
- Autenticação continua por sessão (cookie do Flask). Em desenvolvimento, o Vite faz proxy de `/api` para o Flask (mesma origem, sem CORS). Em produção, o Flask serve a pasta `dist` do build.
- Nomes de tabelas, colunas, funções e rotas da API em português, snake_case. Componentes React em PascalCase com nomes em português (ex.: `ListaProdutos.jsx`).
- Mínimo de dependências. Python: `flask`, `werkzeug`, `python-dotenv`. JS: `react`, `react-dom`, `react-router-dom`, `bootstrap`, `chart.js`, `react-chartjs-2`. Peça permissão antes de adicionar qualquer outra.
- Cenários de teste e bugs documentados em BDD (Dado / Quando / Então).
- Interface responsiva (uso no celular também).

## Estrutura sugerida
```
validador/
  backend/
    app.py
    banco.py          # conexão sqlite3 e criação do schema
    schema.sql
    regras.py         # cálculos de pontuação, margem, funil e veredito (funções puras)
    rotas/            # blueprints da API: auth, produtos, pontuacao, validacao, testes, painel, integracoes
    testes/           # testes das funções de regras.py e das rotas
    .env.example
  frontend/
    src/
      api.js          # todas as chamadas fetch
      contexto/       # UsuarioContexto
      paginas/        # Login, ListaProdutos, Produto, Pontuacao, Validacao, TesteVenda, Painel
      componentes/    # Funil, CardIndicador, Veredito, BotoesNota, GeradorUtm
      App.jsx
      main.jsx
    vite.config.js    # proxy /api → Flask
  README.md           # como rodar backend e frontend
```

## Modelo de dados
- `usuarios` (id, nome, email, senha_hash, criado_em)
- `produtos` (id, usuario_id, nome, plataforma, url_produto, preco_venda, custo_unitario, status, criado_em)
  - status: `ideia`, `pontuado`, `em_validacao`, `em_teste`, `escalar`, `ajustar`, `descartado`
- `pontuacoes` (id, produto_id, demanda, concorrencia, margem, frete, facilidade_explicar, total, veredito, criado_em)
- `validacao_manual` (id, produto_id, etapa, concluida, observacao, link_evidencia, atualizado_em)
- `testes_venda` (id, produto_id, canal, utm_campanha, verba_diaria, data_inicio, data_fim, status)
- `metricas_diarias` (id, teste_id, data, investimento, impressoes, cliques, visitas, carrinhos, vendas, receita, origem)
  - origem: `manual`, `csv`, `webhook`

## Regras de negócio (ficam em regras.py, no backend)
O backend calcula e devolve os resultados na API; o React só exibe. Não duplicar regras no frontend.

**Margem**
- margem_unitaria = preco_venda − custo_unitario (custo inclui produto, frete, taxas da plataforma e impostos)
- margem_percentual = margem_unitaria / preco_venda

**Pontuação (5 critérios, nota de 1 a 5, total até 25)**
- demanda: aparece nos mais vendidos e tem buscas constantes
- concorrencia: há vendedores ativos, mas espaço para se diferenciar
- margem: automática pela margem_percentual → ≥50% = 5; ≥40% = 4; ≥30% = 3; ≥20% = 2; abaixo = 1
- frete: leve, pequeno, difícil de quebrar
- facilidade_explicar: o benefício cabe em uma frase e em um vídeo curto

Veredito da pontuação: total ≥ 18 = "Vale testar"; 13 a 17 = "Testar com cautela"; abaixo de 13 = "Descartar".

**Funil e indicadores**
- CTR = cliques / impressões
- taxa de conversão = vendas / visitas
- abandono de carrinho = 1 − (vendas / carrinhos)
- CPA (custo por venda) = investimento / vendas
- lucro do teste = (vendas × margem_unitaria) − investimento
- Tratar divisão por zero mostrando "–".

**Veredito do teste**
- CPA ≤ 70% da margem_unitaria → "Escalar"
- CPA entre 70% e 100% → "Ajustar" (criativo, preço ou página)
- CPA > 100% → "Trocar de produto"
- Sem vendas: se investimento > margem_unitaria → "Trocar"; senão → "Continue testando"

## Etapas de validação manual (checklist por produto)
1. Escolher 1 produto e 1 público (nicho definido em uma frase)
2. Pesquisar demanda: mais vendidos (Mercado Livre, Shopee), Google Trends, volume de buscas
3. Analisar concorrentes: Biblioteca de Anúncios da Meta, preços praticados
4. Montar oferta mínima: landing page simples com link para o produto na plataforma
5. Gerar links com UTM para cada canal
6. Rodar teste com verba pequena (R$ 30 a 50/dia por 7 dias) ou canal orgânico (WhatsApp, grupos)
7. Registrar métricas diariamente
8. Tomar a decisão: escalar, ajustar ou trocar

Cada etapa tem: concluída (sim/não), observação e link de evidência.

---

## Como trabalhar comigo
- Construa **uma etapa por vez**, na ordem abaixo.
- Ao terminar cada etapa: rode o backend e o frontend, rode os testes, me mostre o que mudou e como testar, e **pare para eu aprovar** antes de seguir.
- Não implemente nada de etapas futuras antecipadamente.
- Mantenha tudo simples. Se houver duas formas, escolha a mais simples e me diga em uma linha.

## Etapas de desenvolvimento

### Etapa 1: Base
- Backend: estrutura de pastas, `schema.sql`, `banco.py`, `app.py`, blueprints vazios.
- Frontend: projeto Vite + React (JavaScript), proxy `/api`, `api.js`, rotas e layout base com Bootstrap (menu: Produtos, Painel).
- Cadastro, login e logout com sessão; rotas protegidas no React redirecionam para Login.
- API e telas de CRUD de produtos (nome, plataforma, url_produto, preco_venda, custo_unitario).
- Cenário: Dado que estou logado, Quando cadastro um produto com preço 200 e custo 110, Então vejo a margem de R$ 90,00 (45%).

### Etapa 2: Pontuação
- Página de pontuação com o componente `BotoesNota` (1 a 5) por critério.
- Margem preenchida automaticamente e bloqueada para edição.
- Exibe total e veredito em destaque (verde, âmbar, vermelho).
- Salva histórico em `pontuacoes` e atualiza o status do produto.
- Testes unitários das funções de pontuação e margem.

### Etapa 3: Validação manual guiada
- Checklist das 8 etapas por produto, com observação e link de evidência.
- Barra de progresso (x de 8 concluídas).
- Gerador de link UTM (url_produto + utm_source, utm_medium, utm_campaign) com botão copiar.

### Etapa 4: Teste de venda
- Criar teste (canal, utm_campanha, verba diária, datas).
- Lançamento diário de métricas (formulário rápido, pensado para celular, sem recarregar a página).
- Tela do teste: funil em barras (impressões → cliques → visitas → carrinhos → vendas) com taxa entre etapas, cards de CTR, conversão, CPA e lucro, e o veredito com barra de CPA × margem.
- Atualiza o status do produto conforme o veredito.

### Etapa 5: Painel comparativo
- Lista de todos os produtos com status, pontuação, CPA, lucro e veredito.
- Filtro por status. Ordenar por lucro.
- Gráfico simples de investimento × receita por dia do teste selecionado.

### Etapa 6: Importação CSV
- Upload de CSV com métricas diárias (exportado do gerenciador de anúncios ou da plataforma).
- Mapeamento simples de colunas e prévia antes de gravar (origem = `csv`).

### Etapa 7: Integração com a plataforma
- Endpoint Flask para webhook de pedidos (começar pela Nuvemshop; deixar a Shopify preparada no mesmo formato).
- Validar a assinatura do webhook com o segredo do `.env`.
- Associar pedido ao teste pela `utm_campaign`; somar vendas e receita do dia (origem = `webhook`).
- Alerta na tela quando o CPA passar da margem ou a conversão cair mais de 30% em relação à média do teste.
- Opcional, só se eu pedir: usar n8n para buscar dados de anúncios e enviar ao sistema.

---

Etapas 1 a 7 concluídas. Próxima: **Etapa 8**.

### Para evolução do sistema
- sistema deve de alguma forma ajudar a encontrar produtos que valhe a pena vender
- criar de alguma forma algoritimos que nos direciona produtos mais vendidos
- captura produtos mais visistados
- Criaçao de promoçoes  com produtos que encontramos com mais visitados
- Sistema deve me indicar como criar campanhas/anuncios (com IA)
- integraçao com shoppe para que venhamos pegar informaçoes de cliques visitas vendas, desistencias
- Dashboard dos meus produtos visitados, vendidos desistencias quando usuario entra pra compra desisiteava

### Etapas de evolução (modelo afiliado Shopee)

Ordem pensada para: primeiro funcionar com dados manuais e CSV; depois a API oficial de afiliados;
por último, IA. Os itens acima estão cobertos assim: encontrar produtos e mais vendidos (Etapa 11),
mais visitados e dashboard (Etapas 9 e 12), promoções (Etapa 13, adaptada para afiliado: ofertas para divulgar),
campanhas com IA (Etapa 13), integração com a Shopee (Etapas 9 e 10).

Limites conhecidos: a Shopee não fornece visitas nem "mais vendidos" de outros vendedores fora da API de afiliados,
e copiar páginas da Shopee (scraping) viola os termos de uso; não fazer. Afiliado não vê carrinho: "desistência"
= cliques sem compra e pedidos cancelados.

### Etapa 8: Modo afiliado
- Produto com `modelo` = `vendedor` (preço e custo) ou `afiliado` (preço do produto e `taxa_comissao` em %; sem custo).
- Comissão por venda = preço × taxa de comissão. Ela faz o papel da margem unitária em todas as regras (pontuação, CPA, veredito, alertas).
- Nota da margem do afiliado pela comissão em R$: ≥ R$ 20 = 5; ≥ R$ 10 = 4; ≥ R$ 5 = 3; ≥ R$ 2 = 2; abaixo = 1.
- Teste de venda do afiliado: "visitas" = cliques no link de afiliado; sem carrinhos; "receita" = comissão recebida;
  lucro = comissão recebida − investimento. A campanha do teste é o **Sub_id** do link.
- Na validação, o gerador de UTM vira orientação de Sub_id para produtos de afiliado.

### Etapa 9: Importar relatórios do Painel de Afiliados (CSV)
- Relatório de conversões (pedidos, status, comissão, Sub_id) e de cliques, ligados ao teste pelo Sub_id.
- Pedidos cancelados não contam como venda e aparecem como desistência. Prévia antes de gravar (origem = `csv`).

### Etapa 10: API de Afiliados da Shopee
- Credenciais (App ID e Secret) no `.env`; assinatura SHA256 da API de afiliados.
- Gerar link curto de afiliado com Sub_id direto do sistema.
- Sincronizar conversões por um botão (o sistema busca os dados; funciona no computador local, sem endereço público).

### Etapa 11: Encontrar produtos
- Busca de ofertas na API de afiliados por palavra-chave, ordenada por vendas ou comissão.
- Ranking com comissão em R$, vendas, avaliação e desconto, e o CPA máximo para anunciar sem prejuízo.
- Botão para adicionar a oferta como produto de afiliado.

### Etapa 12: Painel do afiliado
- Por produto e por campanha (Sub_id): cliques, pedidos, comissão, cancelamentos e conversão.
- Produtos mais clicados e mais vendidos.

### Etapa 13: Ofertas e campanhas com IA
- Lista de ofertas para divulgar (maior comissão, desconto ativo, mais vendidos).
- Assistente com IA (API do Claude) para texto de anúncio, ganchos, público e orçamento a partir do CPA máximo.
  Exige chave da API e aprovação da dependência.
