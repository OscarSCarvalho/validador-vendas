// Todas as chamadas à API do Flask. O cookie de sessão vai em toda requisição.

let aoPerderSessao = () => {};

/** O UsuarioContexto registra aqui o que fazer quando a API responder 401. */
export function definirAoPerderSessao(funcao) {
  aoPerderSessao = funcao;
}

function criarErro(status, erros) {
  const erro = new Error(erros.join(" "));
  erro.status = status;
  erro.erros = erros;
  return erro;
}

async function requisicao(caminho, { metodo = "GET", corpo } = {}) {
  const opcoes = { method: metodo, credentials: "include", headers: {} };
  if (corpo instanceof FormData) {
    opcoes.body = corpo; // upload de arquivo: o navegador define o Content-Type
  } else if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(`/api${caminho}`, opcoes);
  } catch {
    throw criarErro(0, ["Não foi possível falar com o servidor. Ele está rodando?"]);
  }

  const dados = resposta.status === 204 ? null : await resposta.json().catch(() => null);
  if (!resposta.ok) {
    if (resposta.status === 401) aoPerderSessao();
    if (!dados?.erros && resposta.status >= 500) {
      // Sem JSON e com erro 5xx: em geral o Vite não conseguiu falar com o Flask.
      throw criarErro(resposta.status, [
        "Não foi possível falar com o servidor. Verifique se o backend está rodando (cd backend, python app.py).",
      ]);
    }
    throw criarErro(resposta.status, dados?.erros ?? ["Erro inesperado. Tente de novo."]);
  }
  return dados;
}

// Autenticação
export const buscarUsuarioLogado = () => requisicao("/auth/eu");
export const entrar = (email, senha) =>
  requisicao("/auth/login", { metodo: "POST", corpo: { email, senha } });
export const cadastrar = (nome, email, senha) =>
  requisicao("/auth/cadastro", { metodo: "POST", corpo: { nome, email, senha } });
export const sair = () => requisicao("/auth/logout", { metodo: "POST" });

// Produtos
export const listarProdutos = () => requisicao("/produtos");
export const buscarProduto = (id) => requisicao(`/produtos/${id}`);
export const criarProduto = (produto) =>
  requisicao("/produtos", { metodo: "POST", corpo: produto });
export const atualizarProduto = (id, produto) =>
  requisicao(`/produtos/${id}`, { metodo: "PUT", corpo: produto });
export const excluirProduto = (id) => requisicao(`/produtos/${id}`, { metodo: "DELETE" });

// Pontuação
export const buscarPontuacao = (produtoId) => requisicao(`/pontuacao/${produtoId}`);
export const pontuarProduto = (produtoId, notas) =>
  requisicao(`/pontuacao/${produtoId}`, { metodo: "POST", corpo: notas });

// Validação manual
export const buscarValidacao = (produtoId) => requisicao(`/validacao/${produtoId}`);
export const salvarEtapaValidacao = (produtoId, etapa, dados) =>
  requisicao(`/validacao/${produtoId}/${etapa}`, { metodo: "PUT", corpo: dados });

// Testes de venda
export const listarTestes = (produtoId) => requisicao(`/testes?produto_id=${produtoId}`);
export const criarTeste = (dados) => requisicao("/testes", { metodo: "POST", corpo: dados });
export const buscarTeste = (id) => requisicao(`/testes/${id}`);
export const atualizarTeste = (id, dados) => requisicao(`/testes/${id}`, { metodo: "PUT", corpo: dados });
export const excluirTeste = (id) => requisicao(`/testes/${id}`, { metodo: "DELETE" });
export const salvarMetricasDia = (testeId, data, metricas) =>
  requisicao(`/testes/${testeId}/metricas/${data}`, { metodo: "PUT", corpo: metricas });
export const excluirMetricasDia = (testeId, data) =>
  requisicao(`/testes/${testeId}/metricas/${data}`, { metodo: "DELETE" });

// Importação de CSV
function formularioCsv(arquivo, mapeamento) {
  const formulario = new FormData();
  formulario.append("arquivo", arquivo);
  if (mapeamento) formulario.append("mapeamento", JSON.stringify(mapeamento));
  return formulario;
}
export const previaCsv = (testeId, arquivo, mapeamento) =>
  requisicao(`/testes/${testeId}/csv/previa`, { metodo: "POST", corpo: formularioCsv(arquivo, mapeamento) });
export const importarCsv = (testeId, arquivo, mapeamento) =>
  requisicao(`/testes/${testeId}/csv/importar`, { metodo: "POST", corpo: formularioCsv(arquivo, mapeamento) });

// Painel
export const buscarPainel = () => requisicao("/painel");

// Integrações (pedidos recebidos pelos webhooks)
export const listarPedidosIntegracao = () => requisicao("/integracoes/pedidos");
