"""Independent levels, transfer derivatives, branches and one-year lag checks."""
from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator
from research.analytic_response import transfer_response


@pytest.mark.parametrize('layer', [(25, 30, 10), (10, 60, 20), (45, 40, 20)])
@pytest.mark.parametrize('feedback', [False, True])
@pytest.mark.parametrize('ubi', [0, 500])
def test_independent_levels_and_local_response(layer, feedback, ubi):
    policy = EconomicScenario(substitution=layer[0], productivity=layer[1], speed=layer[2], ubi=ubi, tax=20)
    assumptions = ModelAssumptions(dividend=False, clipping=False, feedback=feedback)
    analytic = pd.DataFrame(transfer_response(policy, assumptions))
    simulation = ScenarioSimulator(policy, assumptions).run()
    np.testing.assert_allclose(analytic[['employment', 'income', 'consumption', 'adoption']],
                               simulation[['employment', 'income', 'consumption', 'adoption']], rtol=1e-12, atol=1e-12)
    # A one-dollar monthly change is .012 annual thousand USD.
    changed = ScenarioSimulator(replace(policy, ubi=ubi + 1), assumptions).run()
    assert np.array_equal((simulation.employment < 95).iloc[1:], (changed.employment < 95).iloc[1:])
    for field in ('income', 'employment', 'consumption'):
        np.testing.assert_allclose((changed[field] - simulation[field]) / .012,
                                   analytic[field + '_dT'], rtol=1e-9, atol=1e-9)
    assert analytic.income_dT.iloc[1] == 1
    assert analytic.consumption_dT.iloc[1] == .75
    assert analytic.employment_dT.iloc[1] == 0
    assert (analytic.employment_dT.iloc[2] > 0) == feedback


def test_closed_product_solution_and_benefits_branches():
    # Large transfer reaches the zero-benefits branch. The local response remains
    # valid on each branch, but finite policy jumps need not share these slopes.
    policy = EconomicScenario(ubi=2000)
    assumptions = ModelAssumptions(dividend=False, clipping=False)
    rows = transfer_response(policy, assumptions)
    assert {r['benefits_active'] for r in rows[1:]} == {False, True}
    multipliers = []
    for row in rows[1:]:
        a = row['adoption']
        k = 95 * (1 - .25 * a) / (1 + .55 * .30 * a)
        w = 60 / 95 * (1 + .12 * .30 * a)
        multipliers.append(.42 / 60 * k * (w - .12 * row['benefits_active']))
        t = row['year']
        closed = sum(np.prod(multipliers[j:t]) for j in range(1, t + 1))
        assert row['income_dT'] == pytest.approx(closed)


def test_feedback_off_and_kink():
    assumptions = ModelAssumptions(dividend=False, clipping=False)
    with pytest.raises(ValueError, match='kink'):
        transfer_response(EconomicScenario(speed=0), assumptions)
    rows = transfer_response(EconomicScenario(speed=0), replace(assumptions, feedback=False))
    assert all(row['employment_dT'] == 0 for row in rows)


@pytest.mark.parametrize('assumptions', [ModelAssumptions(), ModelAssumptions(dividend=False), ModelAssumptions(clipping=False)])
def test_reject_full_model_controls(assumptions):
    with pytest.raises(ValueError, match='dividend=False and clipping=False'):
        transfer_response(EconomicScenario(), assumptions)
