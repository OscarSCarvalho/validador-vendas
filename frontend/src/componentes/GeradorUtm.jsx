import { useRef, useState } from "react";
import { paraCampanha } from "../formatar.js";

const ORIGENS = ["facebook", "instagram", "google", "tiktok", "whatsapp"];
const MEIOS = ["cpc", "social", "organico", "email"];

function montarLink(urlProduto, parametros) {
  let url;
  try {
    url = new URL(urlProduto);
  } catch {
    return null;
  }
  for (const [nome, valor] of Object.entries(parametros)) {
    const limpo = valor.trim().toLowerCase();
    if (limpo) url.searchParams.set(nome, limpo);
  }
  return url.toString();
}

/** Monta o link do produto com utm_source, utm_medium e utm_campaign, com botão copiar. */
export default function GeradorUtm({ urlProduto, nomeProduto }) {
  const [origem, setOrigem] = useState("");
  const [meio, setMeio] = useState("");
  const [campanha, setCampanha] = useState(paraCampanha(nomeProduto));
  const [copiado, setCopiado] = useState(false);
  const campoLink = useRef(null);

  if (!urlProduto) {
    return (
      <div className="alert alert-warning mb-0">
        Cadastre a URL do produto (em Editar) para gerar os links com UTM.
      </div>
    );
  }

  const link = montarLink(urlProduto, { utm_source: origem, utm_medium: meio, utm_campaign: campanha });
  const completo = origem.trim() && meio.trim() && campanha.trim();

  async function copiar() {
    try {
      await navigator.clipboard.writeText(link);
    } catch {
      // Sem acesso à área de transferência (ex.: http fora do localhost): seleciona para copiar.
      campoLink.current.select();
      document.execCommand("copy");
    }
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  }

  return (
    <div>
      <div className="row g-2 mb-2">
        <div className="col-6">
          <label htmlFor="utm_source" className="form-label small mb-1">Origem (utm_source)</label>
          <input id="utm_source" className="form-control form-control-sm" list="utm-origens"
                 value={origem} onChange={(e) => setOrigem(e.target.value)} placeholder="facebook" />
          <datalist id="utm-origens">{ORIGENS.map((o) => <option key={o} value={o} />)}</datalist>
        </div>
        <div className="col-6">
          <label htmlFor="utm_medium" className="form-label small mb-1">Meio (utm_medium)</label>
          <input id="utm_medium" className="form-control form-control-sm" list="utm-meios"
                 value={meio} onChange={(e) => setMeio(e.target.value)} placeholder="cpc" />
          <datalist id="utm-meios">{MEIOS.map((m) => <option key={m} value={m} />)}</datalist>
        </div>
        <div className="col-12">
          <label htmlFor="utm_campaign" className="form-label small mb-1">Campanha (utm_campaign)</label>
          <input id="utm_campaign" className="form-control form-control-sm"
                 value={campanha} onChange={(e) => setCampanha(e.target.value)} />
        </div>
      </div>
      {link === null ? (
        <div className="alert alert-warning py-2 mb-0 small">A URL do produto é inválida. Corrija em Editar.</div>
      ) : (
        <>
          <label htmlFor="link_utm" className="form-label small mb-1">Link pronto</label>
          <div className="input-group input-group-sm">
            <input id="link_utm" ref={campoLink} className="form-control font-monospace" value={link} readOnly
                   onFocus={(e) => e.target.select()} />
            <button type="button" className={`btn ${copiado ? "btn-success" : "btn-primary"}`}
                    onClick={copiar} disabled={!completo}>
              {copiado ? "Copiado!" : "Copiar"}
            </button>
          </div>
          {!completo && <div className="form-text">Preencha origem, meio e campanha para copiar.</div>}
        </>
      )}
    </div>
  );
}
