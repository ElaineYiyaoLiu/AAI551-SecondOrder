"""AAI551 exploratory 100-run pipeline pilot, not a frozen main experiment.

Author: Elaine Liu, with AI development assistance. Run from project root.
"""
import hashlib
import json
import platform
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pandas as pd
from scenario import ModelAssumptions
from simulator import ScenarioSimulator
from io_utils import load_scenarios


def run_pilot():
    """Save all annual records, paired summaries, configuration, and source hashes."""
    root = Path(__file__).resolve().parents[1]
    dest = root/'outputs/pilot'
    dest.mkdir(parents=True, exist_ok=True)
    policies = load_scenarios(root/'data/scenarios.json')
    records, summaries, configs = [], [], []
    for demand in np.linspace(0,.84,5):
        for penalty in np.linspace(0,.9,5):
            assumptions = ModelAssumptions(demand_strength=float(demand),tax_adoption_penalty=float(penalty))
            frames = [ScenarioSimulator(p,assumptions).run() for p in policies]
            for policy, frame in zip(policies,frames):
                run_id = f"run_{len(configs):03d}"
                configs.append(dict(run_id=run_id,scenario=policy.to_dict(),assumptions=asdict(assumptions)))
                records.append(frame.assign(run_id=run_id,policy=policy.name,demand_strength=demand,tax_adoption_penalty=penalty))
                summaries.append(dict(run_id=run_id,policy=policy.name,demand_strength=demand,tax_adoption_penalty=penalty,
                    mean_employment_delta=float((frame.employment.iloc[1:]-frames[0].employment.iloc[1:]).mean()),
                    mean_income_delta=float((frame.income.iloc[1:]-frames[0].income.iloc[1:]).mean()),
                    cumulative_incremental_deficit=float(-(frame.balance.iloc[1:]-frames[0].balance.iloc[1:]).sum()),
                    any_clipping=bool(frame[['demand_clipped','employment_clipped','concentration_clipped']].any().any()),
                    out_of_domain=bool(frame.out_of_domain.any())))
    pd.concat(records,ignore_index=True).to_csv(dest/'annual.csv',index=False)
    summary = pd.DataFrame(summaries)
    summary.to_csv(dest/'summary.csv',index=False)
    paths = ['scenario.py','simulator.py','analysis.py','io_utils.py','research/run_pilot.py','data/scenarios.json','reference/model.ts']
    manifest = dict(status='exploratory_pilot_not_main_results',python=platform.python_version(),
                    runs=len(configs),annual_rows=sum(len(f) for f in records),
                    source_hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},configs=configs)
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(summary.groupby('policy')[['mean_employment_delta','mean_income_delta','cumulative_incremental_deficit']].agg(['min','max']).to_string())
    return summary


if __name__ == '__main__':
    run_pilot()
