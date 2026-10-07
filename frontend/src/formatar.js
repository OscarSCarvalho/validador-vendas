// Formatação para exibição. Os cálculos ficam no backend (regras.py).

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const percentual = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 });
const numero = new Intl.NumberFormat("pt-BR");

const valido = (valor) => typeof valor === "number" && Number.isFinite(valor);

/** 1234.5 -> "R$ 1.234,50"; null -> "–" */
export const formatarMoeda = (valor) => (valido(valor) ? moeda.format(valor) : "–");

/** 0.45 -> "45%"; 0.4567 -> "45,7%"; null -> "–" */
export const formatarPercentual = (valor) => (valido(valor) ? percentual.format(valor) : "–");

/** 10000 -> "10.000"; null -> "–" */
export const formatarNumero = (valor) => (valido(valor) ? numero.format(valor) : "–");

/** "2026-10-06" -> "06/10/2026" */
export function formatarData(texto) {
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(texto ?? "");
  return partes ? `${partes[3]}/${partes[2]}/${partes[1]}` : "–";
}

/** Data de hoje no fuso local, em "AAAA-MM-DD". */
export function hojeIso() {
  return paraIso(new Date());
}

/** "2026-10-01" + 6 dias -> "2026-10-07" */
export function somarDias(iso, dias) {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return paraIso(new Date(ano, mes - 1, dia + dias));
}

function paraIso(data) {
  const doisDigitos = (n) => String(n).padStart(2, "0");
  return `${data.getFullYear()}-${doisDigitos(data.getMonth() + 1)}-${doisDigitos(data.getDate())}`;
}

/** "Leitor de código de barras" -> "leitor-de-codigo-de-barras" (nome de campanha UTM) */
export function paraCampanha(texto) {
  return (texto ?? "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

/** "Camiseta UV masculina" -> "camisetauvmasculina" (Sub_id da Shopee: só letras e números, até 30) */
export const paraSubId = (texto) => paraCampanha(texto).replace(/-/g, "").slice(0, 30);

/** "2026-10-06 14:05:09" (horário local do banco) -> "06/10/2026 14:05" */
export function formatarDataHora(texto) {
  const partes = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(texto ?? "");
  if (!partes) return "–";
  const [, ano, mes, dia, hora, minuto] = partes;
  return `${dia}/${mes}/${ano} ${hora}:${minuto}`;
}

/** 200 -> "200,00" (para preencher campos de formulário) */
export const formatarDecimal = (valor) => (valido(valor) ? valor.toFixed(2).replace(".", ",") : "");
