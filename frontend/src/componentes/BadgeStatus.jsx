// Rótulo e cor de cada status de produto, na ordem do método.
export const ROTULOS_STATUS = {
  ideia: ["Ideia", "secondary"],
  pontuado: ["Pontuado", "info"],
  em_validacao: ["Em validação", "primary"],
  em_teste: ["Em teste", "primary"],
  escalar: ["Escalar", "success"],
  ajustar: ["Ajustar", "warning"],
  descartado: ["Descartado", "danger"],
};

export default function BadgeStatus({ status }) {
  const [rotulo, cor] = ROTULOS_STATUS[status] ?? [status, "secondary"];
  return <span className={`badge text-bg-${cor}`}>{rotulo}</span>;
}
