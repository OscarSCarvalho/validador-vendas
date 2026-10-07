import { useState } from "react";
import { IconeOlho, IconeOlhoRiscado } from "./Icones.jsx";

/** Campo de senha com o botão de olho (dentro do campo, à direita) para mostrar ou esconder. */
export default function CampoSenha({ id, valor, aoMudar, ...resto }) {
  const [visivel, setVisivel] = useState(false);
  const texto = visivel ? "Ocultar senha" : "Mostrar senha";
  return (
    <div className="campo-com-icone">
      <input type={visivel ? "text" : "password"} className="form-control form-control-lg com-botao-olho"
             id={id} value={valor} onChange={(e) => aoMudar(e.target.value)} {...resto} />
      <button type="button" className="botao-olho" onClick={() => setVisivel(!visivel)}
              aria-label={texto} aria-pressed={visivel} title={texto}>
        {visivel ? <IconeOlhoRiscado tamanho={18} /> : <IconeOlho tamanho={18} />}
      </button>
    </div>
  );
}
