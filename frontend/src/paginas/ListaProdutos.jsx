import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { excluirProduto, listarProdutos } from "../api.js";
import BadgeStatus from "../componentes/BadgeStatus.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import { formatarMoeda, formatarPercentual } from "../formatar.js";

export default function ListaProdutos() {
  const [produtos, setProdutos] = useState(null);
  const [erros, setErros] = useState([]);
  const [mensagem, setMensagem] = useState(useLocation().state?.mensagem ?? "");

  useEffect(() => {
    listarProdutos().then(setProdutos).catch((erro) => setErros(erro.erros));
  }, []);

  async function aoExcluir(produto) {
    if (!window.confirm(`Excluir "${produto.nome}"?`)) return;
    try {
      await excluirProduto(produto.id);
      setProdutos(produtos.filter((p) => p.id !== produto.id));
      setMensagem("Produto excluído.");
    } catch (erro) {
      setErros(erro.erros);
    }
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="h3 mb-0">Produtos</h1>
        <Link to="/produtos/novo" className="btn btn-primary">+ Novo produto</Link>
      </div>

      {mensagem && (
        <div className="alert alert-success alert-dismissible" role="alert">
          {mensagem}
          <button type="button" className="btn-close" aria-label="Fechar" onClick={() => setMensagem("")} />
        </div>
      )}
      <ListaErros erros={erros} />

      {produtos === null ? (
        !erros.length && <p className="text-muted">Carregando...</p>
      ) : produtos.length === 0 ? (
        <div className="text-center text-muted py-5 border rounded bg-white">
          <p className="mb-2">Você ainda não cadastrou nenhum produto.</p>
          <Link to="/produtos/novo">Cadastre o primeiro produto</Link>
        </div>
      ) : (
        <div className="table-responsive bg-white border rounded">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light">
              <tr>
                <th>Produto</th>
                <th className="d-none d-md-table-cell">Plataforma</th>
                <th className="text-end d-none d-sm-table-cell">Preço</th>
                <th className="text-end d-none d-sm-table-cell">Custo</th>
                <th className="text-end">Margem / comissão</th>
                <th className="d-none d-md-table-cell">Status</th>
                <th className="text-end">Ações</th>
              </tr>
            </thead>
            <tbody>
              {produtos.map((produto) => (
                <tr key={produto.id}>
                  <td>
                    <div className="fw-semibold">
                      {produto.url_produto
                        ? <a href={produto.url_produto} target="_blank" rel="noopener noreferrer">{produto.nome}</a>
                        : produto.nome}
                    </div>
                    <div className="small text-muted d-md-none">
                      {produto.plataforma} · <BadgeStatus status={produto.status} />
                    </div>
                  </td>
                  <td className="d-none d-md-table-cell">{produto.plataforma}</td>
                  <td className="text-end d-none d-sm-table-cell">{formatarMoeda(produto.preco_venda)}</td>
                  <td className="text-end d-none d-sm-table-cell">
                    {produto.modelo === "afiliado" ? <span className="text-muted">–</span> : formatarMoeda(produto.custo_unitario)}
                  </td>
                  <td className={`text-end text-nowrap${produto.margem_unitaria < 0 ? " text-danger" : ""}`}>
                    <span className="margem-valor">{formatarMoeda(produto.margem_unitaria)}</span>{" "}
                    <span className="text-muted small">({formatarPercentual(produto.margem_percentual)})</span>
                    {produto.modelo === "afiliado" && <div className="small text-muted">comissão de afiliado</div>}
                  </td>
                  <td className="d-none d-md-table-cell"><BadgeStatus status={produto.status} /></td>
                  <td>
                    <div className="d-flex flex-wrap justify-content-end gap-1">
                      <Link to={`/produtos/${produto.id}/pontuacao`} className="btn btn-sm btn-outline-primary">
                        Pontuar
                      </Link>
                      <Link to={`/produtos/${produto.id}/validacao`} className="btn btn-sm btn-outline-primary">
                        Validar
                      </Link>
                      <Link to={`/produtos/${produto.id}/testes`} className="btn btn-sm btn-outline-primary">
                        Testes
                      </Link>
                      <Link to={`/produtos/${produto.id}/editar`} className="btn btn-sm btn-outline-secondary">
                        Editar
                      </Link>
                      <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => aoExcluir(produto)}>
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
