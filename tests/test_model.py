"""AAI551 numerical, mechanism, validation, and I/O regression checks.

Author: Elaine Liu, with AI development assistance.
"""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator, ORIGINAL_FIELDS
from analysis import compare_runs, crossing_brackets
from io_utils import load_scenarios, export_run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('case', json.loads((ROOT/'reference/expected.json').read_text()), ids=lambda c:c['name'])
def test_upstream_parity(case):
    """Compare every original field in every year against actual TypeScript output."""
    actual = ScenarioSimulator(EconomicScenario(**case['params'])).run()
    expected = pd.DataFrame(case['rows'])
    np.testing.assert_allclose(actual[list(ORIGINAL_FIELDS)], expected[list(ORIGINAL_FIELDS)], rtol=1e-12, atol=1e-12)


def test_one_year_hand_calculation():
    """At zero adoption, UBI $500/month adds 6k income and costs 6k/year."""
    frame = ScenarioSimulator(EconomicScenario(speed=0, ubi=500), years=1).run()
    assert frame.iloc[1].income == pytest.approx(66)
    assert frame.iloc[1].consumption == pytest.approx(49.5)
    assert frame.iloc[1].balance == pytest.approx(-6)
    assert frame.iloc[1].employment == 95


def test_ubi_employment_lag():
    """Transfer enters income immediately, employment responds from year two."""
    base = EconomicScenario()
    a = ModelAssumptions(dividend=False)
    delta = compare_runs(ScenarioSimulator(base,a).run(), ScenarioSimulator(replace(base,ubi=500),a).run())
    assert delta.employment.iloc[1] == 0
    assert delta.income.iloc[1] == pytest.approx(6)
    assert delta.employment.iloc[2] > 0


@pytest.mark.parametrize('kwargs', [{'tax':41},{'ubi':True},{'speed':float('nan')},{'productivity':-1}])
def test_invalid_parameters(kwargs):
    """Reject malformed numeric inputs before recurrence execution."""
    with pytest.raises(ValueError):
        EconomicScenario(**kwargs)


def test_json_errors_and_export(tmp_path):
    """Distinguish loading errors and verify CSV and metadata round trips."""
    with pytest.raises(FileNotFoundError):
        load_scenarios(tmp_path/'missing.json')
    bad = tmp_path/'bad.json'
    bad.write_text('{')
    with pytest.raises(ValueError, match='Invalid scenario JSON'):
        load_scenarios(bad)
    scenario = load_scenarios(ROOT/'data/scenarios.json')[0]
    sim = ScenarioSimulator(scenario)
    frame = sim.run()
    export_run(frame,sim,tmp_path/'result.csv')
    pd.testing.assert_frame_equal(pd.read_csv(tmp_path/'result.csv'),frame,check_dtype=False)
    assert json.loads((tmp_path/'result.config.json').read_text())['scenario'] == scenario.to_dict()


def test_crossings_and_year_alignment():
    """Handle no crossing, exact zeros, sign changes and invalid paired years."""
    assert crossing_brackets([0,1,2],[-1,0,1]) == [(1,1)]
    assert crossing_brackets([0,1],[-1,1]) == [(0,1)]
    assert crossing_brackets([0,1],[1,2]) == []
    frame = ScenarioSimulator(EconomicScenario()).run()
    with pytest.raises(ValueError):
        compare_runs(frame,frame.iloc[::-1])


def test_clipping_and_feedback_switch():
    """Trace actual clamps, and ensure feedback-off demand stays one."""
    p = EconomicScenario(ubi=2000,speed=0)
    clipped = ScenarioSimulator(p).run()
    raw = ScenarioSimulator(p,ModelAssumptions(clipping=False)).run()
    assert clipped.employment_clipped.any()
    assert not raw.employment_clipped.any()
    assert raw.out_of_domain.any()
    assert (ScenarioSimulator(p,ModelAssumptions(feedback=False)).run().demand == 1).all()
