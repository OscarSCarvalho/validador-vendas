import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buscarPainel, buscarTeste, listarPedidosIntegracao } from "../api.js";
import BadgeStatus, { ROTULOS_STATUS } from "../componentes/BadgeStatus.jsx";
import GraficoInvestimentoReceita from "../componentes/GraficoInvestimentoReceita.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import Veredito from "../componentes/Veredito.jsx";
import { formatarData, formatarMoeda } from "../formatar.js";

/** Ordena por lucro do teste mais recente; produtos sem teste ficam sempre no fim. */
function ordenarPorLucro(produtos, ordem) {
  return [...produtos].sort((a, b) => {
    const lucroA = a.teste?.lucro ?? null;
    const lucroB = b.teste?.lucro ?? null;
    if (lucroA === null && lucroB === null) return 0;
    if (lucroA === null) return 1;
    if (lucroB === null) return -1;
    return ordem === "desc" ? lucroB - lucroA : lucroA - lucroB;
  });
}

export default function Painel() {
  const [dados, setDados] = useState(null);
  const [erros, setErros] = useState([]);
  const [filtro, setFiltro] = useState("todos");
  const [ordem, setOrdem] = useState("desc");
  const [testeId, setTesteId] = useState("");
  const [metricas, setMetricas] = useState(null);
  const [pedidos, setPedidos] = useState([]);

  useEffect(() => {
    buscarPainel()
      .then((resposta) => {
        setDados(resposta);
        if (resposta.testes.length) setTesteId(String(resposta.testes[0].id));
      })
      .catch((erro) => setErros(erro.erros));
    listarPedidosIntegracao().then(setPedidos).catch(() => setPedidos([]));
  }, []);

  useEffect(() => {
    if (!testeId) return;
    setMetricas(null);
    buscarTeste(testeId).then((resumo) => setMetricas(resumo.metricas)).catch((erro) => setErros(erro.erros));
  }, [testeId]);

  if (!dados) {
    return (
      <>
        <h1 className="h3 mb-3">Painel</h1>
        <ListaErros erros={erros} />
        {!erros.length && <p className="text-muted">Carregando...</p>}
      </>
    );
  }

  const contagem = (status) => dados.produtos.filter((p) => status === "todos" || p.status === status).length;
  const visiveis = ordenarPorLucro(dados.produtos.filter((p) => filtro === "todos" || p.status === filtro), ordem);
  const filtros = [["todos", "Todos"], ...Object.entries(ROTULOS_STATUS).map(([status, [rotulo]]) => [status, rotulo])];

  return (
    <>
      <h1 className="h3 mb-3">Painel</h1>
      <ListaErros erros={erros} />

      {dados.produtos.length === 0 ? (
        <div className="text-center text-muted py-5 border rounded bg-white">
          <p className="mb-2">Cadastre produtos para comparar aqui.</p>
          <Link to="/produtos/novo">Cadastrar produto</Link>
        </div>
      ) : (
        <>
          <div className="d-flex flex-wrap gap-1 mb-3" role="group" aria-label="Filtrar por status">
            {filtros.map(([status, rotulo]) => (
              <button key={status} type="button" onClick={() => setFiltro(status)}
                      className={`btn btn-sm ${filtro === status ? "btn-dark" : "btn-outline-secondary"}`}>
                {rotulo} <span className="opacity-75">({contagem(status)})</span>
              </button>
            ))}
          </div>

          <div className="table-responsive bg-white border rounded mb-4">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th>Produto</th>
                  <th className="d-none d-md-table-cell">Status</th>
                  <th className="d-none d-sm-table-cell">Pontuação</th>
                  <th className="text-end d-none d-md-table-cell">CPA</th>
                  <th className="text-end">
                    <button type="button" className="btn btn-link btn-sm p-0 fw-bold text-decoration-none text-reset"
                            onClick={() => setOrdem(ordem === "desc" ? "asc" : "desc")}
                            title="Inverter a ordem">
                      Lucro {ordem === "desc" ? "▼" : "▲"}
                    </button>
                  </th>
                  <th>Veredito</th>
                </tr>
              </thead>
              <tbody>
                {visiveis.length === 0 && (
                  <tr><td colSpan={6} className="text-center text-muted py-4">Nenhum produto com esse status.</td></tr>
                )}
                {visiveis.map((produto) => (
                  <tr key={produto.id}>
                    <td>
                      <Link to={produto.teste ? `/testes/${produto.teste.id}` : `/produtos/${produto.id}/testes`}
                            className="fw-semibold">
                        {produto.nome}
                      </Link>
                      {produto.teste?.alertas.length > 0 && (
                        <span className="text-danger ms-1" role="img" aria-label="Alerta"
                              title={produto.teste.alertas.map((a) => a.mensagem).join("\n")}>⚠</span>
                      )}
                      <div className="small text-muted">
                        {produto.teste ? `${produto.teste.canal} · desde ${formatarData(produto.teste.data_inicio)}` : "sem teste"}
                        {produto.quantidade_testes > 1 && ` · ${produto.quantidade_testes} testes`}
                      </div>
                      <div className="d-md-none mt-1"><BadgeStatus status={produto.status} /></div>
                    </td>
                    <td className="d-none d-md-table-cell"><BadgeStatus status={produto.status} /></td>
                    <td className="d-none d-sm-table-cell text-nowrap">
                      {produto.pontuacao ? (
                        <>
                          <span className="fw-semibold me-1">{produto.pontuacao.total}/25</span>
                          <Veredito codigo={produto.pontuacao.veredito} />
                        </>
                      ) : <span className="text-muted">–</span>}
                    </td>
                    <td className="text-end d-none d-md-table-cell">{formatarMoeda(produto.teste?.cpa ?? null)}</td>
                    <td className={`text-end fw-semibold text-nowrap ${(produto.teste?.lucro ?? 0) < 0 ? "text-danger" : ""}`}>
                      {formatarMoeda(produto.teste?.lucro ?? null)}
                    </td>
                    <td>{produto.teste ? <Veredito codigo={produto.teste.veredito.codigo} /> : <span className="text-muted">–</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card shadow-sm">
            <div className="card-body">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h2 className="h5 mb-0">Investimento × receita por dia</h2>
                {dados.testes.length > 0 && (
                  <select className="form-select form-select-sm w-auto mw-100" value={testeId}
                          onChange={(e) => setTesteId(e.target.value)} aria-label="Teste do gráfico">
                    {dados.testes.map((teste) => (
                      <option key={teste.id} value={teste.id}>
                        {teste.produto_nome} · {teste.canal} · {formatarData(teste.data_inicio)}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              {dados.testes.length === 0 ? (
                <p className="text-muted mb-0">Crie um teste de venda para ver o gráfico.</p>
              ) : metricas === null ? (
                <p className="text-muted mb-0">Carregando...</p>
              ) : (
                <GraficoInvestimentoReceita metricas={metricas}
                  rotuloReceita={dados.testes.find((t) => String(t.id) === testeId)?.modelo === "afiliado" ? "Comissão" : "Receita"} />
              )}
            </div>
          </div>

          {pedidos.length > 0 && (
            <div className="card shadow-sm mt-4">
              <div className="card-body">
                <h2 className="h5">Pedidos recebidos pela integração</h2>
                <div className="table-responsive">
                  <table className="table table-sm align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th>Data</th>
                        <th className="d-none d-sm-table-cell">Plataforma</th>
                        <th className="text-end">Valor</th>
                        <th>Campanha / teste</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pedidos.map((pedido) => (
                        <tr key={`${pedido.plataforma}-${pedido.pedido_id}`}>
                          <td className="text-nowrap">{formatarData(pedido.data)}</td>
                          <td className="d-none d-sm-table-cell text-capitalize">{pedido.plataforma} #{pedido.pedido_id}</td>
                          <td className="text-end">{formatarMoeda(pedido.valor)}</td>
                          <td className="small">
                            {pedido.teste_id ? (
                              <Link to={`/testes/${pedido.teste_id}`}>{pedido.produto_nome} · {pedido.canal}</Link>
                            ) : (
                              <span className="badge text-bg-light border">sem campanha</span>
                            )}
                            {pedido.utm_campanha && <span className="text-muted"> ({pedido.utm_campanha})</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
