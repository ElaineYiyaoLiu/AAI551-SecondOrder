export type Params = { substitution: number; productivity: number; speed: number; ubi: number; tax: number };
export type Metric = 'employment' | 'income' | 'consumption' | 'profit' | 'balance' | 'concentration';
export type Year = { year: number; adoption: number; employment: number; income: number; consumption: number; profit: number; balance: number; concentration: number; output: number; laborIncome: number; benefits: number; dividend: number; aiTax: number };

export const defaults: Params = { substitution: 25, productivity: 30, speed: 10, ubi: 0, tax: 0 };
export const baseline: Year = { year: 0, adoption: 0, employment: 95, income: 60, consumption: 45, profit: 15, balance: 0, concentration: 60, output: 75, laborIncome: 60, benefits: 0, dividend: 0, aiTax: 0 };
const clamp = (n: number, low: number, high: number) => Math.min(high, Math.max(low, n));

// Demand is relative to year-zero household consumption. Keep this rule shared
// by simulation and the calculation inspector.
export function demandMultiplier(previousConsumption: number, feedback = true): number {
  return feedback ? clamp(1 + 0.42 * (previousConsumption / baseline.consumption - 1), 0.65, 1.4) : 1;
}

// Stylized annual quantities per household, in thousands of USD. These are explicit
// relationships for counterfactual exploration, not calibrated forecasts.
export function simulate(p: Params, options: { feedback?: boolean } = {}): Year[] {
  const rows = [baseline];
  for (let year = 1; year <= 10; year++) {
    const prev = rows[rows.length - 1];
    const adoption = clamp(prev.adoption + p.speed / 100 * (1 - p.tax / 100 * 0.45) * (1 - prev.adoption), 0, 1);
    const demand = demandMultiplier(prev.consumption, options.feedback !== false);
    const output = 75 * demand * (1 + p.productivity / 100 * adoption);
    const employment = clamp(95 * demand * (1 - p.substitution / 100 * adoption) / (1 + 0.55 * p.productivity / 100 * adoption), 35, 99);
    const laborIncome = 60 * employment / 95 * (1 + 0.12 * p.productivity / 100 * adoption);
    const benefits = Math.max(0, 95 - employment) / 100 * 12;
    const preTaxProfit = Math.max(0, output - laborIncome - 4 * adoption);
    const aiTax = Math.max(0, preTaxProfit - 15) * adoption * p.tax / 100;
    const profit = preTaxProfit - aiTax;
    const dividend = Math.max(0, profit - 15) * (1 - prev.concentration / 100) * 0.12;
    const income = laborIncome + benefits + p.ubi * 12 / 1000 + dividend;
    const consumption = income * 0.75;
    // Baseline labor tax and ordinary spending cancel at year zero.
    const balance = (laborIncome - 60) * 0.15 + aiTax - benefits - p.ubi * 12 / 1000;
    const concentration = clamp(prev.concentration + 0.08 * Math.max(0, profit - 15) - 0.07 * (p.ubi * 12 / 1000 + benefits) - 0.18 * aiTax, 35, 90);
    rows.push({ year, adoption, employment, income, consumption, profit, balance, concentration, output, laborIncome, benefits, dividend, aiTax });
  }
  return rows;
}

export const metrics: Metric[] = ['employment', 'income', 'consumption', 'profit', 'balance', 'concentration'];
export function format(metric: Metric, value: number, lang: 'en' | 'zh') {
  if (metric === 'employment' || metric === 'concentration') return `${value.toFixed(1)}%`;
  const currency = lang === 'en' ? '$' : '$';
  return `${value < 0 ? '-' : ''}${currency}${Math.abs(value).toFixed(1)}k`;
}
