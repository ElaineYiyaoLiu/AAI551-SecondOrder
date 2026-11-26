"""Execute frozen E3-E5 grids, boundary brackets and fiscal comparisons.

Author: Elaine Liu, with AI assistance. Run from the repository root with
python -m research.run_policy_grids. Completed outputs are never overwritten.
"""
import csv
import gzip
import hashlib
import itertools
import json
import platform
import subprocess
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator

ROOT = Path(__file__).resolve().parents[1]
FLOWS = ('output', 'laborIncome', 'income', 'consumption', 'profit', 'dividend', 'aiTax')
SOURCES = ('research/protocol.json', 'scenario.py', 'simulator.py',
           'research/run_policy_grids.py', 'research/verify_policy_grids.py',
           'research/analyze_policy_grids.py')
METRICS = ('mean_employment_delta', 'mean_income_delta', 'cumulative_incremental_deficit')


def digest(path):
    """Identify exact source or output bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    """Write strict JSON so nonfinite results cannot masquerade as evidence."""
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows):
    """Store records with a stable, explicit column order."""
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_node(protocol, layer, demand, penalty, prefix):
    """Resolve four policies and preserve raw annual fields and validity flags."""
    economy = {k: v for k, v in layer.items() if k != 'name'}
    assumptions = ModelAssumptions(**{k: protocol['e3'][k] for k in
        ('feedback', 'dividend', 'clipping')}, demand_strength=float(demand),
        tax_adoption_penalty=float(penalty))
    configs, traces = [], []
    for policy in protocol['policies']:
        scenario = EconomicScenario(**economy, **policy)
        config = dict(run_id=prefix + '_' + policy['name'], node_id=prefix,
            layer=layer['name'], policy=policy['name'], demand=float(demand),
            penalty=float(penalty), scenario=asdict(scenario),
            assumptions=asdict(assumptions), years=protocol['horizon']['years'])
        rows = list(ScenarioSimulator(scenario, assumptions, config['years']).annual_records())
        for row in rows:
            row['invalid_numeric'] = not all(np.isfinite(v) for v in row.values()
                if isinstance(v, (float, int)))
            row['nonphysical'] = any(row[k] < 0 for k in FLOWS)
            row['run_id'] = config['run_id']
        configs.append(config)
        traces.append(rows)
    summaries = []
    baseline = traces[0][1:]
    if configs[0]['policy'] != 'no_policy':
        raise ValueError('Frozen policy order must start with the baseline')
    for config, rows in zip(configs, traces):
        candidate = rows[1:]
        invalid = any(r['invalid_numeric'] for r in candidate + baseline)
        domain = any(r['out_of_domain'] for r in candidate + baseline)
        physical = any(r['nonphysical'] for r in candidate + baseline)
        summary = {k: config[k] for k in ('run_id', 'node_id', 'layer', 'policy', 'demand', 'penalty')}
        summary.update(invalid_numeric=invalid, out_of_domain=domain,
            nonphysical=physical, ranking_eligible=not (invalid or domain or physical),
            any_clipping=any(r[k] for r in candidate for k in
                ('demand_clipped', 'employment_clipped', 'concentration_clipped')))
        summary.update(dict.fromkeys(METRICS))
        if not invalid:
            summary.update(mean_employment_delta=sum(r['employment']-b['employment']
                for r, b in zip(candidate, baseline))/len(candidate),
                mean_income_delta=sum(r['income']-b['income']
                for r, b in zip(candidate, baseline))/len(candidate),
                cumulative_incremental_deficit=-sum(r['balance']-b['balance']
                for r, b in zip(candidate, baseline)))
        summaries.append(summary)
    return configs, traces, summaries


def winners(rows, tolerance, cap=None):
    """Keep all eligible feasible co-winners, including exact ties."""
    eligible = [r for r in rows if r['ranking_eligible'] and
        (cap is None or r['cumulative_incremental_deficit'] <= cap + 1e-9)]
    if not eligible:
        return []
    maximum = max(r['mean_employment_delta'] for r in eligible)
    return [r['policy'] for r in eligible if maximum-r['mean_employment_delta'] <= tolerance]


def classify(value, tolerance):
    """Classify a signed candidate-minus-reference policy difference."""
    return 1 if value > tolerance else -1 if value < -tolerance else 0


def refine_edge(evaluate, a, b, fa, fb, tolerance, width=1e-6, limit=30):
    """Bisect a strict sign bracket; retain ties, invalid points and unresolved cases."""
    iterations = 0
    if abs(fa) <= tolerance or abs(fb) <= tolerance:
        return a, b, fa, fb, iterations, 'sampled_tie'
    while b-a > width and iterations < limit:
        midpoint = (a+b)/2
        fm = evaluate(midpoint)
        iterations += 1
        if fm is None:
            return a, b, fa, fb, iterations, 'invalid_or_domain_disconnected'
        if abs(fm) <= tolerance:
            return midpoint, midpoint, fm, fm, iterations, 'sampled_tie'
        if fa*fm < 0:
            b, fb = midpoint, fm
        else:
            a, fa = midpoint, fm
    return a, b, fa, fb, iterations, 'width_tolerance' if b-a <= width else 'iteration_limit'


class EvidenceWriter:
    """Stream complete resolved configurations and traces without keeping them in RAM."""
    def __init__(self, directory):
        """Open compressed evidence streams in a fresh staging directory."""
        self.config_stream = gzip.open(directory/'configs.jsonl.gz', 'wt')
        self.annual_stream = gzip.open(directory/'annual.csv.gz', 'wt', newline='')
        self.writer = None
        self.runs = self.rows = 0

    def append(self, configs, traces):
        """Record each actual evaluated configuration once per evidence stream."""
        for config, rows in zip(configs, traces):
            self.config_stream.write(json.dumps(config, allow_nan=False)+'\n')
            if self.writer is None:
                self.writer = csv.DictWriter(self.annual_stream, fieldnames=list(rows[0]))
                self.writer.writeheader()
            self.writer.writerows(rows)
            self.runs += 1
            self.rows += len(rows)

    def close(self):
        """Flush evidence before computing file hashes."""
        self.config_stream.close()
        self.annual_stream.close()


def execute(destination=None):
    """Compute all frozen overdue stages atomically; verifier is a separate program."""
    destination = Path(destination) if destination else ROOT/'outputs/policy_grids'
    if destination.exists():
        raise FileExistsError(destination)
    protocol = json.loads((ROOT/'research/protocol.json').read_text())
    if protocol['status'] != 'frozen' or protocol['version'] != '1.0':
        raise ValueError('Reviewed protocol 1.0 required')
    hashes = {p: digest(ROOT/p) for p in SOURCES}
    tol = protocol['ranking']['absolute_tolerance_pp']
    policies = [p['name'] for p in protocol['policies']]
    pairs = list(itertools.combinations(range(4), 2))
    all_summaries, pairwise, node_rankings, boundaries, coverage, shared = [], [], [], [], [], []
    cache = {}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='grids-staging-', dir=destination.parent) as temporary:
        staging = Path(temporary)
        grid_writer = EvidenceWriter(staging)
        refinement_dir = staging/'refinement'
        refinement_dir.mkdir()
        refinement_writer = EvidenceWriter(refinement_dir)
        grids = {}
        for n in protocol['e4']['resolution_points']:
            ds = np.linspace(0, .84, n)
            ps = np.linspace(0, .9, n)
            for layer in protocol['economic_layers']:
                nodes = {}
                for i, d in enumerate(ds):
                    for j, p in enumerate(ps):
                        key = (layer['name'], round(float(d), 14), round(float(p), 14))
                        if key not in cache:
                            prefix = f'{layer["name"]}_n{n}_{i}_{j}'
                            configs, traces, summary = run_node(protocol, layer, d, p, prefix)
                            grid_writer.append(configs, traces)
                            cache[key] = summary
                        summary = cache[key]
                        nodes[i, j] = summary
                        all_summaries.extend(dict(r, resolution=n, i=i, j=j) for r in summary)
                        node_rankings.append(dict(resolution=n, layer=layer['name'], i=i, j=j,
                            demand=float(d), penalty=float(p), winners='|'.join(winners(summary, tol))))
                        for a, b in pairs:
                            eligible = summary[a]['ranking_eligible'] and summary[b]['ranking_eligible']
                            numeric = not (summary[a]['invalid_numeric'] or summary[b]['invalid_numeric'])
                            diff = summary[b]['mean_employment_delta']-summary[a]['mean_employment_delta'] if numeric else None
                            pairwise.append(dict(resolution=n, layer=layer['name'], i=i, j=j,
                                reference=policies[a], candidate=policies[b], difference=diff,
                                ranking_eligible=eligible, classification=classify(diff, tol) if eligible else None))
                grids[n, layer['name']] = nodes
                print(f'grid {n} {layer["name"]}: {len(nodes)*4} memberships', flush=True)
        grid_writer.close()
        # Adjacent nodes retain all sign-change and tie edges; no-crossing counts are explicit.
        refinement_cache = {}
        for (n, layer_name), nodes in grids.items():
            layer = next(l for l in protocol['economic_layers'] if l['name'] == layer_name)
            for a, b in pairs:
                counts = dict(strict_sign_change=0, sampled_tie=0, same_sign=0, ineligible=0)
                for axis in ('demand', 'penalty'):
                    for i in range(n):
                        for j in range(n):
                            end = (i+1,j) if axis == 'demand' else (i,j+1)
                            if end[0] >= n or end[1] >= n:
                                continue
                            first, second = nodes[i,j], nodes[end]
                            if not all(r['ranking_eligible'] for r in (first[a],first[b],second[a],second[b])):
                                counts['ineligible'] += 1
                                continue
                            fa = first[b]['mean_employment_delta']-first[a]['mean_employment_delta']
                            fb = second[b]['mean_employment_delta']-second[a]['mean_employment_delta']
                            ca, cb = classify(fa,tol), classify(fb,tol)
                            if ca == cb and ca != 0:
                                counts['same_sign'] += 1
                                continue
                            reason = 'sampled_tie' if ca == 0 or cb == 0 else 'strict_sign_change'
                            counts[reason] += 1
                            x0, x1 = first[0][axis], second[0][axis]
                            fixed_axis = 'penalty' if axis == 'demand' else 'demand'
                            fixed = first[0][fixed_axis]
                            def evaluate(x):
                                d, p = (x,fixed) if axis == 'demand' else (fixed,x)
                                key = (layer_name, float(d), float(p))
                                if key not in refinement_cache:
                                    configs, traces, rows = run_node(protocol, layer, d, p,
                                        f'refine_{len(refinement_cache)}_{layer_name}')
                                    refinement_writer.append(configs,traces)
                                    refinement_cache[key] = rows
                                rows = refinement_cache[key]
                                return rows[b]['mean_employment_delta']-rows[a]['mean_employment_delta'] if all(
                                    rows[k]['ranking_eligible'] for k in (a,b)) else None
                            left,right,fl,fr,iterations,termination = refine_edge(evaluate,x0,x1,fa,fb,tol)
                            boundaries.append(dict(resolution=n, layer=layer_name, reference=policies[a],
                                candidate=policies[b], axis=axis, fixed=fixed, original_left=x0,
                                original_right=x1, original_f_left=fa, original_f_right=fb,
                                left=left,right=right,f_left=fl,f_right=fr,iterations=iterations,
                                termination=termination))
                coverage.append(dict(resolution=n, layer=layer_name, reference=policies[a],
                    candidate=policies[b], **counts))
            print(f'boundaries {n} {layer_name}', flush=True)
        refinement_writer.close()
        # Compare signs and co-winners at every nested shared coordinate.
        for small, large in ((21,41),(41,81),(21,81)):
            factor=(large-1)//(small-1)
            for layer in protocol['economic_layers']:
                for (i,j), first in grids[small,layer['name']].items():
                    second=grids[large,layer['name']][i*factor,j*factor]
                    signs=lambda rows: [classify(rows[b]['mean_employment_delta']-rows[a]['mean_employment_delta'],tol)
                        if rows[a]['ranking_eligible'] and rows[b]['ranking_eligible'] else None for a,b in pairs]
                    shared.append(dict(small=small,large=large,layer=layer['name'],i=i,j=j,
                        signs_match=signs(first)==signs(second),winners_match=winners(first,tol)==winners(second,tol)))
        fiscal=[]
        for layer in protocol['economic_layers']:
            for (i,j), rows in grids[41,layer['name']].items():
                for cap in protocol['e5']['budget_caps_thousand_usd']:
                    best=winners(rows,tol,cap)
                    for row in rows:
                        fiscal.append(dict(layer=layer['name'],i=i,j=j,demand=row['demand'],penalty=row['penalty'],
                            policy=row['policy'],cap=cap,ranking_eligible=row['ranking_eligible'],
                            feasible=row['ranking_eligible'] and row['cumulative_incremental_deficit']<=cap+1e-9,
                            winner=row['policy'] in best, **{k:row[k] for k in METRICS}))
        for name, rows in [('summary',all_summaries),('pairwise',pairwise),('rankings',node_rankings),
                ('boundaries',boundaries),('edge_coverage',coverage),('shared_coordinates',shared),('fiscal',fiscal)]:
            write_csv(staging/(name+'.csv'),rows)
        if hashes != {p:digest(ROOT/p) for p in SOURCES}:
            raise RuntimeError('Source changed during computation')
        manifest=dict(status='computed_pending_independent_verification',
            computed_at=datetime.now(timezone.utc).isoformat(),protocol_version=protocol['version'],
            source_hashes=hashes,base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            python=platform.python_version(),platform=platform.platform(),numpy=np.__version__,pandas=pd.__version__,
            grid_unique_runs=grid_writer.runs,grid_annual_rows=grid_writer.rows,
            refinement_runs=refinement_writer.runs,refinement_annual_rows=refinement_writer.rows,
            e3_runs=protocol['e3']['runs'],e3_annual_rows=protocol['e3']['runs']*11,
            config_evidence='configs.jsonl.gz and refinement/configs.jsonl.gz contain complete resolved per-run inputs',
            nested_reuse='Shared grid coordinates reuse identical runs; summary.csv records every resolution membership.',
            output_hashes={str(p.relative_to(staging)):digest(p) for p in staging.rglob('*') if p.is_file()})
        write_json(staging/'manifest.json',manifest)
        staging.rename(destination)
    return {k:manifest[k] for k in ('grid_unique_runs','grid_annual_rows','refinement_runs','e3_runs')}


if __name__ == '__main__':
    print(json.dumps(execute(),indent=2))
