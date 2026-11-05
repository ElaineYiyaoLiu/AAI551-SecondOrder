"""Save independently checked transfer responses and their source hashes."""
import hashlib
import json
from pathlib import Path
from dataclasses import asdict, replace
import numpy as np
import pandas as pd
from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator
from research.analytic_response import transfer_response

ROOT = Path(__file__).resolve().parents[1]


def run_checks():
    records, checks = [], []
    for layer in [(25, 30, 10), (10, 60, 20), (45, 40, 20)]:
        for feedback in [False, True]:
            for ubi in [0, 500]:
                policy = EconomicScenario(substitution=layer[0], productivity=layer[1], speed=layer[2], tax=20, ubi=ubi)
                assumptions = ModelAssumptions(dividend=False, clipping=False, feedback=feedback)
                analytic = pd.DataFrame(transfer_response(policy, assumptions))
                actual = ScenarioSimulator(policy, assumptions).run()
                changed = ScenarioSimulator(replace(policy, ubi=ubi + 1), assumptions).run()
                assert np.array_equal((actual.employment < 95).iloc[1:], (changed.employment < 95).iloc[1:])
                level_error, derivative_error = 0., 0.
                for field in ['income', 'employment', 'consumption']:
                    np.testing.assert_allclose(actual[field], analytic[field], rtol=1e-12, atol=1e-12)
                    observed = (changed[field] - actual[field]) / .012
                    np.testing.assert_allclose(observed, analytic[field + '_dT'], rtol=1e-9, atol=1e-9)
                    level_error = max(level_error, float((actual[field] - analytic[field]).abs().max()))
                    derivative_error = max(derivative_error, float((observed - analytic[field + '_dT']).abs().max()))
                run_id = f'analytic_{len(checks):02d}'
                records.append(analytic.assign(run_id=run_id, out_of_domain=actual.out_of_domain))
                checks.append(dict(run_id=run_id, scenario=policy.to_dict(), assumptions=asdict(assumptions), years=10,
                                   max_level_error=level_error, max_derivative_error=derivative_error,
                                   out_of_domain=bool(actual.out_of_domain.any())))
    sources = ['scenario.py', 'simulator.py', 'research/analytic_response.py',
               'research/run_analytic_checks.py', 'docs/analytic_response.md', 'tests/test_analytic_response.py']
    report = dict(status='passed', configurations=len(checks), annual_rows=sum(map(len, records)),
                  monthly_ubi_increment=1, annual_transfer_increment=.012,
                  level_tolerance=dict(rtol=1e-12, atol=1e-12),
                  derivative_tolerance=dict(rtol=1e-9, atol=1e-9),
                  source_hashes={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}, checks=checks)
    target = ROOT / 'outputs/analytic_response'
    target.mkdir(parents=True, exist_ok=True)
    pd.concat(records, ignore_index=True).to_csv(target / 'annual.csv', index=False)
    (target / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['status', 'configurations', 'annual_rows']}, indent=2))
    return report


if __name__ == '__main__':
    run_checks()
