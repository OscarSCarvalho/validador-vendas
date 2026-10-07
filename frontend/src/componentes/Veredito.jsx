// Rótulo e cor de cada veredito devolvido pela API (o cálculo fica no backend).
const VEREDITOS = {
  // Pontuação
  vale_testar: ["Vale testar", "success"],
  testar_com_cautela: ["Testar com cautela", "warning"],
  descartar: ["Descartar", "danger"],
  // Teste de venda
  escalar: ["Escalar", "success"],
  ajustar: ["Ajustar", "warning"],
  trocar: ["Trocar de produto", "danger"],
  continue_testando: ["Continue testando", "secondary"],
};

/** [rótulo, cor do Bootstrap] de um veredito. */
export function rotuloVeredito(codigo) {
  return VEREDITOS[codigo] ?? [codigo, "secondary"];
}

/** Selo do veredito. Com `total`, mostra o destaque grande (verde, âmbar ou vermelho). */
export default function Veredito({ codigo, total, maximo = 25 }) {
  const [rotulo, cor] = rotuloVeredito(codigo);

  if (total === undefined) {
    return <span className={`badge text-bg-${cor}`}>{rotulo}</span>;
  }
  return (
    <div className={`border border-${cor} border-2 rounded p-3 text-center bg-${cor}-subtle`}>
      <div className="display-6 fw-bold">
        {total}<span className="fs-5 text-muted"> / {maximo}</span>
      </div>
      <div className={`fs-5 fw-semibold text-${cor}-emphasis`}>{rotulo}</div>
    </div>
  );
}
