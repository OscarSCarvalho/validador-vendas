import { useState } from "react";
import { paraSubId } from "../formatar.js";

const PAINEL_AFILIADOS = "https://affiliate.shopee.com.br/dashboard";

/** Para produto de afiliado: na Shopee a UTM não chega ao pedido; o rastreio é pelo Sub_id do link. */
export default function OrientacaoSubId({ nomeProduto }) {
  const sugestao = paraSubId(nomeProduto);
  const [copiado, setCopiado] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(sugestao);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setCopiado(false);
    }
  }

  return (
    <div className="small">
      <p className="mb-2">
        Na Shopee a UTM <strong>não chega ao pedido</strong>. Como afiliado, você rastreia cada campanha pelo
        <strong> Sub_id</strong> do seu link de afiliado.
      </p>
      <ol className="ps-3 mb-3">
        <li>
          Abra o <a href={PAINEL_AFILIADOS} target="_blank" rel="noopener noreferrer">Painel de Afiliados da Shopee</a> e
          gere o link do produto (link personalizado).
        </li>
        <li>Preencha o <strong>Sub_id</strong> com o nome da campanha. Use um Sub_id diferente por canal.</li>
        <li>Use esse <strong>mesmo Sub_id</strong> como campanha do teste de venda no sistema.</li>
      </ol>
      <label htmlFor="sub_id_sugerido" className="form-label mb-1">Sugestão de Sub_id (só letras e números)</label>
      <div className="input-group input-group-sm">
        <input id="sub_id_sugerido" className="form-control font-monospace" value={sugestao} readOnly
               onFocus={(e) => e.target.select()} />
        <button type="button" className={`btn ${copiado ? "btn-success" : "btn-primary"}`} onClick={copiar}>
          {copiado ? "Copiado!" : "Copiar"}
        </button>
      </div>
      <div className="form-text">Exemplo por canal: {sugestao.slice(0, 22)}insta, {sugestao.slice(0, 22)}whats.</div>
    </div>
  );
}
