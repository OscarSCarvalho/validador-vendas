import { formatarNumero, formatarPercentual } from "../formatar.js";

/**
 * Funil em barras (impressões → cliques → visitas → carrinhos → vendas).
 * A largura usa escala logarítmica: com escala normal, 3 vendas ao lado de 10.000 impressões
 * ficariam invisíveis. Os números e as taxas vêm prontos da API.
 */
export default function Funil({ etapas }) {
  const maior = Math.max(...etapas.map((e) => e.valor), 1);
  const largura = (valor) => (valor > 0 ? Math.max(4, (Math.log10(valor + 1) / Math.log10(maior + 1)) * 100) : 0);

  return (
    <div>
      {etapas.map((etapa) => (
        <div key={etapa.etapa} className="mb-2">
          <div className="d-flex justify-content-between small">
            <span className="fw-semibold">{etapa.rotulo}</span>
            <span>
              {formatarNumero(etapa.valor)}
              {etapa.taxa !== null && etapa.taxa !== undefined && (
                <span className="text-muted"> · {formatarPercentual(etapa.taxa)} da etapa anterior</span>
              )}
              {etapa.taxa === null && etapa.etapa !== etapas[0].etapa && (
                <span className="text-muted"> · –</span>
              )}
            </span>
          </div>
          <div className="progress" style={{ height: "1.25rem" }} role="presentation">
            <div className="progress-bar" style={{ width: `${largura(etapa.valor)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
