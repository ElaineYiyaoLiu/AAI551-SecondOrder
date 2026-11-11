"""Check frozen ablation coverage, fiscal signs and paired validity handling."""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.run_mechanisms import (SWITCHES, mechanism_configs,
    mechanism_contrasts, run_mechanisms, summarize)

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_config_coverage():
    protocol = json.loads((ROOT / 'research/protocol.json').read_text())
    configs = mechanism_configs(protocol)
    assert len(configs) == len({config['run_id'] for config in configs}) == 192
    for layer in protocol['economic_layers']:
        for switches in itertools.product((False, True), repeat=4):
            group = [c for c in configs if c['layer'] == layer['name']
                     and tuple(c[key] for key in SWITCHES) == switches]
            assert {c['policy'] for c in group} == {'no_policy', 'ubi_500', 'tax_20', 'combined'}
            for config in group:
                assert config['assumptions']['tax_adoption_penalty'] == (.45 if switches[-1] else 0)
    protocol['status'] = 'draft'
    with pytest.raises(ValueError, match='reviewed'):
        mechanism_configs(protocol)


def sample_pair():
    reference = pd.DataFrame({'year': [0, 1, 2], 'employment': [95., 40., 40.],
        'income': [60., 30., 30.], 'balance': [0., -3., -4.],
        'out_of_domain': [False, False, True], 'nonphysical': False,
        'invalid_numeric': False, 'demand_clipped': False,
        'employment_clipped': False, 'concentration_clipped': False})
    candidate = reference.copy()
    candidate['employment'] = [999., 50., 60.]
    candidate['income'] = [999., 34., 36.]
    candidate['balance'] = [999., -1., -2.]
    candidate['out_of_domain'] = False
    config = dict(run_id='candidate', pair_id='pair', layer='test', policy='ubi_500',
                  years=2, **dict.fromkeys(SWITCHES, True))
    return candidate, reference, config


def test_paired_metrics_exclude_initial_year_and_keep_domain_flags():
    candidate, reference, config = sample_pair()
    result = summarize(candidate, reference, config)
    assert result['mean_employment_delta'] == 15
    assert result['mean_income_delta'] == 5
    assert result['cumulative_incremental_deficit'] == -4
    assert result['out_of_domain'] and not result['ranking_eligible']


def test_nonfinite_pair_has_null_metrics():
    candidate, reference, config = sample_pair()
    candidate.loc[1, 'invalid_numeric'] = True
    candidate.loc[1, 'employment'] = np.nan
    result = summarize(candidate, reference, config)
    assert result['invalid_numeric'] and not result['ranking_eligible']
    assert result['mean_employment_delta'] is None
    assert result['cumulative_incremental_deficit'] is None


def test_contrasts_hold_other_switches_fixed_and_keep_interactions():
    records = []
    for values in itertools.product((False, True), repeat=4):
        switches = dict(zip(SWITCHES, values))
        effect = 2 * switches['feedback'] + 3 * switches['dividend'] + 5 * switches['feedback'] * switches['dividend']
        records.append(dict(run_id=str(values), layer='test', policy='ubi_500', **switches,
            mean_employment_delta=effect, mean_income_delta=effect,
            cumulative_incremental_deficit=-effect, ranking_eligible=True,
            out_of_domain=False, nonphysical=False, invalid_numeric=False))
    contrasts = mechanism_contrasts(pd.DataFrame(records))
    assert len(contrasts) == 32
    feedback = contrasts.loc[contrasts.mechanism == 'feedback']
    np.testing.assert_allclose(feedback.mean_employment_delta_on_minus_off,
                               2 + 5 * feedback.dividend.astype(int))
    suppression = contrasts.loc[contrasts.mechanism == 'adoption_suppression']
    assert (suppression.mean_employment_delta_on_minus_off == 0).all()


def test_existing_experiment_is_protected(tmp_path):
    (tmp_path / 'existing.txt').write_text('preserve')
    with pytest.raises(FileExistsError):
        run_mechanisms(tmp_path)
    assert (tmp_path / 'existing.txt').read_text() == 'preserve'
