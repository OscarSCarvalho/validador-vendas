import { BarElement, CategoryScale, Chart, Legend, LinearScale, Tooltip } from "chart.js";
import { Bar } from "react-chartjs-2";
import { formatarData, formatarMoeda } from "../formatar.js";

Chart.register(BarElement, CategoryScale, LinearScale, Legend, Tooltip);

const COR_INVESTIMENTO = "#dc3545"; // vermelho do Bootstrap
const COR_RECEITA = "#198754";      // verde do Bootstrap

/** Barras de investimento × receita para cada dia lançado do teste. */
export default function GraficoInvestimentoReceita({ metricas, rotuloReceita = "Receita" }) {
  if (!metricas.length) {
    return <p className="text-muted mb-0">Este teste ainda não tem dias lançados.</p>;
  }

  const dados = {
    labels: metricas.map((m) => formatarData(m.data).slice(0, 5)), // "06/10"
    datasets: [
      { label: "Investimento", data: metricas.map((m) => m.investimento), backgroundColor: COR_INVESTIMENTO },
      { label: rotuloReceita, data: metricas.map((m) => m.receita), backgroundColor: COR_RECEITA },
    ],
  };
  const opcoes = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "bottom" },
      tooltip: { callbacks: { label: (item) => `${item.dataset.label}: ${formatarMoeda(item.parsed.y)}` } },
    },
    scales: {
      y: { beginAtZero: true, ticks: { callback: (valor) => formatarMoeda(valor) } },
    },
  };

  return (
    <div style={{ height: "280px" }}>
      <Bar data={dados} options={opcoes} aria-label="Gráfico de investimento e receita por dia" role="img" />
    </div>
  );
}
