"""Run frozen E2 mechanism ablations and retain every annual trajectory.

Run python -m research.run_mechanisms from the project root. Existing completed
results are protected from overwriting. Source and protocol hashes identify the
exact computation; verification is in research.verify_mechanisms.
"""
import gzip
import hashlib
import itertools
import json
import platform
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator

ROOT = Path(__file__).resolve().parents[1]
SWITCHES = ('feedback', 'dividend', 'clipping', 'adoption_suppression')
FLOW_FIELDS = ('output', 'laborIncome', 'income', 'consumption', 'profit', 'dividend', 'aiTax')
METRICS = ('mean_employment_delta', 'mean_income_delta', 'cumulative_incremental_deficit')
SOURCES = ('research/protocol.json', 'research/run_mechanisms.py',
           'research/verify_mechanisms.py', 'scenario.py', 'simulator.py')


def source_hashes():
    """Hash the exact inputs and implementation used in the run."""
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCES}


def mechanism_configs(protocol):
    """Resolve all frozen layer, switch and policy inputs in stable order."""
    if protocol['status'] != 'frozen' or protocol['version'] != '1.0':
        raise ValueError('E2 requires the reviewed version 1.0 protocol')
    configs = []
    for layer in protocol['economic_layers']:
        economy = {key: value for key, value in layer.items() if key != 'name'}
        for values in itertools.product(*(protocol['e2']['switches'][key] for key in SWITCHES)):
            switches = dict(zip(SWITCHES, values))
            pair_id = layer['name'] + '_' + ''.join(str(int(value)) for value in values)
            assumptions = ModelAssumptions(**{key: switches[key] for key in SWITCHES[:3]},
                demand_strength=protocol['e2']['demand_strength'],
                tax_adoption_penalty=protocol['e2']['penalty_when_on'] if values[3]
                else protocol['e2']['penalty_when_off'])
            for policy in protocol['policies']:
                scenario = EconomicScenario(**economy, **policy)
                configs.append({'run_id': f'{pair_id}_{policy["name"]}', 'pair_id': pair_id,
                    'layer': layer['name'], 'policy': policy['name'], **switches,
                    'scenario': asdict(scenario), 'assumptions': asdict(assumptions),
                    'years': protocol['horizon']['years']})
    if len(configs) != protocol['e2']['runs']:
        raise ValueError('E2 configuration count differs from frozen protocol')
    return configs


def summarize(frame, baseline, config):
    """Compute paired metrics while inheriting validity flags from both runs."""
    candidate = frame.loc[frame.year.between(1, config['years'])]
    reference = baseline.loc[baseline.year.between(1, config['years'])]
    invalid = bool(candidate.invalid_numeric.any() or reference.invalid_numeric.any())
    out_of_domain = bool(candidate.out_of_domain.any() or reference.out_of_domain.any())
    nonphysical = bool(candidate.nonphysical.any() or reference.nonphysical.any())
    result = {key: config[key] for key in ('run_id', 'pair_id', 'layer', 'policy', *SWITCHES)}
    result.update(invalid_numeric=invalid, out_of_domain=out_of_domain,
                  nonphysical=nonphysical, ranking_eligible=not (invalid or out_of_domain or nonphysical),
                  any_clipping=bool(candidate[['demand_clipped', 'employment_clipped',
                                               'concentration_clipped']].any().any()))
    result.update(dict.fromkeys(METRICS))
    if not invalid:
        result.update(mean_employment_delta=float((candidate.employment - reference.employment).mean()),
                      mean_income_delta=float((candidate.income - reference.income).mean()),
                      cumulative_incremental_deficit=float(-(candidate.balance - reference.balance).sum()))
    return result


def mechanism_contrasts(summary):
    """Compare paired policy effects with one mechanism switched on versus off."""
    records = []
    for switch in SWITCHES:
        keys = ['layer', 'policy', *(key for key in SWITCHES if key != switch)]
        merged = summary.loc[summary[switch]].merge(summary.loc[~summary[switch]],
                    on=keys, suffixes=('_on', '_off'), validate='one_to_one')
        for row in merged.to_dict('records'):
            record = {key: row[key] for key in keys}
            record.update(mechanism=switch, run_on=row['run_id_on'], run_off=row['run_id_off'],
                ranking_eligible=bool(row['ranking_eligible_on'] and row['ranking_eligible_off']),
                out_of_domain=bool(row['out_of_domain_on'] or row['out_of_domain_off']),
                nonphysical=bool(row['nonphysical_on'] or row['nonphysical_off']),
                invalid_numeric=bool(row['invalid_numeric_on'] or row['invalid_numeric_off']))
            for metric in METRICS:
                record[metric + '_on_minus_off'] = (None if record['invalid_numeric']
                    else row[metric + '_on'] - row[metric + '_off'])
            records.append(record)
    return pd.DataFrame(records)


def run_mechanisms(destination=None):
    """Write results atomically after the entire frozen experiment succeeds."""
    destination = Path(destination) if destination else ROOT / 'outputs/mechanisms'
    if destination.exists():
        raise FileExistsError(f'Results already exist: {destination}')
    hashes = source_hashes()
    protocol = json.loads((ROOT / 'research/protocol.json').read_text())
    configs = mechanism_configs(protocol)
    frames, summaries = {}, []
    for config in configs:
        frame = ScenarioSimulator(EconomicScenario(**config['scenario']),
            ModelAssumptions(**config['assumptions']), config['years']).run()
        frame['invalid_numeric'] = ~np.isfinite(frame.select_dtypes(include='number')).all(axis=1)
        frame['nonphysical'] = (frame[list(FLOW_FIELDS)] < 0).any(axis=1)
        frames[config['run_id']] = frame
    for config in configs:
        summaries.append(summarize(frames[config['run_id']],
            frames[config['pair_id'] + '_no_policy'], config))
    summary = pd.DataFrame(summaries)
    contrasts = mechanism_contrasts(summary)
    annual = pd.concat([frames[config['run_id']].assign(run_id=config['run_id'])
                        for config in configs], ignore_index=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='e2-staging-', dir=destination.parent) as directory:
        staging = Path(directory)
        # Fixed gzip timestamp makes compression reproducible.
        with gzip.GzipFile(filename=str(staging / 'annual.csv.gz'), mode='wb', mtime=0) as stream:
            stream.write(annual.to_csv(index=False).encode())
        summary.to_csv(staging / 'summary.csv', index=False)
        contrasts.to_csv(staging / 'contrasts.csv', index=False)
        if source_hashes() != hashes:
            raise RuntimeError('Source changed during the experiment')
        manifest = {'status': 'computed_pending_independent_verification',
            'computed_at': datetime.now(timezone.utc).isoformat(),
            'protocol_version': protocol['version'], 'source_hashes': hashes,
            'python': platform.python_version(), 'platform': platform.platform(),
            'numpy': np.__version__, 'pandas': pd.__version__,
            'runs': len(configs), 'annual_rows': len(annual), 'contrasts': len(contrasts),
            'configs': configs,
            'output_hashes': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in sorted(staging.iterdir())}}
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
        staging.rename(destination)
    return {'runs': len(configs), 'annual_rows': len(annual), 'contrasts': len(contrasts)}


if __name__ == '__main__':
    print(json.dumps(run_mechanisms(), indent=2))
