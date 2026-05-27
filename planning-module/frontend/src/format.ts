/** Числа из API/JS без артефактов вроде 5.779999999999999 */
export function formatHours(value: number, decimals = 1): string {
  if (!Number.isFinite(value)) return "—";
  const factor = 10 ** decimals;
  const rounded = Math.round(value * factor) / factor;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(decimals);
}

export function formatNumber(value: number, decimals = 1): string {
  if (!Number.isFinite(value)) return "—";
  const factor = 10 ** decimals;
  return (Math.round(value * factor) / factor).toFixed(decimals);
}
