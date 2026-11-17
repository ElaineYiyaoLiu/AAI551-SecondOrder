"""Rebuild E3-E5 report tables and figures from independently verified evidence.

Author: Elaine Liu, with AI assistance. No model simulation is used for plotting.
"""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def analyze(destination=None):
    """Create readable scientific figures while preserving all source rows."""
    destination=Path(destination) if destination else ROOT/'outputs/policy_grids'
    validation=json.loads((destination/'validation.json').read_text())
    if validation['status']!='passed':
        raise ValueError('Independent validation required before reporting')
    manifest=json.loads((destination/'manifest.json').read_text())
    if hashlib.sha256((destination/'manifest.json').read_bytes()).hexdigest()!=validation['manifest_sha256']:
        raise ValueError('Validation no longer describes this manifest')
    for name,expected in manifest['output_hashes'].items():
        if hashlib.sha256((destination/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Changed evidence: '+name)
    summary=pd.read_csv(destination/'summary.csv')
    e3=summary[summary.resolution==41]
    pairwise=pd.read_csv(destination/'pairwise.csv')
    fiscal=pd.read_csv(destination/'fiscal.csv')
    edges=pd.read_csv(destination/'edge_coverage.csv')
    boundaries=pd.read_csv(destination/'boundaries.csv')
    layers=['central','productivity_led','substitution_led']
    policies=['no_policy','ubi_500','tax_20','combined']
    colors=['#d1d5db','#1d7a8c','#e9a23b','#8753a1']
    rankings=pd.read_csv(destination/'rankings.csv',keep_default_na=False)
    fig,axes=plt.subplots(1,3,figsize=(12,3.7),layout='constrained')
    cmap=ListedColormap(colors+['#202b3a'])
    for ax,layer in zip(axes,layers):
        subset=rankings[(rankings.resolution==41)&(rankings.layer==layer)].copy()
        subset['code']=subset.winners.map(lambda x:policies.index(x) if x in policies else 4)
        grid=subset.pivot(index='i',columns='j',values='code').to_numpy()
        ax.imshow(grid,origin='lower',extent=(0,.9,0,.84),aspect='auto',cmap=cmap,
            norm=BoundaryNorm(np.arange(-.5,5.5),5),interpolation='nearest')
        ax.set(title=layer.replace('_',' ').title(),xlabel='Tax adoption penalty',ylabel='Demand feedback strength')
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=c,label=p.replace('_',' ')) for c,p in zip(colors+['#202b3a'],policies+['co-winners'])],
        loc='outside lower center',ncol=5,frameon=False)
    fig.savefig(destination/'policy_rankings.png',dpi=180)
    plt.close(fig)
    # Pairwise maps make reversals visible even when the same policy wins overall.
    fig,axes=plt.subplots(1,3,figsize=(12,3.6),layout='constrained')
    for ax,layer in zip(axes,layers):
        rows=pairwise[(pairwise.resolution==41)&(pairwise.layer==layer)&
            (pairwise.reference=='ubi_500')&(pairwise.candidate=='tax_20')]
        grid=rows.pivot(index='i',columns='j',values='difference').to_numpy()
        vmax=max(abs(grid.min()),abs(grid.max()))
        im=ax.imshow(grid,origin='lower',extent=(0,.9,0,.84),aspect='auto',cmap='RdBu',vmin=-vmax,vmax=vmax)
        if grid.min()<0<grid.max():
            ax.contour(np.linspace(0,.9,41),np.linspace(0,.84,41),grid,levels=[0],colors='black',linewidths=.8)
        ax.set(title=layer.replace('_',' ').title(),xlabel='Tax adoption penalty',ylabel='Demand feedback strength')
        fig.colorbar(im,ax=ax,label='Tax minus UBI employment (pp)',shrink=.85)
    fig.savefig(destination/'pairwise_reversals.png',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,3.7),layout='constrained')
    for ax,layer in zip(axes,layers):
        rows=e3[e3.layer==layer]
        for policy,color in zip(policies,colors):
            r=rows[rows.policy==policy]
            ax.scatter(r.cumulative_incremental_deficit,r.mean_employment_delta,s=4,alpha=.3,color=color,label=policy.replace('_',' '),rasterized=True)
        for cap in (0,30,60):
            ax.axvline(cap,color='#808080',linewidth=.6,linestyle='--')
        ax.set(title=layer.replace('_',' ').title(),xlabel='Cumulative incremental deficit ($1,000)',ylabel='Mean employment gain (pp)')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=4,frameon=False)
    fig.savefig(destination/'fiscal_tradeoffs.png',dpi=180)
    plt.close(fig)
    counts=pairwise.groupby(['resolution','layer','reference','candidate','classification'],dropna=False).size().rename('nodes').reset_index()
    counts.to_csv(destination/'pairwise_counts.csv',index=False)
    fiscal_counts=fiscal.groupby(['layer','cap','policy'])[['feasible','winner']].sum().reset_index()
    fiscal_counts.to_csv(destination/'fiscal_counts.csv',index=False)
    ranking_counts=rankings.groupby(['resolution','layer','winners']).size().rename('nodes').reset_index()
    ranking_counts.to_csv(destination/'ranking_counts.csv',index=False)
    report=['# E3-E5 policy grids, boundaries and fiscal constraints','',
        'The frozen protocol 1.0 was executed without changing its policy inputs, grid ranges, ranking tolerance or budgets. Independent validation passed. These are deterministic artificial stress tests; node counts describe these grids, not real-world probabilities.','',
        '## E3: policy comparisons','',
        'The 41 by 41 grids contain 20,172 runs and 221,892 annual observations across three economic layers and four policies. All six policy pairs and all co-winners are retained.','',
        f'Invalid numeric runs: {validation["e3_invalid_numeric_runs"]}; out-of-domain paired runs: {validation["e3_out_of_domain_runs"]}; nonphysical paired runs: {validation["e3_nonphysical_runs"]}; runs with any clamp: {validation["e3_clipped_runs"]}.','',
        '| Layer | Policy | Minimum employment gain (pp) | Maximum employment gain (pp) |','| --- | --- | ---: | ---: |']
    for (layer,policy),rows in e3.groupby(['layer','policy'],sort=False):
        report.append(f'| {layer} | {policy} | {rows.mean_employment_delta.min():.6f} | {rows.mean_employment_delta.max():.6f} |')
    report+=['','![Employment co-winners](../outputs/policy_grids/policy_rankings.png)','',
        '![Tax versus UBI differences](../outputs/policy_grids/pairwise_reversals.png)','',
        '## E4: sampled boundaries and resolution checks','',
        f'The nested 21, 41 and 81 grids use {manifest["grid_unique_runs"]:,} unique configurations. Shared coordinates reuse identical evaluations; their comparison checks membership and classification consistency, not an independent convergence proof. All {validation["shared_coordinates_verified"]:,} shared-coordinate checks agree.','',
        '| Resolution | Strict sign-change edges | Edges touching sampled ties | Same-sign edges | Ineligible edges |',
        '| ---: | ---: | ---: | ---: | ---: |']
    for n,rows in edges.groupby('resolution'):
        totals=rows[['strict_sign_change','sampled_tie','same_sign','ineligible']].sum()
        report.append(f'| {n} | '+' | '.join(str(int(x)) for x in totals)+' |')
    report+=['',f'Every candidate edge is saved in boundaries.csv; {validation["unresolved_brackets"]} brackets remain unresolved. Strict brackets are bisected to width at most 1e-6 or 30 iterations. Sampled ties are points or tie-touching edges, not proofs of unique roots. Same-sign edge counts retain no-crossing cases. These scans do not certify the continuous parameter domain.','',
        '## E5: fiscal feasibility','',
        'Cumulative incremental deficit is the negative sum of candidate-minus-baseline annual balances over years 1-10. Negative values mean incremental savings. At each E3 node, all eligible policies meeting each 0, 30 or 60 thousand-dollar cap are compared by mean employment gain; ties remain co-winners. Dominated and infeasible policies remain in fiscal.csv.','',
        '| Layer | Cap ($1,000) | Policy | Feasible nodes | Co-winner nodes |',
        '| --- | ---: | --- | ---: | ---: |']
    for r in fiscal_counts.itertuples(index=False):
        report.append(f'| {r.layer} | {r.cap} | {r.policy} | {r.feasible} | {r.winner} |')
    report+=['','![Employment and fiscal tradeoffs](../outputs/policy_grids/fiscal_tradeoffs.png)','',
        '## Reproduction and evidence','',
        'Run `python -m research.verify_policy_grids` to independently reconstruct every grid summary from saved annual traces, check hashes and inputs, replay selected grid paths and all reported boundary endpoints, enumerate all candidate edges, and verify paired signs, ties and budget winners. Run `python -m research.analyze_policy_grids` to rebuild these figures and count tables. To recompute, preserve or move outputs/policy_grids first and run `python -m research.run_policy_grids`; existing results are protected.','',
        'The manifest hashes the frozen protocol, model, runner, verifier, analysis source and evidence files. Complete resolved inputs are in configs.jsonl.gz; refinement evaluations have separate configuration and annual streams. summary.csv contains all three resolution memberships. The numerical validation does not constitute Windows/macOS installation acceptance or a completed paper.','']
    (ROOT/'docs/e3_e5_results.md').write_text('\n'.join(report))
    analysis_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()
        if p.suffix=='.png' or p.name.endswith('_counts.csv')}
    (destination/'analysis_hashes.json').write_text(json.dumps(analysis_hashes,indent=2)+'\n')
    return {'report':'docs/e3_e5_results.md','figures':3,'count_tables':3}


if __name__=='__main__':
    print(json.dumps(analyze(),indent=2))
