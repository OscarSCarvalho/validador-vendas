import { useState } from "react";
import { formatarDecimal } from "../formatar.js";
import ListaErros from "./ListaErros.jsx";

const CANAIS_SUGERIDOS = ["Facebook Ads", "Instagram Ads", "Google Ads", "TikTok Ads", "WhatsApp", "Grupos", "Orgânico"];

/** Formulário de teste de venda (criar ou editar). `inicial` traz os valores; `aoSalvar` recebe os dados. */
export default function FormularioTeste({ inicial, textoBotao, aoSalvar, aoCancelar, afiliado = false }) {
  const [teste, setTeste] = useState({
    canal: inicial.canal ?? "",
    utm_campanha: inicial.utm_campanha ?? "",
    verba_diaria: typeof inicial.verba_diaria === "number" ? formatarDecimal(inicial.verba_diaria) : inicial.verba_diaria ?? "",
    data_inicio: inicial.data_inicio ?? "",
    data_fim: inicial.data_fim ?? "",
  });
  const [erros, setErros] = useState([]);
  const [enviando, setEnviando] = useState(false);

  const alterar = (evento) => setTeste({ ...teste, [evento.target.name]: evento.target.value });

  async function aoEnviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    try {
      await aoSalvar(teste);
    } catch (erro) {
      setErros(erro.erros);
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={aoEnviar}>
      <ListaErros erros={erros} />
      <div className="row g-2">
        <div className="col-12 col-sm-6">
          <label htmlFor="canal" className="form-label small mb-1">Canal</label>
          <input id="canal" name="canal" className="form-control" list="canais-sugeridos"
                 value={teste.canal} onChange={alterar} required />
          <datalist id="canais-sugeridos">{CANAIS_SUGERIDOS.map((c) => <option key={c} value={c} />)}</datalist>
        </div>
        <div className="col-12 col-sm-6">
          <label htmlFor="utm_campanha" className="form-label small mb-1">
            {afiliado ? "Sub_id do link de afiliado" : "Campanha (utm_campaign)"}
          </label>
          <input id="utm_campanha" name="utm_campanha" className="form-control"
                 value={teste.utm_campanha} onChange={alterar} required />
        </div>
        <div className="col-12 col-sm-4">
          <label htmlFor="verba_diaria" className="form-label small mb-1">Verba diária (R$)</label>
          <input id="verba_diaria" name="verba_diaria" className="form-control" inputMode="decimal"
                 value={teste.verba_diaria} onChange={alterar} placeholder="0,00" required />
        </div>
        <div className="col-6 col-sm-4">
          <label htmlFor="data_inicio" className="form-label small mb-1">Início</label>
          <input id="data_inicio" name="data_inicio" type="date" className="form-control"
                 value={teste.data_inicio} onChange={alterar} required />
        </div>
        <div className="col-6 col-sm-4">
          <label htmlFor="data_fim" className="form-label small mb-1">Fim</label>
          <input id="data_fim" name="data_fim" type="date" className="form-control"
                 value={teste.data_fim} onChange={alterar} required />
        </div>
      </div>
      <div className="form-text mb-2">Sugestão do método: R$ 30 a 50 por dia durante 7 dias. Orgânico pode ter verba 0.</div>
      <div className="d-flex gap-2">
        <button type="submit" className="btn btn-primary" disabled={enviando}>
          {enviando ? "Salvando..." : textoBotao}
        </button>
        {aoCancelar && <button type="button" className="btn btn-outline-secondary" onClick={aoCancelar}>Cancelar</button>}
      </div>
    </form>
  );
}
