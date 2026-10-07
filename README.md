# Validador de Vendas

Sistema web para descobrir, **com dados e passo a passo**, se vale a pena vender um produto físico
hospedado em uma plataforma (Nuvemshop, Shopify, Mercado Livre, Shopee etc.) **antes de investir pesado nele**.

Funciona para quem **vende com estoque** (margem = preço − custo) e para **afiliados da Shopee**
(margem = comissão por venda, rastreada pelo Sub_id do link de afiliado).

> Regra principal: **primeiro valide manualmente, depois automatize.**
> O sistema funciona desde o primeiro dia só com dados digitados à mão. Importação de planilhas e
> integração automática com a loja vêm depois, como apoio.

---

## Sumário

1. [Para que serve](#para-que-serve)
2. [O método em 5 passos](#o-método-em-5-passos)
3. [Funcionalidades](#funcionalidades)
4. [Regras de cálculo](#regras-de-cálculo)
5. [Tecnologias](#tecnologias)
6. [Como foi feito](#como-foi-feito)
7. [Estrutura de pastas](#estrutura-de-pastas)
8. [Instalação passo a passo](#instalação-passo-a-passo)
9. [Como usar passo a passo](#como-usar-passo-a-passo)
10. [Importação de CSV](#importação-de-csv)
11. [Integração com Nuvemshop e Shopify](#integração-com-nuvemshop-e-shopify)
12. [Testes](#testes)
13. [Colocando em produção](#colocando-em-produção)
14. [Referência da API](#referência-da-api)
15. [Situação atual e limitações conhecidas](#situação-atual-e-limitações-conhecidas)

---

## Para que serve

Quem está começando a vender produtos físicos pela internet costuma errar de dois jeitos:
escolhe o produto "no feeling" ou gasta em anúncios sem saber quanto pode pagar por cada venda.
O Validador de Vendas resolve isso transformando a decisão em um processo com números:

- **Antes de anunciar:** calcula a margem real do produto e dá uma nota para ele em 5 critérios.
- **Durante a validação:** guia você por um checklist de 8 etapas, com espaço para anotar e guardar provas
  (links de pesquisa, prints, concorrentes).
- **Durante o teste de venda:** registra os números de cada dia (investimento, cliques, visitas,
  carrinhos, vendas) e mostra o funil, o custo por venda (CPA), o lucro e um **veredito claro**:
  **Escalar**, **Ajustar** ou **Trocar de produto**.
- **Na hora de decidir:** um painel compara todos os produtos lado a lado, ordenados por lucro.

**Primeiro caso de uso real:** hardware da Yep Solutions (ex.: leitor de código de barras),
revendido pelo site da Athos Tecnologia.

---

## O método em 5 passos

```
  1. Cadastrar        2. Pontuar          3. Validar           4. Testar             5. Decidir
  ───────────►        ───────────►        ───────────►         ───────────►          ───────────
  preço e custo       5 critérios         8 etapas             verba pequena         Escalar
  = margem            nota até 25         + links UTM          7 dias                Ajustar
                                                               métricas diárias      Trocar
```

Cada produto tem um **status** que acompanha essa jornada:

| Status | Quando acontece |
|---|---|
| **Ideia** | o produto acabou de ser cadastrado |
| **Pontuado** | recebeu a primeira pontuação |
| **Em validação** | a primeira etapa do checklist foi concluída |
| **Em teste** | um teste de venda foi criado (ou ainda não há vendas suficientes para decidir) |
| **Escalar** / **Ajustar** / **Descartado** | veredito do teste de venda mais recente |

---

## Funcionalidades

| Módulo | O que faz |
|---|---|
| **Conta** | cadastro, login e logout; cada usuário só vê os próprios produtos |
| **Produtos** | dois modelos: **vendedor** (preço e custo) ou **afiliado** (preço e % de comissão); a margem ou a comissão em R$ e em % aparece na hora |
| **Pontuação** | notas de 1 a 5 em demanda, concorrência, frete e facilidade de explicar; a nota da margem é automática; total até 25, com veredito colorido e histórico |
| **Validação manual** | checklist das 8 etapas com observação e link de evidência, barra de progresso e **gerador de links UTM** com botão copiar |
| **Teste de venda** | canal, campanha, verba e período; lançamento diário rápido (pensado para o celular); funil em barras, cards de CTR, conversão, CPA e lucro; veredito com barra de CPA × margem |
| **Painel** | todos os produtos com status, pontuação, CPA, lucro e veredito; filtro por status; ordenação por lucro; gráfico de investimento × receita por dia |
| **Importação de CSV** | envia o relatório do gerenciador de anúncios ou a planilha de pedidos; o sistema sugere qual coluna é qual e mostra uma prévia antes de gravar |
| **Integração** | recebe automaticamente os pedidos pagos da Nuvemshop (e da Shopify) e soma a venda no teste certo pela `utm_campaign` |
| **Alertas** | aviso na tela quando o CPA passa da margem ou quando a conversão cai mais de 30% |

Tudo funciona no computador e no celular.

---

## Regras de cálculo

Todas as regras ficam em um único lugar no backend (`backend/regras.py`). A tela só exibe o resultado.

**Margem**
- Margem unitária = preço de venda − custo unitário
  *(o custo deve somar produto, frete, taxas da plataforma e impostos)*
- Margem % = margem unitária ÷ preço de venda

**Modo afiliado (Shopee)**
- Comissão por venda = preço × % de comissão. Ela faz o papel da margem unitária em todas as regras.
- Nota da margem do afiliado pela comissão em R$: ≥ R$ 20 = 5 · ≥ R$ 10 = 4 · ≥ R$ 5 = 3 · ≥ R$ 2 = 2 · abaixo = 1.
- No teste de venda: "visitas" = cliques no link de afiliado, não há carrinho, "receita" = comissão recebida
  e **lucro = comissão recebida − investimento**.
- A campanha do teste é o **Sub_id** do link de afiliado (na Shopee a UTM não chega ao pedido).
- **Veredito do afiliado** pelo que você recebeu de fato: razão = investimento ÷ comissão recebida.
  - Menos de **3 dias** lançados → **Continue testando** (um clique ainda pode virar comissão em até 7 dias).
  - A partir de 3 dias: até 70% → **Escalar** · até 100% → **Ajustar** · acima, ou sem nenhuma comissão → **Trocar**.
  - Exemplo: R$ 90 investidos em 3 dias e R$ 135 de comissão = 66,7% → **Escalar** (lucro de R$ 45).

**Pontuação** (5 critérios, nota de 1 a 5, total até 25)

| Critério | O que significa nota alta |
|---|---|
| Demanda | aparece nos mais vendidos e tem buscas constantes |
| Concorrência | há vendedores ativos, mas espaço para se diferenciar |
| Margem *(automática)* | ≥ 50% = 5 · ≥ 40% = 4 · ≥ 30% = 3 · ≥ 20% = 2 · abaixo = 1 |
| Frete | leve, pequeno, difícil de quebrar |
| Facilidade de explicar | o benefício cabe em uma frase e em um vídeo curto |

Veredito: **18 ou mais = Vale testar** · **13 a 17 = Testar com cautela** · **abaixo de 13 = Descartar**.

**Funil e indicadores** (somando todos os dias do teste)
- CTR = cliques ÷ impressões
- Taxa de conversão = vendas ÷ visitas
- Abandono de carrinho = 1 − (vendas ÷ carrinhos)
- CPA (custo por venda) = investimento ÷ vendas
- Lucro do teste = (vendas × margem unitária) − investimento
- Quando a conta divide por zero, a tela mostra "–".

**Veredito do teste**
- CPA até 70% da margem unitária → **Escalar**
- CPA entre 70% e 100% da margem → **Ajustar** (criativo, preço ou página)
- CPA acima de 100% da margem → **Trocar de produto**
- Sem vendas: se o investimento já passou da margem → **Trocar**; senão → **Continue testando**

**Alertas**
- O CPA acumulado do teste passou da margem por venda (afiliado: o investimento passou da comissão recebida).
- A conversão do último dia com visitas caiu mais de 30% em relação à média dos dias anteriores.

---

## Tecnologias

| Parte | Tecnologia | Por quê |
|---|---|---|
| Backend | **Python + Flask** | simples e direto; funciona só como **API JSON** (rotas em `/api/...`) |
| Banco de dados | **SQLite** com `sqlite3` puro (sem ORM) | um único arquivo, nada para instalar; SQL legível |
| Autenticação | **Sessão do Flask** + senhas com hash do **Werkzeug** | sem JWT; o cookie de sessão basta |
| Configuração | **python-dotenv** | segredos no arquivo `.env`, fora do código |
| Frontend | **React** (JavaScript, sem TypeScript) criado com **Vite** | telas rápidas e atualização sem recarregar a página |
| Rotas da tela | **react-router-dom** | navegação entre as páginas |
| Visual | **Bootstrap 5** | layout responsivo pronto (celular e computador) |
| Gráficos | **Chart.js** + **react-chartjs-2** | gráfico de investimento × receita no Painel |
| Ícones | SVG do Bootstrap Icons colado no código | sem biblioteca extra |
| Testes | **unittest** (vem com o Python) | 149 testes, com cenários escritos em **Dado / Quando / Então** |

**Dependências de propósito mínimas:**
- Python: `flask`, `werkzeug`, `python-dotenv`.
- JavaScript: `react`, `react-dom`, `react-router-dom`, `bootstrap`, `chart.js`, `react-chartjs-2`
  (mais `vite` e `@vitejs/plugin-react` para desenvolver).
- A leitura de CSV, a assinatura dos webhooks e a chamada à API da Nuvemshop usam só a biblioteca padrão do Python.

**Como as partes conversam:**

```
  Navegador (React)  ──fetch /api/...──►  Vite (localhost:5173)  ──proxy──►  Flask (localhost:5000)  ──►  SQLite
                                                                                   ▲
  Nuvemshop / Shopify ───────────── webhook de pedido pago (HTTPS público) ────────┘
```

Em desenvolvimento, o Vite repassa as chamadas `/api` para o Flask. Por isso tudo fica na mesma origem,
sem CORS, e o cookie de sessão funciona. Em produção, o próprio Flask serve as telas já compiladas (`frontend/dist`).

---

## Como foi feito

O projeto foi construído **em 7 etapas**, uma de cada vez, seguindo a especificação do arquivo
[`CLAUDE.md`](CLAUDE.md). Ele foi desenvolvido com a ajuda do Claude Code (assistente de programação com IA).
Em cada etapa:

1. Antes de programar, eram apresentados as tabelas, as rotas da API e as decisões em aberto, para aprovação.
2. O código era escrito com testes automáticos, incluindo cenários em linguagem de negócio
   (*"Dado um produto com preço 200 e custo 110, Quando… Então vejo a margem de R$ 90,00 (45%)"*).
3. O sistema era aberto num navegador real, no tamanho de computador e de celular, para conferir as telas.
4. O trabalho parava até a etapa ser aprovada.

| Etapa | Entrega |
|---|---|
| 1. Base | estrutura, banco, cadastro/login, CRUD de produtos com margem |
| 2. Pontuação | 5 critérios, total até 25, veredito colorido e histórico |
| 3. Validação manual | checklist de 8 etapas, progresso e gerador de UTM |
| 4. Teste de venda | métricas diárias, funil, indicadores, veredito e status do produto |
| 5. Painel | comparação entre produtos, filtro, ordenação por lucro e gráfico |
| 6. Importação CSV | sugestão de colunas, prévia e mescla com o que já foi lançado |
| 7. Integração | webhooks da Nuvemshop e da Shopify e alertas |

**Princípios seguidos:**
- **As regras ficam só no backend.** O React apenas exibe, então nenhuma conta é feita em dois lugares.
- **Nomes em português.** Tabelas, colunas, funções e rotas usam `snake_case`; os componentes React usam `PascalCase`.
- **A opção mais simples sempre que havia duas.**

---

## Estrutura de pastas

```
validador/
├── iniciar.bat                 # atalho do Windows: abre backend, frontend e navegador
├── CLAUDE.md                   # especificação do projeto
├── README.md
├── exemplos/                   # CSVs de exemplo para testar a importação
│   ├── metricas_meta_exemplo.csv
│   └── pedidos_exemplo.csv
├── backend/
│   ├── app.py                  # cria o app Flask e registra as rotas
│   ├── banco.py                # conexão SQLite e criação das tabelas
│   ├── schema.sql              # tabelas do banco
│   ├── regras.py               # TODAS as regras de cálculo (funções puras)
│   ├── importacao_csv.py       # leitura e conversão de CSV (funções puras)
│   ├── .env.example            # modelo das configurações
│   ├── rotas/                  # rotas da API: auth, produtos, pontuacao, validacao,
│   │                           #   testes, painel, integracoes
│   └── testes/                 # testes automáticos
└── frontend/
    ├── index.html
    ├── vite.config.js          # proxy /api → Flask
    └── src/
        ├── api.js              # todas as chamadas à API
        ├── formatar.js         # moeda, porcentagem e datas no padrão brasileiro
        ├── contexto/           # usuário logado
        ├── componentes/        # Layout, Funil, CardIndicador, Veredito, BotoesNota,
        │                       #   GeradorUtm, CampoSenha, Icones...
        └── paginas/            # Login, Cadastro, ListaProdutos, Produto, Pontuacao,
                                #   Validacao, TestesProduto, TesteVenda, ImportarCsv, Painel
```

**Tabelas do banco:**
- `usuarios`, `produtos`, `pontuacoes` e `validacao_manual`.
- `testes_venda` e `metricas_diarias` (com `origem`: manual, csv ou webhook).
- `pedidos_webhook`, que evita contar o mesmo pedido duas vezes.

---

## Instalação passo a passo

### Pré-requisitos

- **Python 3.10 ou mais novo** (testado no 3.12). No Windows, marque *"Add Python to PATH"* ao instalar.
- **Node.js 20.19 ou mais novo** (recomendado 22 ou 24; testado no 24), que já vem com o `npm`.

Para conferir, abra um terminal e rode:

```bash
python --version
node --version
```

### 1. Instalar o backend

```bash
cd validador/backend
pip install flask werkzeug python-dotenv
```

### 2. Criar o arquivo de configuração

```bash
copy .env.example .env        # Linux/Mac: cp .env.example .env
```

Abra o `backend/.env` e troque o `SECRET_KEY` por uma chave aleatória. Para gerar uma:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

As variáveis `NUVEMSHOP_*` e `SHOPIFY_*` podem ficar vazias. Só são necessárias para a integração automática.

### 3. Instalar o frontend

```bash
cd ../frontend
npm install
```

### 4. Abrir o sistema

**No Windows (jeito mais fácil):** dê dois cliques em **`iniciar.bat`**, na pasta principal do projeto.
Ele abre duas janelas pretas (*Validador de Vendas - backend* e *Validador de Vendas - frontend*)
e, em seguida, o navegador em http://localhost:5173.

> **Deixe as duas janelas abertas** enquanto usa o sistema. Para desligar, feche as duas.

**Manualmente (qualquer sistema), em dois terminais:**

```bash
# Terminal 1
cd backend
python app.py          # deve aparecer "Running on http://127.0.0.1:5000"

# Terminal 2
cd frontend
npm run dev            # abre em http://localhost:5173
```

O banco `backend/validador.db` é criado sozinho na primeira vez.

> **"Não foi possível falar com o servidor"?** O backend não está rodando. Confira se a janela ou o terminal do
> backend está aberto e sem erros.

---

## Como usar passo a passo

O exemplo abaixo usa o **leitor de código de barras**: preço de **R$ 200** e custo total de **R$ 110**.

### Passo 1: Criar sua conta
Abra http://localhost:5173 e clique em **Cadastre-se**. Preencha nome, e-mail e senha (mínimo de 6 caracteres).
Você entra direto na lista de produtos. Nas próximas vezes, use **Entrar**.
O ícone de olho no campo de senha mostra ou esconde o que você digitou.

### Passo 2: Cadastrar o produto
Clique em **+ Novo produto** e escolha **como você vende**:
- **Afiliado** (padrão): preço do produto na Shopee e **sua comissão em %** (veja no Painel de Afiliados).
  A comissão por venda aparece no lugar da margem. Exemplo: R$ 34,95 com 10% = **R$ 3,50 por venda**.
- **Vendedor**: preço e custo, como no exemplo abaixo.

Para o vendedor, preencha:
- **Nome** e **Plataforma** (ex.: Nuvemshop);
- **URL do produto** na loja (opcional, mas necessária para gerar os links UTM);
- **Preço de venda** e **Custo unitário**. O custo deve **somar produto, frete, taxas da plataforma e impostos**.
  Pode digitar com vírgula: `199,90`.

Na lista aparece a margem: **R$ 90,00 (45%)**. O status começa como **Ideia**.

### Passo 3: Pontuar
Na linha do produto, clique em **Pontuar** e dê uma nota de 1 a 5 para cada critério.
A margem já vem preenchida e bloqueada: 45% dá nota 4.
Clique em **Salvar pontuação** e veja o total (ex.: **20 / 25, Vale testar**).
Cada pontuação fica no histórico, e o status vira **Pontuado**.

> Se o veredito for **Descartar**, pense duas vezes antes de gastar com anúncios.

### Passo 4: Validar manualmente
Clique em **Validar**. Para cada uma das 8 etapas, marque **Concluída** e, se quiser, escreva uma
observação e cole um link de evidência:

1. Escolher 1 produto e 1 público (nicho definido em uma frase)
2. Pesquisar demanda (mais vendidos, Google Trends, volume de buscas)
3. Analisar concorrentes (Biblioteca de Anúncios da Meta, preços praticados)
4. Montar oferta mínima (landing page simples com link para o produto)
5. Gerar links com UTM para cada canal
6. Rodar teste com verba pequena (R$ 30 a 50/dia por 7 dias) ou canal orgânico
7. Registrar métricas diariamente
8. Tomar a decisão: escalar, ajustar ou trocar

Use o **Gerador de link UTM** da mesma página:
1. Escolha a origem (ex.: `facebook`) e o meio (ex.: `cpc`). A campanha já vem com o nome do produto.
2. Clique em **Copiar** e use esse link no anúncio.

Exemplo de link gerado: `https://sualoja.com/leitor?utm_source=facebook&utm_medium=cpc&utm_campaign=leitor-de-codigo-de-barras`

### Passo 5: Criar o teste de venda
Na lista de produtos, clique em **Testes** e depois em **+ Novo teste**. Preencha:
- **Canal** (ex.: Facebook Ads);
- **Campanha**: use **o mesmo nome do `utm_campaign`** do link do anúncio;
- **Verba diária** (sugestão: R$ 30) e **datas** (já vem com 7 dias).

O status do produto vira **Em teste**.

### Passo 6: Lançar os números de cada dia
Na página do teste, use o bloco **Lançar dia**:
1. A data de hoje já vem preenchida.
2. Copie do gerenciador de anúncios e da loja: investimento, impressões, cliques, visitas, carrinhos,
   vendas e receita.
3. Clique em **Salvar dia**.

Para corrigir um dia, clique em **Corrigir** na tabela "Dias lançados".

**Atalhos:**
- **Importar CSV:** em vez de digitar, envie o relatório do Meta ou a planilha de pedidos
  (veja [Importação de CSV](#importação-de-csv)).
- **Integração:** com a Nuvemshop ligada, as vendas pagas entram sozinhas
  (veja [Integração](#integração-com-nuvemshop-e-shopify)).

### Passo 7: Ler o resultado
A página do teste mostra:
- **Veredito:** Escalar, Ajustar, Trocar de produto ou Continue testando, com uma **barra de CPA × margem**
  e marcas em 70% e 100%.
- **Cards:** CTR, conversão, CPA e lucro.
- **Funil:** impressões → cliques → visitas → carrinhos → vendas, com a taxa entre cada etapa.
- **Alertas** em vermelho, quando o CPA passa da margem ou a conversão despenca.

Exemplo: R$ 210 investidos e 3 vendas dão **CPA de R$ 70,00**, que é **77,8% da margem**, e o veredito é **Ajustar**.
O status do produto acompanha o veredito.

### Passo 8: Comparar no Painel
No menu, clique em **Painel**:
- Filtre por status: Todos, Escalar, Ajustar, Descartado…
- Clique em **Lucro** para inverter a ordem.
- Escolha um teste para ver o gráfico de **investimento × receita** por dia.
- Veja os **pedidos recebidos pela integração**. Os que vieram sem campanha aparecem marcados.

### Passo 9: Decidir
- **Escalar:** aumente a verba aos poucos e continue acompanhando.
- **Ajustar:** mude o criativo, o preço ou a página, e crie um novo teste.
- **Trocar:** encerre o teste (botão **Encerrar teste**) e volte ao passo 2 com outro produto.

---

## Importação de CSV

Na página do teste, clique em **Importar CSV**:

1. **Escolha o arquivo** (até 2 MB).
2. **Confira as colunas.** O sistema sugere qual coluna é qual pelo nome. Por exemplo, num relatório do Meta:
   "Valor usado (BRL)" vira investimento e "Cliques no link" vira cliques. Ajuste o que precisar.
   - Para **planilhas de pedidos**, em **Vendas** escolha **"Contar 1 por linha (pedidos)"**.
3. **Veja a prévia.** Cada dia aparece como **Novo** ou **Atualiza**, há aviso para dias **fora do período**,
   e as linhas ignoradas são listadas com o motivo (por exemplo, a linha "Total" do relatório).
4. Clique em **Importar**.

**O que o sistema entende:**
- Separador `;` ou `,`.
- Acentos em UTF-8 ou no formato do Excel.
- Números como `R$ 1.234,56` ou `1234.56`.
- Datas como `2026-10-06` ou `06/10/2026 14:33`.

**Regras da importação:**
- Campos marcados como "não importar" **não apagam** o que já está lançado. Dá para importar os anúncios
  do Meta e depois as vendas da loja, e os dois se juntam.
- Linhas com a mesma data são **somadas**.

**Teste com os arquivos de `exemplos/`.** Eles usam um teste que começa em 01/10/2026:
- `metricas_meta_exemplo.csv`: relatório do Meta;
- `pedidos_exemplo.csv`: pedidos no formato do Excel.

---

## Integração com Nuvemshop e Shopify

Com a integração ligada, cada **pedido pago** na loja chega sozinho ao sistema:
1. O sistema confere a assinatura do aviso.
2. Busca o pedido na API da Nuvemshop.
3. Acha a `utm_campaign` (na URL pela qual o cliente entrou).
4. Soma **1 venda e o valor** no dia do teste com essa campanha.

Pedidos repetidos não contam duas vezes. Pedidos sem campanha ficam listados no Painel.

> **Importante:** a loja precisa conseguir acessar o sistema pela internet, com **HTTPS**.
> Ela não alcança o `localhost` do seu computador. Use um túnel (como Cloudflare Tunnel ou ngrok)
> ou publique o sistema num servidor.

### Nuvemshop

Os passos abaixo seguem a documentação da Nuvemshop. Confira lá se algo mudou.

1. No **Portal de Parceiros da Nuvemshop**, crie um app com permissão de leitura de pedidos (`read_orders`).
   Anote o **ID do app** e o **client secret**.
2. Instale o app na sua loja: abra `https://www.nuvemshop.com.br/apps/<ID do app>/authorize` logado na loja.
   Você volta para a URL de redirecionamento do app com um `code` no endereço.
3. Troque o `code` pelo token. Faça isso logo, porque o `code` vale por pouco tempo:
   ```bash
   curl -X POST https://www.tiendanube.com/apps/authorize/token \
     -d client_id=<ID do app> -d client_secret=<client secret> \
     -d grant_type=authorization_code -d code=<code>
   ```
   A resposta traz o `access_token` e o `user_id`, que é o número da loja.
4. Cadastre o webhook de pedido pago apontando para o seu endereço público:
   ```bash
   curl -X POST https://api.nuvemshop.com.br/v1/<número da loja>/webhooks \
     -H "Authentication: bearer <access_token>" -H "Content-Type: application/json" \
     -H "User-Agent: Validador de Vendas (seu-email)" \
     -d '{"event": "order/paid", "url": "https://SEU-ENDERECO/api/integracoes/nuvemshop/webhook"}'
   ```
5. No `backend/.env`, preencha as três variáveis e reinicie o backend:
   - `NUVEMSHOP_SEGREDO_APP`: o client secret;
   - `NUVEMSHOP_TOKEN_ACESSO`: o access_token;
   - `NUVEMSHOP_EMAIL_USUARIO`: o e-mail da sua conta no Validador de Vendas.
6. Nos anúncios, use os links gerados na Validação, com a **mesma `utm_campaign` do teste de venda**.

### Shopify

1. Em **Configurações → Notificações → Webhooks**, crie um webhook de **"Pagamento do pedido"** em JSON,
   apontando para `https://SEU-ENDERECO/api/integracoes/shopify/webhook`.
2. No `backend/.env`, preencha `SHOPIFY_SEGREDO_WEBHOOK` com o segredo mostrado nessa tela e
   `SHOPIFY_EMAIL_USUARIO` com o e-mail da sua conta.

### Cuidados

- Só pedidos **pagos** contam. Cancelamentos não descontam.
- Se um teste recebe pedidos pela integração, **não importe vendas e receita por CSV**, ou elas contam duas vezes.
- Antes de lançar o dia pelo formulário, **atualize a página (F5)**, para não regravar as vendas com um número antigo.

---

## Testes

```bash
cd backend
python -m unittest discover -s testes -t . -v
```

São **149 testes**:

| Arquivo | O que verifica |
|---|---|
| `testes/test_regras.py` | margem, pontuação, progresso da validação, indicadores, funil, veredito e alertas |
| `testes/test_importacao_csv.py` | separador, acentos, números, datas, sugestão de colunas, soma por dia |
| `testes/test_integracoes.py` | assinatura dos webhooks, UTM, pedido repetido, pedido sem campanha (com a Nuvemshop simulada) |
| `testes/test_cenarios.py` | cenários de uso pela API em **Dado / Quando / Então**, com um banco temporário |

Exemplo de cenário:

```
Dado que estou logado,
Quando cadastro um produto com preço 200 e custo 110,
Então vejo a margem de R$ 90,00 (45%).
```

---

## Colocando em produção

```bash
cd frontend && npm run build     # gera frontend/dist
cd ../backend && python app.py   # o Flask serve as telas e a API em http://127.0.0.1:5000
```

Antes de expor na internet:
- Use um `SECRET_KEY` forte no `.env`.
- Sirva por **HTTPS**, que é obrigatório para os webhooks.
- O `python app.py` usa o servidor de desenvolvimento do Flask. Para uso real, rode o app com um servidor
  WSGI de produção, o que exige instalar um pacote a mais.

---

## Referência da API

Todas as rotas respondem em JSON. Os erros vêm como `{"erros": ["..."]}`.
Sem login, as rotas protegidas respondem `401`, e um produto de outro usuário responde `404`.

**Conta**

| Método | Rota | Resposta |
|---|---|---|
| POST | `/api/auth/cadastro` | 201 usuário (já entra logado) · 400 · 409 e-mail já cadastrado |
| POST | `/api/auth/login` | 200 usuário · 401 |
| POST | `/api/auth/logout` | 204 |
| GET | `/api/auth/eu` | 200 usuário logado · 401 |

**Produtos**

| Método | Rota | Resposta |
|---|---|---|
| GET | `/api/produtos` | lista com `margem_unitaria` e `margem_percentual` |
| POST | `/api/produtos` | 201 produto · 400 |
| GET | `/api/produtos/<id>` | produto · 404 |
| PUT | `/api/produtos/<id>` | produto · 400 · 404 |
| DELETE | `/api/produtos/<id>` | 204 · 404 |

**Pontuação e validação**

| Método | Rota | Resposta |
|---|---|---|
| GET | `/api/pontuacao/<produto_id>` | produto, `nota_margem`, `ultima` e `historico` |
| POST | `/api/pontuacao/<produto_id>` | envia demanda, concorrencia, frete, facilidade_explicar (1 a 5) · 201 com total e veredito · 400 |
| GET | `/api/validacao/<produto_id>` | as 8 `etapas` e o `progresso` |
| PUT | `/api/validacao/<produto_id>/<etapa>` | envia concluida, observacao, link_evidencia · 200 etapa, progresso e status · 400 |

**Testes de venda**

| Método | Rota | Resposta |
|---|---|---|
| GET | `/api/testes?produto_id=X` | testes do produto com totais, lucro e veredito |
| POST | `/api/testes` | envia produto_id, canal, utm_campanha, verba_diaria, data_inicio, data_fim · 201 · 400 |
| GET | `/api/testes/<id>` | teste, produto, métricas por dia, totais, indicadores, funil, veredito e alertas |
| PUT | `/api/testes/<id>` | mesmos campos + status (`em_andamento`/`encerrado`) · 200 · 400 |
| DELETE | `/api/testes/<id>` | 204 |
| PUT | `/api/testes/<id>/metricas/<AAAA-MM-DD>` | envia investimento, impressoes, cliques, visitas, carrinhos, vendas, receita · 200 resumo recalculado · 400 |
| DELETE | `/api/testes/<id>/metricas/<AAAA-MM-DD>` | 200 resumo recalculado · 404 |
| POST | `/api/testes/<id>/csv/previa` | multipart: `arquivo` + `mapeamento` (JSON, opcional) · colunas, dias e linhas ignoradas |
| POST | `/api/testes/<id>/csv/importar` | mesmo envio · importados, novos, atualizados e resumo |

**Painel e integrações**

| Método | Rota | Resposta |
|---|---|---|
| GET | `/api/painel` | produtos com status, última pontuação e teste mais recente (CPA, lucro, veredito, alertas) e a lista de testes |
| POST | `/api/integracoes/nuvemshop/webhook` | sem login; confere `x-linkedstore-hmac-sha256` · 200 · 401 · 502 (tentar de novo) · 503 (não configurado) |
| POST | `/api/integracoes/shopify/webhook` | sem login; confere `X-Shopify-Hmac-Sha256` · 200 · 401 · 503 |
| GET | `/api/integracoes/pedidos` | últimos 50 pedidos recebidos e o teste ligado (ou sem campanha) |

---

## Situação atual e limitações conhecidas

- [x] Etapa 1: Base (cadastro, login, CRUD de produtos com margem)
- [x] Etapa 2: Pontuação (5 critérios, total até 25, veredito e histórico)
- [x] Etapa 3: Validação manual guiada (checklist de 8 etapas, progresso, gerador UTM)
- [x] Etapa 4: Teste de venda (métricas diárias, funil, indicadores, veredito)
- [x] Etapa 5: Painel comparativo (filtro por status, ordem por lucro, gráfico investimento × receita)
- [x] Etapa 6: Importação CSV (sugestão de colunas, prévia, mescla com o já lançado)
- [x] Etapa 7: Integração com a plataforma (webhooks Nuvemshop/Shopify, alertas)
- [ ] Etapa 8: Modo afiliado (comissão como margem, Sub_id, lucro pela comissão recebida): aguardando aprovação
- [ ] Etapa 9: Importar relatórios do Painel de Afiliados (CSV)
- [ ] Etapa 10: API de Afiliados da Shopee (link com Sub_id e sincronizar conversões)
- [ ] Etapa 11: Encontrar produtos (ofertas por vendas e comissão)
- [ ] Etapa 12: Painel do afiliado (cliques, pedidos, comissão, cancelamentos)
- [ ] Etapa 13: Ofertas e campanhas com IA

**Limitações conhecidas:**
- **Integração ainda sem teste real.** A integração com a Nuvemshop foi testada com a API simulada. O teste com
  uma loja de verdade depende de criar o app na Nuvemshop e de ter um endereço público com HTTPS.
- **Cancelamentos não descontam.** Pedidos cancelados depois de pagos continuam contando como venda.
- **Formulário aberto pode regravar vendas.** Se a página do teste ficar aberta muito tempo e chegar uma venda
  pelo webhook, salvar o dia pelo formulário regrava as vendas daquele dia. Atualize a página antes de lançar.
- **Servidor de desenvolvimento.** O sistema roda no servidor de desenvolvimento do Flask; veja
  [Colocando em produção](#colocando-em-produção).
