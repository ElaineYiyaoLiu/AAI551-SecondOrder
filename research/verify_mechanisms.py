"""Independently reconstruct E2 summaries, contrasts, configs and trajectories."""
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator

ROOT = Path(__file__).resolve().parents[1]
SWITCHES = ('feedback', 'dividend', 'clipping', 'adoption_suppression')
FLOWS = ('output', 'laborIncome', 'income', 'consumption', 'profit', 'dividend', 'aiTax')


def verify_mechanisms(destination=None, write_report=True):
    """Fail on missing, changed or inconsistent E2 evidence; save a check report."""
    destination = Path(destination) if destination else ROOT / 'outputs/mechanisms'
    manifest = json.loads((destination / 'manifest.json').read_text())
    protocol = json.loads((ROOT / 'research/protocol.json').read_text())
    for name, expected in manifest['source_hashes'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Source hash mismatch: {name}')
    for name, expected in manifest['output_hashes'].items():
        if hashlib.sha256((destination / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Output hash mismatch: {name}')
    configs = manifest['configs']
    if len(configs) != 192 or len({config['run_id'] for config in configs}) != 192:
        raise ValueError('Expected 192 unique configurations')
    expected_keys = {(layer['name'], *values, policy['name'])
        for layer in protocol['economic_layers']
        for values in itertools.product((False, True), repeat=4)
        for policy in protocol['policies']}
    actual_keys = {(c['layer'], *(c[key] for key in SWITCHES), c['policy']) for c in configs}
    if actual_keys != expected_keys:
        raise ValueError('Missing or unexpected mechanism coverage')
    layers = {layer['name']: layer for layer in protocol['economic_layers']}
    policies = {policy['name']: policy for policy in protocol['policies']}
    for config in configs:
        expected_scenario = {key: value for key, value in layers[config['layer']].items() if key != 'name'}
        expected_scenario.update(policies[config['policy']])
        expected_assumptions = {key: config[key] for key in SWITCHES[:3]}
        expected_assumptions.update(demand_strength=protocol['e2']['demand_strength'],
            tax_adoption_penalty=protocol['e2']['penalty_when_on'] if config['adoption_suppression']
            else protocol['e2']['penalty_when_off'])
        if config['scenario'] != expected_scenario or config['assumptions'] != expected_assumptions or config['years'] != 10:
            raise ValueError('Configuration does not implement the frozen protocol')
    annual = pd.read_csv(destination / 'annual.csv.gz')
    summary = pd.read_csv(destination / 'summary.csv')
    contrasts = pd.read_csv(destination / 'contrasts.csv')
    if len(annual) != 2112 or len(summary) != 192 or len(contrasts) != 384:
        raise ValueError('Unexpected E2 output dimensions')
    run_ids = {config['run_id'] for config in configs}
    if set(annual.run_id) != run_ids or set(summary.run_id) != run_ids or summary.run_id.duplicated().any():
        raise ValueError('Run identity mismatch in output tables')
    traces = {key: group.reset_index(drop=True) for key, group in annual.groupby('run_id')}
    summaries = summary.set_index('run_id')
    independent = {}
    for config in configs:
        trace = traces[config['run_id']]
        if trace.year.tolist() != list(range(11)):
            raise ValueError('Missing, duplicated or reordered annual observations')
        replay = ScenarioSimulator(EconomicScenario(**config['scenario']),
            ModelAssumptions(**config['assumptions']), 10).run()
        pd.testing.assert_frame_equal(trace[list(replay.columns)], replay,
            check_dtype=False, rtol=1e-12, atol=1e-12)
        invalid_rows = ~np.isfinite(trace.select_dtypes(include='number')).all(axis=1)
        nonphysical_rows = (trace[list(FLOWS)] < 0).any(axis=1)
        if not np.array_equal(trace.invalid_numeric, invalid_rows) or not np.array_equal(trace.nonphysical, nonphysical_rows):
            raise ValueError('Incorrect numerical or nonphysical flags')
        reference_id = next(c['run_id'] for c in configs if c['layer'] == config['layer']
            and all(c[key] == config[key] for key in SWITCHES) and c['policy'] == 'no_policy')
        reference = traces[reference_id].iloc[1:]
        candidate = trace.iloc[1:]
        expected = {'mean_employment_delta': np.mean(candidate.employment.to_numpy() - reference.employment.to_numpy()),
            'mean_income_delta': np.mean(candidate.income.to_numpy() - reference.income.to_numpy()),
            'cumulative_incremental_deficit': -np.sum(candidate.balance.to_numpy() - reference.balance.to_numpy())}
        if candidate.invalid_numeric.any() or reference.invalid_numeric.any():
            expected = dict.fromkeys(expected, np.nan)
        independent[config['run_id']] = expected
        row = summaries.loc[config['run_id']]
        for key in ('layer', 'policy', 'pair_id', *SWITCHES):
            if row[key] != config[key]:
                raise ValueError('Incorrect summary identity or mechanism setting')
        for metric, value in expected.items():
            if candidate.invalid_numeric.any() or reference.invalid_numeric.any():
                if pd.notna(row[metric]):
                    raise ValueError('Invalid pair must have null summary metrics')
            else:
                np.testing.assert_allclose(row[metric], value, rtol=1e-12, atol=1e-10)
        invalid = bool(candidate.invalid_numeric.any() or reference.invalid_numeric.any())
        domain = bool(candidate.out_of_domain.any() or reference.out_of_domain.any())
        physical = bool(candidate.nonphysical.any() or reference.nonphysical.any())
        for field, value in {'invalid_numeric': invalid, 'out_of_domain': domain,
                'nonphysical': physical, 'ranking_eligible': not (invalid or domain or physical),
                'any_clipping': bool(candidate[['demand_clipped', 'employment_clipped',
                                              'concentration_clipped']].any().any())}.items():
            if row[field] != value:
                raise ValueError(f'Incorrect paired flag: {field}')
    by_id = {config['run_id']: config for config in configs}
    expected_contrast_keys = set()
    for switch in SWITCHES:
        for config in configs:
            if config[switch]:
                expected_contrast_keys.add((switch, config['run_id']))
    if set(zip(contrasts.mechanism, contrasts.run_on)) != expected_contrast_keys:
        raise ValueError('Contrast coverage mismatch')
    for contrast in contrasts.to_dict('records'):
        switch = contrast['mechanism']
        on, off = by_id[contrast['run_on']], by_id[contrast['run_off']]
        if not on[switch] or off[switch] or on['layer'] != off['layer'] or on['policy'] != off['policy']:
            raise ValueError('Invalid on/off contrast pairing')
        if any(on[key] != off[key] for key in SWITCHES if key != switch):
            raise ValueError('Contrast changed more than one mechanism')
        for key in ('layer', 'policy', *(key for key in SWITCHES if key != switch)):
            if contrast[key] != on[key]:
                raise ValueError('Contrast identity does not match its source run')
        for field in ('out_of_domain', 'nonphysical', 'invalid_numeric', 'ranking_eligible'):
            first, second = bool(summaries.loc[on['run_id'], field]), bool(summaries.loc[off['run_id'], field])
            expected_flag = first and second if field == 'ranking_eligible' else first or second
            if contrast[field] != expected_flag:
                raise ValueError(f'Incorrect contrast validity flag: {field}')
        for metric in independent[on['run_id']]:
            expected = independent[on['run_id']][metric] - independent[off['run_id']][metric]
            np.testing.assert_allclose(contrast[metric + '_on_minus_off'], expected,
                                       rtol=1e-12, atol=1e-10)
        if switch == 'adoption_suppression' and on['scenario']['tax'] == 0:
            pd.testing.assert_frame_equal(traces[on['run_id']].drop(columns='run_id'),
                                          traces[off['run_id']].drop(columns='run_id'))
    no_feedback_ubi = summary.loc[(~summary.feedback) & (summary.policy == 'ubi_500')]
    np.testing.assert_allclose(no_feedback_ubi.mean_employment_delta, 0, atol=1e-12)
    report = {'status': 'passed', 'verified_at': datetime.now(timezone.utc).isoformat(),
        'runs_replayed': 192, 'annual_rows_verified': 2112,
        'summaries_reconstructed': 192, 'contrasts_reconstructed': 384,
        'protocol_sha256': manifest['source_hashes']['research/protocol.json'],
        'manifest_sha256': hashlib.sha256((destination / 'manifest.json').read_bytes()).hexdigest(),
        'source_and_output_hashes': 'passed',
        'untaxed_adoption_suppression_invariance': 'passed',
        'no_feedback_ubi_employment_invariance': 'passed',
        'out_of_domain_runs': int(summary.out_of_domain.sum()),
        'nonphysical_runs': int(summary.nonphysical.sum()),
        'invalid_numeric_runs': int(summary.invalid_numeric.sum()),
        'ranking_eligible_runs': int(summary.ranking_eligible.sum())}
    if write_report:
        (destination / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(json.dumps(verify_mechanisms(), indent=2))
