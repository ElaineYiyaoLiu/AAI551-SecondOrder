"""Independent transfer-response calculation for the unclipped, no-dividend model.

Author: Elaine Liu, with AI assistance. Derivation: docs/analytic_response.md.
No simulator implementation is imported here.
"""
from scenario import EconomicScenario, ModelAssumptions


def transfer_response(scenario, assumptions, years=10):
    """Return levels and derivatives per annual thousand USD of constant transfer.

    Adoption and tax are held fixed between paired policies. Derivatives are
    local to a benefits branch; a reachable kink raises ValueError. They do not
    describe the full model with dividends or grouped clamps enabled.
    """
    if not isinstance(scenario, EconomicScenario) or not isinstance(assumptions, ModelAssumptions):
        raise ValueError('validated scenario and assumptions required')
    if assumptions.dividend or assumptions.clipping:
        raise ValueError('requires dividend=False and clipping=False')
    if type(years) is not int or not 1 <= years <= 100:
        raise ValueError('years must be an integer in [1, 100]')
    rate = scenario.speed / 100 * (1 - scenario.tax / 100 * assumptions.tax_adoption_penalty)
    gain = assumptions.demand_strength if assumptions.feedback else 0.
    transfer = scenario.ubi * 12 / 1000
    income, response = 60., 0.
    rows = [dict(year=0, adoption=0., employment=95., income=60., consumption=45.,
                 income_dT=0., employment_dT=0., consumption_dT=0., benefits_active=False)]
    for year in range(1, years + 1):
        adoption = 1 - (1 - rate) ** year
        employment_factor = 95 * (1 - scenario.substitution / 100 * adoption) / (1 + .55 * scenario.productivity / 100 * adoption)
        wage_factor = 60 / 95 * (1 + .12 * scenario.productivity / 100 * adoption)
        employment = employment_factor * (1 - gain + gain * income / 60)
        employment_response = employment_factor * gain * response / 60
        if abs(employment - 95) < 1e-10 and abs(employment_response) > 1e-12:
            raise ValueError(f'benefits kink at year {year}; use one-sided checks')
        active = employment < 95
        slope = wage_factor - .12 * active
        income = slope * employment + 11.4 * active + transfer
        response = 1 + slope * employment_response
        rows.append(dict(year=year, adoption=adoption, employment=employment,
                         income=income, consumption=.75 * income,
                         income_dT=response, employment_dT=employment_response,
                         consumption_dT=.75 * response, benefits_active=active))
    return rows
