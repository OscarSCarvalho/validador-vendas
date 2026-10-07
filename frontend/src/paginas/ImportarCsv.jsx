import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { buscarTeste, importarCsv, previaCsv } from "../api.js";
import ListaErros from "../componentes/ListaErros.jsx";
import { formatarData, formatarMoeda, formatarNumero } from "../formatar.js";

const CONTAR_LINHAS = "__contar_linhas__";
const CAMPOS = [
  { campo: "data", rotulo: "Data", obrigatorio: true },
  { campo: "investimento", rotulo: "Investimento", dinheiro: true },
  { campo: "impressoes", rotulo: "Impressões" },
  { campo: "cliques", rotulo: "Cliques" },
  { campo: "visitas", rotulo: "Visitas" },
  { campo: "carrinhos", rotulo: "Carrinhos" },
  { campo: "vendas", rotulo: "Vendas" },
  { campo: "receita", rotulo: "Receita", dinheiro: true },
];
const ROTULOS_AFILIADO = { visitas: "Cliques no link", vendas: "Pedidos", receita: "Comissão" };
const MAXIMO_IGNORADAS_VISIVEIS = 10;

/** Importação de métricas diárias por CSV: arquivo → colunas → prévia → importar. */
export default function ImportarCsv() {
  const { id } = useParams();
  const navegar = useNavigate();
  const [resumo, setResumo] = useState(null);
  const [arquivo, setArquivo] = useState(null);
  const [previa, setPrevia] = useState(null);
  const [erros, setErros] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [importando, setImportando] = useState(false);

  useEffect(() => {
    buscarTeste(id).then(setResumo).catch((erro) => setErros(erro.erros));
  }, [id]);

  async function pedirPrevia(novoArquivo, mapeamento) {
    setCarregando(true);
    try {
      setPrevia(await previaCsv(id, novoArquivo, mapeamento));
      setErros([]);
    } catch (erro) {
      setErros(erro.erros);
      if (!mapeamento) setPrevia(null);
    } finally {
      setCarregando(false);
    }
  }

  function escolherArquivo(evento) {
    const escolhido = evento.target.files[0];
    setArquivo(escolhido ?? null);
    setPrevia(null);
    if (escolhido) pedirPrevia(escolhido);
  }

  function mudarColuna(campo, coluna) {
    const mapeamento = { ...previa.mapeamento, [campo]: coluna || null };
    setPrevia({ ...previa, mapeamento });
    pedirPrevia(arquivo, mapeamento);
  }

  async function importar() {
    setImportando(true);
    try {
      const resposta = await importarCsv(id, arquivo, previa.mapeamento);
      navegar(`/testes/${id}`, {
        state: { mensagem: `${resposta.importados} dia(s) importado(s) do CSV: ${resposta.novos} novo(s), ${resposta.atualizados} atualizado(s).` },
      });
    } catch (erro) {
      setErros(erro.erros);
      setImportando(false);
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

  const { teste, produto } = resumo;
  const rotuloCampo = (campo, rotulo) => (produto.modelo === "afiliado" && ROTULOS_AFILIADO[campo]) || rotulo;
  const camposImportados = previa ? CAMPOS.filter(({ campo }) => campo !== "data" && previa.mapeamento[campo]) : [];
  const foraDoPeriodo = previa ? previa.dias.filter((d) => d.fora_do_periodo).length : 0;
  const atualiza = previa ? previa.dias.filter((d) => d.situacao === "atualiza").length : 0;

  return (
    <>
      <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
        <div>
          <h1 className="h3 mb-1">Importar CSV</h1>
          <p className="text-muted small mb-0">
            {produto.nome} · {teste.canal} · {formatarData(teste.data_inicio)} a {formatarData(teste.data_fim)}
          </p>
        </div>
        <Link to={`/testes/${id}`} className="btn btn-outline-secondary btn-sm">Voltar</Link>
      </div>

      <div className="card card-body shadow-sm mb-3">
        <label htmlFor="arquivo" className="form-label fw-semibold">1. Escolha o arquivo</label>
        <input id="arquivo" type="file" className="form-control" accept=".csv,text/csv" onChange={escolherArquivo} />
        <div className="form-text">
          Exportado do gerenciador de anúncios (Meta, Google) ou da plataforma (pedidos). Até 2 MB.
        </div>
      </div>

      <ListaErros erros={erros} />

      {previa && (
        <>
          <div className="card card-body shadow-sm mb-3">
            <h2 className="h6 fw-semibold">2. Confira qual coluna é qual</h2>
            <p className="small text-muted">
              Sugerimos pelo nome das colunas ({previa.total_linhas} linhas no arquivo). Campos em "não importar"
              não mudam o que já está lançado.
            </p>
            {previa.aviso && <div className="alert alert-warning py-2">{previa.aviso}</div>}
            {(previa.mapeamento.vendas || previa.mapeamento.receita) && (
              <div className="alert alert-secondary py-2 small">
                Se este teste recebe pedidos pela integração (Nuvemshop ou Shopify), não importe vendas e
                receita por CSV: elas seriam contadas duas vezes.
              </div>
            )}
            <div className="row g-2">
              {CAMPOS.map(({ campo, rotulo, obrigatorio }) => (
                <div key={campo} className="col-12 col-sm-6 col-lg-3">
                  <label htmlFor={`coluna-${campo}`} className="form-label small mb-1">
                    {rotuloCampo(campo, rotulo)}{obrigatorio && " *"}
                  </label>
                  <select id={`coluna-${campo}`} className="form-select form-select-sm" disabled={carregando}
                          value={previa.mapeamento[campo] ?? ""} onChange={(e) => mudarColuna(campo, e.target.value)}>
                    <option value="">{obrigatorio ? "— escolha —" : "— não importar —"}</option>
                    {campo === "vendas" && <option value={CONTAR_LINHAS}>Contar 1 por linha (pedidos)</option>}
                    {previa.colunas.map((coluna) => <option key={coluna} value={coluna}>{coluna}</option>)}
                  </select>
                </div>
              ))}
            </div>
          </div>

          <div className="card card-body shadow-sm mb-3">
            <h2 className="h6 fw-semibold">3. Prévia ({previa.dias.length} dia{previa.dias.length === 1 ? "" : "s"})</h2>
            {atualiza > 0 && (
              <div className="alert alert-info py-2 small">
                {atualiza} dia(s) já lançado(s) serão atualizados só nos campos importados.
              </div>
            )}
            {foraDoPeriodo > 0 && (
              <div className="alert alert-warning py-2 small">
                {foraDoPeriodo} dia(s) fora do período do teste. Eles também serão importados.
              </div>
            )}
            {previa.ignoradas.length > 0 && (
              <div className="alert alert-warning py-2 small">
                <div className="fw-semibold">{previa.ignoradas.length} linha(s) ignorada(s):</div>
                <ul className="mb-0 ps-3">
                  {previa.ignoradas.slice(0, MAXIMO_IGNORADAS_VISIVEIS).map((item) => (
                    <li key={item.linha}>Linha {item.linha}: {item.motivo}</li>
                  ))}
                  {previa.ignoradas.length > MAXIMO_IGNORADAS_VISIVEIS && (
                    <li>e mais {previa.ignoradas.length - MAXIMO_IGNORADAS_VISIVEIS}.</li>
                  )}
                </ul>
              </div>
            )}

            {previa.dias.length > 0 && (
              <div className="table-responsive border rounded mb-3">
                <table className="table table-sm align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>Data</th>
                      <th></th>
                      {camposImportados.map(({ campo, rotulo }) => <th key={campo} className="text-end">{rotuloCampo(campo, rotulo)}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {previa.dias.map((dia) => (
                      <tr key={dia.data}>
                        <td className="text-nowrap">{formatarData(dia.data)}</td>
                        <td className="text-nowrap">
                          <span className={`badge ${dia.situacao === "novo" ? "text-bg-success" : "text-bg-info"}`}>
                            {dia.situacao === "novo" ? "Novo" : "Atualiza"}
                          </span>
                          {dia.fora_do_periodo && <span className="badge text-bg-warning ms-1">Fora do período</span>}
                        </td>
                        {camposImportados.map(({ campo, dinheiro }) => (
                          <td key={campo} className="text-end">
                            {dinheiro ? formatarMoeda(dia[campo]) : formatarNumero(dia[campo])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="d-flex align-items-center gap-2">
              <button type="button" className="btn btn-primary" onClick={importar}
                      disabled={importando || carregando || !previa.dias.length || Boolean(previa.aviso)}>
                {importando ? "Importando..." : `Importar ${previa.dias.length} dia${previa.dias.length === 1 ? "" : "s"}`}
              </button>
              {carregando && <span className="small text-muted">Atualizando prévia...</span>}
            </div>
          </div>
        </>
      )}
    </>
  );
}
