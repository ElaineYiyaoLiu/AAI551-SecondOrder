"""AAI551 annual recurrence translated from the attributed TypeScript reference.

Author: Elaine Liu, with AI development assistance. No empirical calibration.
"""
import pandas as pd
from scenario import EconomicScenario, ModelAssumptions

BASELINE = dict(year=0, adoption=0, employment=95, income=60, consumption=45,
                profit=15, balance=0, concentration=60, output=75,
                laborIncome=60, benefits=0, dividend=0, aiTax=0)
ORIGINAL_FIELDS = tuple(BASELINE)


def clamp(value, low, high):
    """Project a scalar onto a closed interval."""
    return min(high, max(low, value))


class ScenarioSimulator:
    """Compose validated scenario and assumptions; yield independent annual rows."""

    def __init__(self, scenario, assumptions=None, years=10):
        """Construct a simulator with a finite integer horizon of 1 to 100 years."""
        if not isinstance(scenario, EconomicScenario):
            raise ValueError("scenario must be EconomicScenario")
        if assumptions is not None and not isinstance(assumptions, ModelAssumptions):
            raise ValueError("assumptions must be ModelAssumptions")
        if type(years) is not int or not 1 <= years <= 100:
            raise ValueError("years must be an integer in [1, 100]")
        self.scenario = scenario
        self.assumptions = assumptions or ModelAssumptions()
        self.years = years

    def annual_records(self):
        """Yield year zero and annual results, including raw values and clip flags."""
        p, a = self.scenario, self.assumptions
        prev = dict(BASELINE, demand=1., raw_demand=1., raw_employment=95.,
                    raw_concentration=60., demand_clipped=False,
                    employment_clipped=False, concentration_clipped=False,
                    out_of_domain=False)
        yield prev.copy()
        for year in range(1, self.years + 1):
            adoption = clamp(prev['adoption'] + p.speed / 100 *
                             (1 - p.tax / 100 * a.tax_adoption_penalty) *
                             (1 - prev['adoption']), 0, 1)
            raw_demand = 1 + a.demand_strength * (prev['consumption'] / 45 - 1) if a.feedback else 1
            demand = clamp(raw_demand, .65, 1.4) if a.clipping else raw_demand
            output = 75 * demand * (1 + p.productivity / 100 * adoption)
            raw_employment = 95 * demand * (1 - p.substitution / 100 * adoption) / (1 + .55 * p.productivity / 100 * adoption)
            employment = clamp(raw_employment, 35, 99) if a.clipping else raw_employment
            labor = 60 * employment / 95 * (1 + .12 * p.productivity / 100 * adoption)
            benefits = max(0, 95 - employment) / 100 * 12
            pretax = max(0, output - labor - 4 * adoption)
            ai_tax = max(0, pretax - 15) * adoption * p.tax / 100
            profit = pretax - ai_tax
            dividend = max(0, profit - 15) * (1 - prev['concentration'] / 100) * .12 if a.dividend else 0
            transfer = p.ubi * 12 / 1000
            income = labor + benefits + transfer + dividend
            consumption = income * .75
            balance = (labor - 60) * .15 + ai_tax - benefits - transfer
            raw_concentration = prev['concentration'] + .08 * max(0, profit - 15) - .07 * (transfer + benefits) - .18 * ai_tax
            concentration = clamp(raw_concentration, 35, 90) if a.clipping else raw_concentration
            prev = dict(year=year, adoption=adoption, employment=employment,
                        income=income, consumption=consumption, profit=profit,
                        balance=balance, concentration=concentration, output=output,
                        laborIncome=labor, benefits=benefits, dividend=dividend, aiTax=ai_tax,
                        demand=demand, raw_demand=raw_demand, raw_employment=raw_employment,
                        raw_concentration=raw_concentration,
                        demand_clipped=demand != raw_demand,
                        employment_clipped=employment != raw_employment,
                        concentration_clipped=concentration != raw_concentration,
                        out_of_domain=not (.65 <= demand <= 1.4 and 35 <= employment <= 99 and 35 <= concentration <= 90))
            yield prev.copy()

    def run(self):
        """Collect annual records into a fresh dataframe."""
        return pd.DataFrame(self.annual_records())


if __name__ == "__main__":
    print(ScenarioSimulator(EconomicScenario()).run().to_string(index=False))
