"""Checks for annual ordering and retained boundary diagnostics."""
import pytest
from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator


def test_prior_consumption_and_concentration():
    frame = ScenarioSimulator(EconomicScenario(ubi=500, tax=20)).run()
    for previous, current in zip(frame.to_dict('records'), frame.iloc[1:].to_dict('records')):
        assert current['raw_demand'] == pytest.approx(1 + .42 * (previous['consumption'] / 45 - 1))
        assert current['dividend'] == pytest.approx(max(0, current['profit'] - 15) * (1 - previous['concentration'] / 100) * .12)
    assert frame.dividend.iloc[1] > 0
    assert frame.concentration.iloc[1] != frame.concentration.iloc[0]


def test_lower_demand_bound_retains_raw_value():
    policy = EconomicScenario(substitution=60, productivity=100, speed=25)
    frame = ScenarioSimulator(policy, ModelAssumptions(demand_strength=.84)).run()
    clipped = frame[frame.demand_clipped]
    assert not clipped.empty
    assert (clipped.raw_demand < .65).all()
    assert (clipped.demand == .65).all()
    assert (frame.employment >= 35).all()
    raw = ScenarioSimulator(policy, ModelAssumptions(demand_strength=.84, clipping=False)).run()
    assert raw.out_of_domain.any()
    assert not raw[['demand_clipped', 'employment_clipped', 'concentration_clipped']].any().any()


@pytest.mark.parametrize('years', [True, 0, 101, 1.5])
def test_invalid_horizon(years):
    with pytest.raises(ValueError, match='years'):
        ScenarioSimulator(EconomicScenario(), years=years)
