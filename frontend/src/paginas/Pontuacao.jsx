import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { buscarPontuacao, pontuarProduto } from "../api.js";
import BotoesNota from "../componentes/BotoesNota.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import Veredito from "../componentes/Veredito.jsx";
import { formatarDataHora, formatarMoeda, formatarPercentual } from "../formatar.js";

const CRITERIOS = [
  { campo: "demanda", rotulo: "Demanda", dica: "Aparece nos mais vendidos e tem buscas constantes." },
  { campo: "concorrencia", rotulo: "Concorrência", dica: "Há vendedores ativos, mas espaço para se diferenciar." },
  { campo: "margem", rotulo: "Margem", automatico: true },
  { campo: "frete", rotulo: "Frete", dica: "Leve, pequeno, difícil de quebrar." },
  { campo: "facilidade_explicar", rotulo: "Facilidade de explicar", dica: "O benefício cabe em uma frase e em um vídeo curto." },
];
const NOTAS_VAZIAS = { demanda: null, concorrencia: null, frete: null, facilidade_explicar: null };

export default function Pontuacao() {
  const { id } = useParams();
  const [dados, setDados] = useState(null);
  const [notas, setNotas] = useState(NOTAS_VAZIAS);
  const [erros, setErros] = useState([]);
  const [mensagem, setMensagem] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    buscarPontuacao(id)
      .then((resposta) => {
        setDados(resposta);
        if (resposta.ultima) {
          const { demanda, concorrencia, frete, facilidade_explicar } = resposta.ultima;
          setNotas({ demanda, concorrencia, frete, facilidade_explicar });
        }
      })
      .catch((erro) => setErros(erro.erros));
  }, [id]);

  const completo = Object.values(notas).every((nota) => nota !== null);

  async function aoSalvar() {
    setEnviando(true);
    setMensagem("");
    try {
      const nova = await pontuarProduto(id, notas);
      setDados({ ...dados, ultima: nova, historico: [nova, ...dados.historico] });
      setErros([]);
      setMensagem("Pontuação salva.");
    } catch (erro) {
      setErros(erro.erros);
    } finally {
      setEnviando(false);
    }
  }

  if (!dados) {
    return (
      <>
        <ListaErros erros={erros} />
        {erros.length ? <Link to="/produtos">Voltar para a lista de produtos</Link>
                      : <p className="text-muted">Carregando...</p>}
      </>
    );
  }

  const { produto, nota_margem: notaMargem, ultima, historico } = dados;
  const afiliado = produto.modelo === "afiliado";

  return (
    <div className="row g-4">
      <div className="col-12 col-lg-7">
        <h1 className="h3 mb-1">Pontuar produto</h1>
        <p className="text-muted mb-3">{produto.nome} · {produto.plataforma}</p>
        <ListaErros erros={erros} />

        <div className="card card-body shadow-sm">
          {CRITERIOS.map(({ campo, rotulo: rotuloBase, dica, automatico }) => {
            const rotulo = automatico && afiliado ? "Comissão" : rotuloBase;
            return (
            <div key={campo} className="mb-4">
              <div className="d-flex justify-content-between align-items-baseline mb-1">
                <span className="fw-semibold">{rotulo}</span>
                {automatico && <span className="badge text-bg-secondary">automática</span>}
              </div>
              <BotoesNota rotulo={rotulo}
                          valor={automatico ? notaMargem : notas[campo]}
                          bloqueado={automatico}
                          aoMudar={(nota) => setNotas({ ...notas, [campo]: nota })} />
              <div className="form-text">
                {automatico && afiliado
                  ? `Comissão de ${formatarMoeda(produto.margem_unitaria)} (${formatarPercentual(produto.margem_percentual)}) por venda. A nota vem do valor em R$. Para mudar, edite o preço ou a comissão do produto.`
                  : automatico
                  ? `Margem de ${formatarMoeda(produto.margem_unitaria)} (${formatarPercentual(produto.margem_percentual)}) por venda. Para mudar, edite o preço ou o custo do produto.`
                  : dica}
              </div>
            </div>
            );
          })}
          <div className="d-flex gap-2 align-items-center flex-wrap">
            <button type="button" className="btn btn-primary" onClick={aoSalvar}
                    disabled={!completo || enviando}>
              {enviando ? "Salvando..." : "Salvar pontuação"}
            </button>
            <Link to="/produtos" className="btn btn-outline-secondary">Voltar</Link>
            {!completo && <span className="small text-muted">Dê uma nota para cada critério.</span>}
          </div>
        </div>
      </div>

      <div className="col-12 col-lg-5">
        <h2 className="h5 mb-3">Resultado</h2>
        {mensagem && <div className="alert alert-success py-2">{mensagem}</div>}
        {ultima ? (
          <>
            <Veredito codigo={ultima.veredito} total={ultima.total} />
            <p className="small text-muted mt-2 mb-0">Pontuado em {formatarDataHora(ultima.criado_em)}.</p>
          </>
        ) : (
          <div className="text-center text-muted py-4 border rounded bg-white">
            Dê as notas e salve para ver o total e o veredito.
          </div>
        )}

        {historico.length > 0 && (
          <>
            <h2 className="h5 mt-4 mb-2">Histórico</h2>
            <div className="table-responsive bg-white border rounded">
              <table className="table table-sm align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th>Data</th>
                    <th className="text-center d-none d-sm-table-cell" title="Demanda · Concorrência · Margem · Frete · Facilidade de explicar">
                      Notas
                    </th>
                    <th className="text-center">Total</th>
                    <th>Veredito</th>
                  </tr>
                </thead>
                <tbody>
                  {historico.map((item) => (
                    <tr key={item.id}>
                      <td className="small text-nowrap">{formatarDataHora(item.criado_em)}</td>
                      <td className="text-center small text-muted d-none d-sm-table-cell text-nowrap">
                        {[item.demanda, item.concorrencia, item.margem, item.frete, item.facilidade_explicar].join(" · ")}
                      </td>
                      <td className="text-center fw-semibold">{item.total}</td>
                      <td><Veredito codigo={item.veredito} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
