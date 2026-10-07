import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { buscarProduto, criarTeste, listarTestes } from "../api.js";
import FormularioTeste from "../componentes/FormularioTeste.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import Veredito from "../componentes/Veredito.jsx";
import { formatarData, formatarMoeda, hojeIso, paraCampanha, paraSubId, somarDias } from "../formatar.js";

/** Testes de venda de um produto: lista e criação. */
export default function TestesProduto() {
  const { id } = useParams();
  const [produto, setProduto] = useState(null);
  const [testes, setTestes] = useState([]);
  const [erros, setErros] = useState([]);
  const [criando, setCriando] = useState(false);
  const navegar = useNavigate();

  useEffect(() => {
    Promise.all([buscarProduto(id), listarTestes(id)])
      .then(([dadosProduto, lista]) => {
        setProduto(dadosProduto);
        setTestes(lista);
        setCriando(lista.length === 0);
      })
      .catch((erro) => setErros(erro.erros));
  }, [id]);

  async function aoCriar(dados) {
    const resumo = await criarTeste({ ...dados, produto_id: Number(id) });
    navegar(`/testes/${resumo.teste.id}`);
  }

  if (!produto) {
    return (
      <>
        <ListaErros erros={erros} />
        {erros.length ? <Link to="/produtos">Voltar para a lista de produtos</Link>
                      : <p className="text-muted">Carregando...</p>}
      </>
    );
  }

  const hoje = hojeIso();
  return (
    <>
      <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
        <div>
          <h1 className="h3 mb-1">Testes de venda</h1>
          <p className="text-muted mb-0">
            {produto.nome} · {produto.modelo === "afiliado" ? "comissão" : "margem"} de{" "}
            {formatarMoeda(produto.margem_unitaria)} por venda
          </p>
        </div>
        <Link to="/produtos" className="btn btn-outline-secondary btn-sm">Voltar</Link>
      </div>

      {criando ? (
        <div className="card card-body shadow-sm mb-4">
          <h2 className="h5">Novo teste</h2>
          <FormularioTeste
            inicial={{ utm_campanha: produto.modelo === "afiliado" ? paraSubId(produto.nome) : paraCampanha(produto.nome),
                       verba_diaria: "30,00", data_inicio: hoje, data_fim: somarDias(hoje, 6) }}
            afiliado={produto.modelo === "afiliado"}
            textoBotao="Criar teste"
            aoSalvar={aoCriar}
            aoCancelar={testes.length ? () => setCriando(false) : undefined} />
        </div>
      ) : (
        <button type="button" className="btn btn-primary mb-3" onClick={() => setCriando(true)}>+ Novo teste</button>
      )}

      {testes.length > 0 && (
        <div className="table-responsive bg-white border rounded">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light">
              <tr>
                <th>Canal</th>
                <th className="d-none d-md-table-cell">Período</th>
                <th className="text-end d-none d-sm-table-cell">Investido</th>
                <th className="text-end">Vendas</th>
                <th className="text-end d-none d-sm-table-cell">Lucro</th>
                <th>Veredito</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {testes.map((teste) => (
                <tr key={teste.id}>
                  <td>
                    <div className="fw-semibold">{teste.canal}</div>
                    <div className="small text-muted">
                      {teste.utm_campanha}
                      {teste.status === "encerrado" && <span className="badge text-bg-light border ms-1">Encerrado</span>}
                    </div>
                  </td>
                  <td className="small d-none d-md-table-cell text-nowrap">
                    {formatarData(teste.data_inicio)} a {formatarData(teste.data_fim)}
                  </td>
                  <td className="text-end d-none d-sm-table-cell">{formatarMoeda(teste.totais.investimento)}</td>
                  <td className="text-end">{teste.totais.vendas}</td>
                  <td className={`text-end d-none d-sm-table-cell ${teste.lucro < 0 ? "text-danger" : ""}`}>
                    {formatarMoeda(teste.lucro)}
                  </td>
                  <td><Veredito codigo={teste.veredito.codigo} /></td>
                  <td className="text-end">
                    <Link to={`/testes/${teste.id}`} className="btn btn-sm btn-outline-primary">Abrir</Link>
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
