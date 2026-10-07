import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { atualizarTeste, buscarTeste, excluirMetricasDia, excluirTeste, salvarMetricasDia } from "../api.js";
import CardIndicador from "../componentes/CardIndicador.jsx";
import FormularioTeste from "../componentes/FormularioTeste.jsx";
import Funil from "../componentes/Funil.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import { rotuloVeredito } from "../componentes/Veredito.jsx";
import { formatarData, formatarDecimal, formatarMoeda, formatarNumero, formatarPercentual, hojeIso } from "../formatar.js";

const CAMPOS_DIA = [
  { campo: "investimento", rotulo: "Investimento (R$)", dinheiro: true },
  { campo: "impressoes", rotulo: "Impressões" },
  { campo: "cliques", rotulo: "Cliques" },
  { campo: "visitas", rotulo: "Visitas" },
  { campo: "carrinhos", rotulo: "Carrinhos" },
  { campo: "vendas", rotulo: "Vendas" },
  { campo: "receita", rotulo: "Receita (R$)", dinheiro: true },
];
// Afiliado: sem carrinho; "visitas" = cliques no link; "vendas" = pedidos; "receita" = comissão recebida.
const CAMPOS_DIA_AFILIADO = [
  { campo: "investimento", rotulo: "Investimento (R$)", dinheiro: true },
  { campo: "impressoes", rotulo: "Impressões" },
  { campo: "cliques", rotulo: "Cliques no anúncio" },
  { campo: "visitas", rotulo: "Cliques no link (Shopee)" },
  { campo: "vendas", rotulo: "Pedidos" },
  { campo: "receita", rotulo: "Comissão (R$)", dinheiro: true },
];
/** Afiliado: o veredito compara o investimento com a comissão recebida, a partir de alguns dias de teste. */
function descricaoVereditoAfiliado({ codigo, razao_cpa_margem: razao, dias_lancados: lancados, dias_minimos: minimos }) {
  const faltam = minimos - lancados;
  return {
    escalar: "O investimento está em até 70% da comissão recebida. Aumente a verba aos poucos.",
    ajustar: "O investimento está entre 70% e 100% da comissão recebida. Ajuste o criativo, o público ou escolha uma oferta com comissão maior.",
    trocar: razao === null
      ? `${lancados} dias lançados sem nenhuma comissão. Troque de produto ou de oferta.`
      : "O investimento passou da comissão recebida. Troque de produto ou de oferta.",
    continue_testando: `O veredito sai com ${minimos} dias lançados (falta${faltam > 1 ? "m" : ""} ${faltam}): ` +
      "um clique ainda pode virar comissão em até 7 dias. Continue o teste.",
  }[codigo];
}

const DESCRICOES_VEREDITO = {
  escalar: "O custo por venda está em até 70% da margem. Aumente a verba aos poucos.",
  ajustar: "O custo por venda está entre 70% e 100% da margem. Ajuste o criativo, o preço ou a página.",
  trocar: "O custo por venda passou da margem (ou o investimento sem vendas já passou da margem).",
  continue_testando: "Ainda sem vendas, mas o investimento não passou da margem. Continue o teste.",
};
const ESCALA_BARRA = 1.5; // a barra vai até 150% da margem

/** Valores do formulário do dia: os do dia já lançado ou em branco. */
function valoresDoDia(metricas, data) {
  const salvo = metricas.find((m) => m.data === data);
  return Object.fromEntries(CAMPOS_DIA.map(({ campo, dinheiro }) => [
    campo, salvo ? (dinheiro ? formatarDecimal(salvo[campo]) : String(salvo[campo])) : "",
  ]));
}

function BarraCpaMargem({ veredito, indicadores, produto, totais }) {
  const razao = veredito.razao_cpa_margem;
  const afiliado = produto.modelo === "afiliado";
  if (afiliado && razao === null) {
    return <p className="small mb-0">Nenhuma comissão recebida: investido {formatarMoeda(totais.investimento)}.</p>;
  }
  if (razao === null) {
    return (
      <p className="small mb-0">
        {totais.vendas === 0
          ? `Sem vendas: investido ${formatarMoeda(totais.investimento)} de uma margem de ${formatarMoeda(produto.margem_unitaria)} por venda.`
          : "Margem do produto zerada ou negativa: revise o preço e o custo."}
      </p>
    );
  }
  const [, cor] = rotuloVeredito(veredito.codigo);
  const posicao = (valor) => `${(Math.min(valor, ESCALA_BARRA) / ESCALA_BARRA) * 100}%`;
  return (
    <div>
      <p className="small mb-2">
        {afiliado ? (
          <>Investimento de <strong>{formatarMoeda(totais.investimento)}</strong> = <strong>{formatarPercentual(razao)}</strong>{" "}
            da comissão recebida de {formatarMoeda(totais.receita)}.</>
        ) : (
          <>CPA de <strong>{formatarMoeda(indicadores.cpa)}</strong> = <strong>{formatarPercentual(razao)}</strong> da{" "}
            margem de {formatarMoeda(produto.margem_unitaria)}.</>
        )}
      </p>
      <div className="position-relative pb-4">
        <div className="progress" style={{ height: "1rem" }}>
          <div className={`progress-bar bg-${cor}`} style={{ width: posicao(razao) }} />
        </div>
        {[[0.7, "70%"], [1, "100%"]].map(([valor, texto]) => (
          <div key={texto} className="position-absolute top-0 small text-muted text-center"
               style={{ left: posicao(valor), transform: "translateX(-50%)" }}>
            <div className="border-start border-2 border-dark mx-auto" style={{ height: "1rem", width: 0 }} />
            {texto}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TesteVenda() {
  const { id } = useParams();
  const navegar = useNavigate();
  const [resumo, setResumo] = useState(null);
  const [erros, setErros] = useState([]);
  const [data, setData] = useState(hojeIso());
  const [dia, setDia] = useState(valoresDoDia([], hojeIso()));
  const [errosDia, setErrosDia] = useState([]);
  const [mensagemDia, setMensagemDia] = useState("");
  const [salvandoDia, setSalvandoDia] = useState(false);
  const [editando, setEditando] = useState(false);
  const [mensagem, setMensagem] = useState(useLocation().state?.mensagem ?? "");

  useEffect(() => {
    buscarTeste(id)
      .then((dados) => {
        setResumo(dados);
        setDia(valoresDoDia(dados.metricas, hojeIso()));
      })
      .catch((erro) => setErros(erro.erros));
  }, [id]);

  function escolherData(novaData, metricas = resumo.metricas) {
    setData(novaData);
    setDia(valoresDoDia(metricas, novaData));
    setErrosDia([]);
    setMensagemDia("");
  }

  /** Recarrega o teste e traz para o formulário só os campos que mudaram no servidor; o resto fica como digitado. */
  async function juntarComOServidor() {
    const novo = await buscarTeste(id).catch(() => null);
    if (!novo) return;
    const anterior = valoresDoDia(resumo.metricas, data);
    const servidor = valoresDoDia(novo.metricas, data);
    setResumo(novo);
    setDia(Object.fromEntries(Object.keys(servidor).map((campo) => [
      campo, servidor[campo] !== anterior[campo] ? servidor[campo] : dia[campo],
    ])));
  }

  async function salvarDia(evento) {
    evento.preventDefault();
    setSalvandoDia(true);
    setMensagemDia("");
    // base: o dia como esta página o conhece. Se mudou no servidor (ex.: venda pelo webhook), a API responde 409.
    const base = resumo.metricas.find((m) => m.data === data) ?? null;
    try {
      const novo = await salvarMetricasDia(id, data, { ...dia, base });
      setResumo(novo);
      setDia(valoresDoDia(novo.metricas, data));
      setErrosDia([]);
      setMensagemDia(`Dia ${formatarData(data)} salvo.`);
    } catch (erro) {
      if (erro.status === 409) await juntarComOServidor();
      setErrosDia(erro.erros);
    } finally {
      setSalvandoDia(false);
    }
  }

  async function apagarDia(dataDia) {
    if (!window.confirm(`Excluir as métricas de ${formatarData(dataDia)}?`)) return;
    try {
      const novo = await excluirMetricasDia(id, dataDia);
      setResumo(novo);
      if (dataDia === data) setDia(valoresDoDia(novo.metricas, data));
    } catch (erro) {
      setErros(erro.erros);
    }
  }

  async function salvarTeste(dados) {
    setResumo(await atualizarTeste(id, { ...dados, status: resumo.teste.status }));
    setEditando(false);
  }

  async function alternarEncerrado() {
    const { teste } = resumo;
    try {
      setResumo(await atualizarTeste(id, { ...teste, status: teste.status === "encerrado" ? "em_andamento" : "encerrado" }));
    } catch (erro) {
      setErros(erro.erros);
    }
  }

  async function apagarTeste() {
    if (!window.confirm("Excluir este teste e todas as métricas dele?")) return;
    try {
      await excluirTeste(id);
      navegar(`/produtos/${resumo.teste.produto_id}/testes`);
    } catch (erro) {
      setErros(erro.erros);
    }
  }

  if (!resumo) {
    return (
      <>
        <ListaErros erros={erros} />
        {erros.length ? <Link to="/produtos">Voltar para a lista de produtos</Link>
                      : <p className="text-muted">Carregando...</p>}
      </>
    );
  }

  const { teste, produto, metricas, totais, indicadores, funil, veredito, alertas } = resumo;
  const [rotulo, cor] = rotuloVeredito(veredito.codigo);
  const encerrado = teste.status === "encerrado";
  const afiliado = produto.modelo === "afiliado";
  const camposDia = afiliado ? CAMPOS_DIA_AFILIADO : CAMPOS_DIA;

  return (
    <>
      <div className="d-flex justify-content-between align-items-start gap-2 mb-3 flex-wrap">
        <div>
          <h1 className="h3 mb-1">
            Teste: {teste.canal}
            {encerrado && <span className="badge text-bg-secondary fs-6 align-middle ms-2">Encerrado</span>}
          </h1>
          <p className="text-muted mb-0 small">
            {produto.nome} · {teste.utm_campanha} · {formatarData(teste.data_inicio)} a {formatarData(teste.data_fim)} ·
            verba de {formatarMoeda(teste.verba_diaria)}/dia
          </p>
        </div>
        <div className="d-flex gap-1 flex-wrap">
          <Link to={`/produtos/${produto.id}/testes`} className="btn btn-sm btn-outline-secondary">Voltar</Link>
          <Link to={`/testes/${id}/importar`} className="btn btn-sm btn-outline-primary">Importar CSV</Link>
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setEditando(!editando)}>Editar</button>
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={alternarEncerrado}>
            {encerrado ? "Reabrir" : "Encerrar teste"}
          </button>
          <button type="button" className="btn btn-sm btn-outline-danger" onClick={apagarTeste}>Excluir</button>
        </div>
      </div>
      <ListaErros erros={erros} />
      {alertas.length > 0 && (
        <div className="alert alert-danger" role="alert">
          <div className="fw-semibold mb-1">⚠ Atenção</div>
          <ul className="mb-0 ps-3">
            {alertas.map((alerta) => <li key={alerta.codigo}>{alerta.mensagem}</li>)}
          </ul>
        </div>
      )}
      {mensagem && (
        <div className="alert alert-success alert-dismissible" role="alert">
          {mensagem}
          <button type="button" className="btn-close" aria-label="Fechar" onClick={() => setMensagem("")} />
        </div>
      )}

      {editando && (
        <div className="card card-body shadow-sm mb-3">
          <FormularioTeste inicial={teste} textoBotao="Salvar teste" aoSalvar={salvarTeste}
                           aoCancelar={() => setEditando(false)} />
        </div>
      )}

      <div className="row g-4">
        <div className="col-12 col-lg-5 order-lg-2">
          <div className="card shadow-sm">
            <div className="card-body">
              <h2 className="h5">Lançar dia</h2>
              <form onSubmit={salvarDia}>
                <div className="mb-2">
                  <label htmlFor="data" className="form-label small mb-1">Data</label>
                  <input id="data" type="date" className="form-control" value={data} required
                         onChange={(e) => escolherData(e.target.value)} />
                </div>
                <div className="row g-2 mb-2">
                  {camposDia.map(({ campo, rotulo: rotuloCampo, dinheiro }) => (
                    <div key={campo} className="col-6">
                      <label htmlFor={campo} className="form-label small mb-1">{rotuloCampo}</label>
                      <input id={campo} className="form-control" inputMode={dinheiro ? "decimal" : "numeric"}
                             placeholder={dinheiro ? "0,00" : "0"} value={dia[campo]}
                             onChange={(e) => setDia({ ...dia, [campo]: e.target.value })} />
                    </div>
                  ))}
                </div>
                <ListaErros erros={errosDia} />
                <div className="d-flex align-items-center gap-2">
                  <button type="submit" className="btn btn-primary" disabled={salvandoDia}>
                    {salvandoDia ? "Salvando..." : "Salvar dia"}
                  </button>
                  {mensagemDia && <span className="small text-success">{mensagemDia}</span>}
                </div>
                <div className="form-text">Campos vazios contam como zero. Lançar o mesmo dia de novo corrige os números.</div>
              </form>
            </div>
          </div>
        </div>

        <div className="col-12 col-lg-7 order-lg-1">
          <div className={`border border-${cor} border-2 rounded p-3 mb-3 bg-${cor}-subtle`}>
            <div className="small text-muted">Veredito do teste</div>
            <div className={`fs-3 fw-bold text-${cor}-emphasis`}>{rotulo}</div>
            <p className="small mb-3">{afiliado ? descricaoVereditoAfiliado(veredito) : DESCRICOES_VEREDITO[veredito.codigo]}</p>
            <BarraCpaMargem veredito={veredito} indicadores={indicadores} produto={produto} totais={totais} />
          </div>

          <div className="row g-2 mb-3">
            <div className="col-6 col-md-3">
              <CardIndicador titulo="CTR" valor={formatarPercentual(indicadores.ctr)} detalhe="cliques ÷ impressões" />
            </div>
            <div className="col-6 col-md-3">
              <CardIndicador titulo="Conversão" valor={formatarPercentual(indicadores.taxa_conversao)} detalhe={afiliado ? "pedidos ÷ cliques no link" : "vendas ÷ visitas"} />
            </div>
            <div className="col-6 col-md-3">
              <CardIndicador titulo="CPA" valor={formatarMoeda(indicadores.cpa)} detalhe="custo por venda" />
            </div>
            <div className="col-6 col-md-3">
              <CardIndicador titulo="Lucro" valor={formatarMoeda(indicadores.lucro)}
                             corValor={indicadores.lucro < 0 ? "text-danger" : "text-success"}
                             detalhe={`${afiliado ? "comissão recebida" : "receita"} ${formatarMoeda(totais.receita)}`} />
            </div>
          </div>

          <div className="card card-body shadow-sm mb-3">
            <h2 className="h5">Funil</h2>
            <Funil etapas={funil} />
            <div className="small text-muted mt-1">
              Investido: {formatarMoeda(totais.investimento)}
              {!afiliado && <> · Abandono de carrinho: {formatarPercentual(indicadores.abandono_carrinho)}</>}
            </div>
          </div>
        </div>
      </div>

      <h2 className="h5 mt-4">Dias lançados</h2>
      {metricas.length === 0 ? (
        <p className="text-muted">Nenhum dia lançado ainda.</p>
      ) : (
        <div className="table-responsive bg-white border rounded">
          <table className="table table-sm table-hover align-middle mb-0">
            <thead className="table-light">
              <tr>
                <th>Data</th>
                <th className="text-end">Investido</th>
                <th className="text-end d-none d-md-table-cell">Impressões</th>
                <th className="text-end d-none d-sm-table-cell">Cliques</th>
                <th className="text-end d-none d-md-table-cell">{afiliado ? "Cliques no link" : "Visitas"}</th>
                {!afiliado && <th className="text-end d-none d-md-table-cell">Carrinhos</th>}
                <th className="text-end">{afiliado ? "Pedidos" : "Vendas"}</th>
                <th className="text-end d-none d-sm-table-cell">{afiliado ? "Comissão" : "Receita"}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {metricas.map((m) => (
                <tr key={m.data} className={m.data === data ? "table-active" : ""}>
                  <td className="text-nowrap">{formatarData(m.data)}</td>
                  <td className="text-end">{formatarMoeda(m.investimento)}</td>
                  <td className="text-end d-none d-md-table-cell">{formatarNumero(m.impressoes)}</td>
                  <td className="text-end d-none d-sm-table-cell">{formatarNumero(m.cliques)}</td>
                  <td className="text-end d-none d-md-table-cell">{formatarNumero(m.visitas)}</td>
                  {!afiliado && <td className="text-end d-none d-md-table-cell">{formatarNumero(m.carrinhos)}</td>}
                  <td className="text-end">{formatarNumero(m.vendas)}</td>
                  <td className="text-end d-none d-sm-table-cell">{formatarMoeda(m.receita)}</td>
                  <td className="text-end text-nowrap">
                    <button type="button" className="btn btn-sm btn-outline-secondary me-1"
                            onClick={() => { escolherData(m.data); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
                      Corrigir
                    </button>
                    <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => apagarDia(m.data)}>
                      Excluir
                    </button>
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
