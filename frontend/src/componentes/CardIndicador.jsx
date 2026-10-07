/** Card de um indicador: título, valor grande e um detalhe opcional. */
export default function CardIndicador({ titulo, valor, detalhe, corValor = "" }) {
  return (
    <div className="card h-100 shadow-sm">
      <div className="card-body py-3">
        <div className="small text-muted">{titulo}</div>
        <div className={`fs-4 fw-bold ${corValor}`}>{valor}</div>
        {detalhe && <div className="small text-muted">{detalhe}</div>}
      </div>
    </div>
  );
}
