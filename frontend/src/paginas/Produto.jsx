import { Fragment, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { atualizarProduto, buscarProduto, criarProduto } from "../api.js";
import ListaErros from "../componentes/ListaErros.jsx";
import { formatarDecimal } from "../formatar.js";

const PLATAFORMAS_SUGERIDAS = ["Shopee", "Nuvemshop", "Shopify", "Mercado Livre", "Site próprio"];
// Produto novo começa como afiliado Shopee (o foco do sistema; dá para trocar para vendedor).
const PRODUTO_VAZIO = { modelo: "afiliado", nome: "", plataforma: "Shopee", url_produto: "",
                        preco_venda: "", custo_unitario: "", taxa_comissao: "" };
const MODELOS = [
  ["afiliado", "Afiliado", "ganho comissão"],
  ["vendedor", "Vendedor", "tenho estoque"],
];

/** 10 -> "10"; 12.5 -> "12,5" */
const formatarTaxa = (taxa) => (typeof taxa === "number" ? String(taxa).replace(".", ",") : "");

/** Formulário de novo produto (/produtos/novo) e de edição (/produtos/:id/editar). */
export default function Produto() {
  const { id } = useParams();
  const editando = Boolean(id);
  const [produto, setProduto] = useState(PRODUTO_VAZIO);
  const [carregando, setCarregando] = useState(editando);
  const [erros, setErros] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [falhaAoCarregar, setFalhaAoCarregar] = useState(false);
  const navegar = useNavigate();

  useEffect(() => {
    if (!editando) return;
    buscarProduto(id)
      .then((dados) => setProduto({
        modelo: dados.modelo,
        nome: dados.nome,
        plataforma: dados.plataforma,
        url_produto: dados.url_produto ?? "",
        preco_venda: formatarDecimal(dados.preco_venda),
        custo_unitario: dados.modelo === "afiliado" ? "" : formatarDecimal(dados.custo_unitario),
        taxa_comissao: formatarTaxa(dados.taxa_comissao),
      }))
      .catch((erro) => {
        setErros(erro.erros);
        setFalhaAoCarregar(true);
      })
      .finally(() => setCarregando(false));
  }, [id, editando]);

  function alterar(evento) {
    setProduto({ ...produto, [evento.target.name]: evento.target.value });
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    try {
      if (editando) await atualizarProduto(id, produto);
      else await criarProduto(produto);
      navegar("/produtos", { state: { mensagem: editando ? "Produto atualizado." : "Produto cadastrado." } });
    } catch (erro) {
      setErros(erro.erros);
      setEnviando(false);
    }
  }

  const titulo = editando ? "Editar produto" : "Novo produto";
  const afiliado = produto.modelo === "afiliado";

  return (
    <div className="row justify-content-center">
      <div className="col-12 col-md-8 col-lg-6">
        <h1 className="h3 mb-3">{titulo}</h1>
        <ListaErros erros={erros} />
        {carregando ? <p className="text-muted">Carregando...</p> : falhaAoCarregar ? (
          <Link to="/produtos">Voltar para a lista de produtos</Link>
        ) : (
          <form onSubmit={aoEnviar} className="card card-body shadow-sm">
            <fieldset className="mb-3">
              <legend className="form-label fs-6 mb-1">Como você vende este produto?</legend>
              <div className="btn-group w-100" role="group">
                {MODELOS.map(([valor, rotulo, detalhe]) => (
                  <Fragment key={valor}>
                    <input type="radio" className="btn-check" name="modelo" id={`modelo-${valor}`} value={valor}
                           checked={produto.modelo === valor} onChange={alterar} />
                    <label className="btn btn-outline-primary" htmlFor={`modelo-${valor}`}>
                      {rotulo} <span className="small opacity-75">({detalhe})</span>
                    </label>
                  </Fragment>
                ))}
              </div>
            </fieldset>
            <div className="mb-3">
              <label htmlFor="nome" className="form-label">Nome do produto</label>
              <input type="text" className="form-control" id="nome" name="nome"
                     value={produto.nome} onChange={alterar} required autoFocus />
            </div>
            <div className="mb-3">
              <label htmlFor="plataforma" className="form-label">Plataforma</label>
              <input type="text" className="form-control" id="plataforma" name="plataforma"
                     list="lista-plataformas" value={produto.plataforma} onChange={alterar} required />
              <datalist id="lista-plataformas">
                {PLATAFORMAS_SUGERIDAS.map((nome) => <option key={nome} value={nome} />)}
              </datalist>
            </div>
            <div className="mb-3">
              <label htmlFor="url_produto" className="form-label">
                {afiliado ? "Link do produto ou seu link de afiliado" : "URL do produto"}{" "}
                <span className="text-muted">(opcional)</span>
              </label>
              <input type="url" className="form-control" id="url_produto" name="url_produto"
                     value={produto.url_produto} onChange={alterar} placeholder="https://..." />
            </div>
            <div className="row">
              <div className="col-6 mb-3">
                <label htmlFor="preco_venda" className="form-label">
                  {afiliado ? "Preço do produto (R$)" : "Preço de venda (R$)"}
                </label>
                <input type="text" inputMode="decimal" className="form-control" id="preco_venda"
                       name="preco_venda" value={produto.preco_venda} onChange={alterar}
                       placeholder="0,00" required />
              </div>
              {afiliado ? (
                <div className="col-6 mb-3">
                  <label htmlFor="taxa_comissao" className="form-label">Sua comissão (%)</label>
                  <input type="text" inputMode="decimal" className="form-control" id="taxa_comissao"
                         name="taxa_comissao" value={produto.taxa_comissao} onChange={alterar}
                         placeholder="ex.: 10" required />
                </div>
              ) : (
                <div className="col-6 mb-3">
                  <label htmlFor="custo_unitario" className="form-label">Custo unitário (R$)</label>
                  <input type="text" inputMode="decimal" className="form-control" id="custo_unitario"
                         name="custo_unitario" value={produto.custo_unitario} onChange={alterar}
                         placeholder="0,00" required />
                </div>
              )}
            </div>
            <div className="form-text mb-3">
              {afiliado
                ? "Veja a comissão do produto no Painel de Afiliados da Shopee (padrão de 3%; produtos com Comissão Extra pagam até 30%). A comissão por venda faz o papel da margem."
                : "O custo deve somar produto, frete, taxas da plataforma e impostos."}
            </div>
            <div className="d-flex gap-2">
              <button type="submit" className="btn btn-primary" disabled={enviando}>
                {enviando ? "Salvando..." : "Salvar"}
              </button>
              <Link to="/produtos" className="btn btn-outline-secondary">Cancelar</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
