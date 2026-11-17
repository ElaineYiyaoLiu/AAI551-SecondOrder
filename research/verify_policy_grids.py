"""Independently audit E3-E5 saved traces, configurations and comparison tables.

Does not import runner summaries, ranking or refinement functions. Every grid
summary is reconstructed from annual evidence; selected model paths and every
reported boundary endpoint are replayed. Author: Elaine Liu, with AI assistance.
"""
import csv
import gzip
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator

ROOT=Path(__file__).resolve().parents[1]
FLOWS=('output','laborIncome','income','consumption','profit','dividend','aiTax')
METRICS=('mean_employment_delta','mean_income_delta','cumulative_incremental_deficit')


def check(condition, message):
    """Raise a durable validation failure even when Python assertions are disabled."""
    if not condition:
        raise ValueError(message)


def close(actual, expected):
    """Check serialized numeric evidence with stricter tolerance than plot precision."""
    np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-10,equal_nan=True)


def verify(destination=None):
    """Reconstruct all outputs and write passed status only after every check succeeds."""
    destination=Path(destination) if destination else ROOT/'outputs/policy_grids'
    manifest=json.loads((destination/'manifest.json').read_text())
    protocol=json.loads((ROOT/'research/protocol.json').read_text())
    for name,expected in manifest['source_hashes'].items():
        check(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,'Source hash: '+name)
    for name,expected in manifest['output_hashes'].items():
        check(hashlib.sha256((destination/name).read_bytes()).hexdigest()==expected,'Output hash: '+name)
    policies=[p['name'] for p in protocol['policies']]
    layers={l['name']:l for l in protocol['economic_layers']}
    policy_inputs={p['name']:p for p in protocol['policies']}
    tol=protocol['ranking']['absolute_tolerance_pp']
    reconstructed={}
    coordinates={}
    replays=0
    total_rows=0
    for directory in (destination,destination/'refinement'):
        with gzip.open(directory/'configs.jsonl.gz','rt') as stream:
            configs=[json.loads(line) for line in stream]
        ids=[c['run_id'] for c in configs]
        check(len(set(ids))==len(ids),'Duplicate run ids')
        reader=pd.read_csv(directory/'annual.csv.gz',chunksize=11000)
        cursor=0
        for chunk in reader:
            check(len(chunk)%11==0,'Incomplete annual block')
            for offset in range(0,len(chunk),44):
                block=chunk.iloc[offset:offset+44]
                node_configs=configs[cursor:cursor+4]
                check(len(node_configs)==4,'Missing four-policy config block')
                base=block.iloc[1:11]
                check(node_configs[0]['policy']=='no_policy','Wrong baseline')
                for k,config in enumerate(node_configs):
                    trace=block.iloc[k*11:(k+1)*11].reset_index(drop=True)
                    check(trace.run_id.tolist()==[config['run_id']]*11,'Run/trace ordering')
                    check(trace.year.tolist()==list(range(11)),'Annual coverage')
                    check(config['years']==10,'Horizon')
                    layer=layers[config['layer']]
                    expected={key:value for key,value in layer.items() if key!='name'}
                    expected.update(policy_inputs[config['policy']])
                    check(config['scenario']==expected,'Scenario differs from protocol')
                    check(config['assumptions']==dict(feedback=True,dividend=True,clipping=True,
                        demand_strength=config['demand'],tax_adoption_penalty=config['penalty']),
                        'Wrong resolved assumptions')
                    check(0<=config['demand']<=.84 and 0<=config['penalty']<=.9,'Outside frozen grid domain')
                    invalid=~np.isfinite(trace.select_dtypes(include='number')).all(axis=1)
                    nonphysical=(trace[list(FLOWS)]<0).any(axis=1)
                    domain=~(trace.demand.between(.65,1.4)&trace.employment.between(35,99)&trace.concentration.between(35,90))
                    check(np.array_equal(invalid,trace.invalid_numeric),'Incorrect nonfinite flags')
                    check(np.array_equal(nonphysical,trace.nonphysical),'Incorrect flow flags')
                    check(np.array_equal(domain,trace.out_of_domain),'Incorrect domain flags')
                    for field in ('demand','employment','concentration'):
                        check(np.array_equal(trace[field]!=trace['raw_'+field],trace[field+'_clipped']),
                            'Incorrect clamp flags')
                    current=trace.iloc[1:]
                    bad=bool(current.invalid_numeric.any() or base.invalid_numeric.any())
                    out=bool(current.out_of_domain.any() or base.out_of_domain.any())
                    phys=bool(current.nonphysical.any() or base.nonphysical.any())
                    values=[float(np.mean(current.employment.to_numpy()-base.employment.to_numpy())),
                        float(np.mean(current.income.to_numpy()-base.income.to_numpy())),
                        float(-np.sum(current.balance.to_numpy()-base.balance.to_numpy()))]
                    result=dict(zip(METRICS,values if not bad else [np.nan]*3))
                    result.update(invalid_numeric=bad,out_of_domain=out,nonphysical=phys,
                        ranking_eligible=not(bad or out or phys),any_clipping=bool(current[
                            ['demand_clipped','employment_clipped','concentration_clipped']].any().any()),
                        layer=config['layer'],policy=config['policy'],demand=config['demand'],penalty=config['penalty'],
                        node_id=config['node_id'])
                    reconstructed[config['run_id']]=result
                    if directory==destination:
                        coordinates[config['run_id']]=config
                        # Corners plus stratified deterministic sample, all four policies.
                        replay_required=(config['demand'] in (0,.84) and config['penalty'] in (0,.9)) or cursor%400==0
                    else:
                        replay_required=False
                    if replay_required:
                        replay=ScenarioSimulator(EconomicScenario(**config['scenario']),ModelAssumptions(**config['assumptions']),10).run()
                        pd.testing.assert_frame_equal(trace[list(replay.columns)],replay,check_dtype=False,rtol=1e-12,atol=1e-12)
                        replays+=1
                cursor+=4
                total_rows+=len(block)
        check(cursor==len(configs),'Missing trace evidence')
        expected_runs=manifest['grid_unique_runs' if directory==destination else 'refinement_runs']
        check(cursor==expected_runs,'Manifest run count')
        print(f'traces reconstructed: {directory.name}, {cursor} runs',flush=True)
    check(total_rows==manifest['grid_annual_rows']+manifest['refinement_annual_rows'],'Annual row total')
    summary=pd.read_csv(destination/'summary.csv')
    check(len(summary)==sum(n*n*12 for n in (21,41,81)),'Grid membership count')
    check(not summary.duplicated(['resolution','layer','i','j','policy']).any(),'Duplicate memberships')
    for row in summary.to_dict('records'):
        source=reconstructed[row['run_id']]
        for key in (*METRICS,'demand','penalty'):
            close(row[key],source[key])
        for key in ('invalid_numeric','out_of_domain','nonphysical','ranking_eligible','any_clipping','layer','policy','node_id'):
            check(row[key]==source[key],'Summary mismatch: '+key)
        config=coordinates[row['run_id']]
        close(row['demand'],row['i']*.84/(row['resolution']-1))
        close(row['penalty'],row['j']*.9/(row['resolution']-1))
        check(config['layer']==row['layer'] and config['policy']==row['policy'],'Membership identity')
    for n in (21,41,81):
        for layer in layers:
            subset=summary[(summary.resolution==n)&(summary.layer==layer)]
            check(len(subset)==n*n*4,'Resolution coverage')
            check(set(subset.policy)==set(policies),'Policy coverage')
    e3=summary[summary.resolution==41]
    check(len(e3)==20172 and len(e3)*11==221892,'E3 dimensions')
    def sign(value):
        return int(value>tol)-int(value < -tol)
    groups={key:group.set_index('policy') for key,group in summary.groupby(['resolution','layer','i','j'])}
    def best(group,cap=None):
        subset=group[group.ranking_eligible]
        if cap is not None:
            subset=subset[subset.cumulative_incremental_deficit<=cap+1e-9]
        return set(subset.index[subset.mean_employment_delta>=subset.mean_employment_delta.max()-tol])
    pairs=pd.read_csv(destination/'pairwise.csv')
    check(len(pairs)==len(groups)*6,'Pairwise count')
    check(not pairs.duplicated(['resolution','layer','i','j','reference','candidate']).any(),'Duplicate pair')
    for r in pairs.itertuples(index=False):
        g=groups[r.resolution,r.layer,r.i,r.j]
        a,b=g.loc[r.reference],g.loc[r.candidate]
        eligible=bool(a.ranking_eligible and b.ranking_eligible)
        close(r.difference,b.mean_employment_delta-a.mean_employment_delta)
        check(r.ranking_eligible==eligible,'Pair eligibility')
        check((r.classification==sign(r.difference)) if eligible else pd.isna(r.classification),'Pair sign')
    ranks=pd.read_csv(destination/'rankings.csv',keep_default_na=False)
    check(len(ranks)==len(groups) and not ranks.duplicated(['resolution','layer','i','j']).any(),'Ranking coverage')
    for r in ranks.itertuples(index=False):
        check(set(filter(None,r.winners.split('|')))==best(groups[r.resolution,r.layer,r.i,r.j]),'Lost co-winner')
    fiscal=pd.read_csv(destination/'fiscal.csv')
    check(len(fiscal)==20172*3,'Fiscal dimensions')
    check(not fiscal.duplicated(['layer','i','j','policy','cap']).any(),'Fiscal uniqueness')
    check(set(fiscal.cap)=={0,30,60},'Budget caps')
    fiscal_best={}
    for r in fiscal.itertuples(index=False):
        g=groups[41,r.layer,r.i,r.j]
        source=g.loc[r.policy]
        for metric in METRICS:
            close(getattr(r,metric),source[metric])
        feasible=bool(source.ranking_eligible and source.cumulative_incremental_deficit<=r.cap+1e-9)
        check(r.ranking_eligible==source.ranking_eligible and r.feasible==feasible,'Fiscal feasibility')
        key=(r.layer,r.i,r.j,r.cap)
        if key not in fiscal_best:
            fiscal_best[key]=best(g,r.cap)
        check(r.winner==(r.policy in fiscal_best[key]),'Fiscal co-winners')
    shared=pd.read_csv(destination/'shared_coordinates.csv')
    check(len(shared)==3*(21*21+41*41+21*21),'Shared-coordinate coverage')
    for r in shared.itertuples(index=False):
        factor=(r.large-1)//(r.small-1)
        a,b=groups[r.small,r.layer,r.i,r.j],groups[r.large,r.layer,r.i*factor,r.j*factor]
        close(a.loc[policies,list(METRICS)],b.loc[policies,list(METRICS)])
        check(r.signs_match and r.winners_match and best(a)==best(b),'Shared-node mismatch')
    # Reconstruct the complete adjacent-edge candidate inventory independently.
    expected_edges={}
    expected_counts={}
    for n in (21,41,81):
        for layer in layers:
            for a,b in itertools.combinations(policies,2):
                counts=dict(strict_sign_change=0,sampled_tie=0,same_sign=0,ineligible=0)
                for axis in ('demand','penalty'):
                    for i in range(n):
                        for j in range(n):
                            ii,jj=(i+1,j) if axis=='demand' else (i,j+1)
                            if ii>=n or jj>=n:
                                continue
                            ga,gb=groups[n,layer,i,j],groups[n,layer,ii,jj]
                            rows=(ga.loc[a],ga.loc[b],gb.loc[a],gb.loc[b])
                            if not all(r.ranking_eligible for r in rows):
                                counts['ineligible']+=1
                                continue
                            fa=rows[1].mean_employment_delta-rows[0].mean_employment_delta
                            fb=rows[3].mean_employment_delta-rows[2].mean_employment_delta
                            if sign(fa)==sign(fb) and sign(fa)!=0:
                                counts['same_sign']+=1
                                continue
                            reason='sampled_tie' if sign(fa)==0 or sign(fb)==0 else 'strict_sign_change'
                            counts[reason]+=1
                            fixed=float(ga.loc[a,'penalty' if axis=='demand' else 'demand'])
                            key=(n,layer,a,b,axis,round(fixed,12),round(float(ga.loc[a,axis]),12))
                            expected_edges[key]=(fa,fb)
                expected_counts[n,layer,a,b]=counts
    coverage=pd.read_csv(destination/'edge_coverage.csv')
    check(len(coverage)==54,'Edge coverage rows')
    for r in coverage.to_dict('records'):
        counts=expected_counts[r['resolution'],r['layer'],r['reference'],r['candidate']]
        check(all(r[k]==v for k,v in counts.items()),'Edge inventory counts')
    boundaries=pd.read_csv(destination/'boundaries.csv')
    check(len(boundaries)==len(expected_edges),'Missing/extra candidate edges')
    seen=set()
    endpoint_cache={}
    for r in boundaries.itertuples(index=False):
        key=(r.resolution,r.layer,r.reference,r.candidate,r.axis,round(r.fixed,12),round(r.original_left,12))
        check(key not in seen and key in expected_edges,'Duplicate/unexpected boundary')
        seen.add(key)
        close([r.original_f_left,r.original_f_right],expected_edges[key])
        check(r.original_left<=r.left<=r.right<=r.original_right,'Bracket escaped original edge')
        for x,fx in ((r.left,r.f_left),(r.right,r.f_right)):
            demand,penalty=(x,r.fixed) if r.axis=='demand' else (r.fixed,x)
            values=[]
            for policy in (r.reference,r.candidate):
                ck=(r.layer,policy,float(demand),float(penalty))
                if ck not in endpoint_cache:
                    inputs={k:v for k,v in layers[r.layer].items() if k!='name'}
                    inputs.update(policy_inputs[policy])
                    rows=list(ScenarioSimulator(EconomicScenario(**inputs),ModelAssumptions(
                        demand_strength=demand,tax_adoption_penalty=penalty),10).annual_records())[1:]
                    check(not any(y['out_of_domain'] or any(y[f]<0 for f in FLOWS) for y in rows),'Ineligible boundary endpoint')
                    endpoint_cache[ck]=np.mean([y['employment'] for y in rows])
                values.append(endpoint_cache[ck])
            close(fx,values[1]-values[0])
        check(0<=r.iterations<=30,'Bisection iteration count')
        if r.termination=='width_tolerance':
            check(r.right-r.left<=1e-6 and r.f_left*r.f_right<0,'Invalid terminal sign bracket')
        elif r.termination=='sampled_tie':
            check(min(abs(r.f_left),abs(r.f_right))<=tol,'Unjustified tie')
        elif r.termination=='iteration_limit':
            check(r.iterations==30,'Unjustified iteration limit')
        else:
            check(r.termination=='invalid_or_domain_disconnected','Unknown termination')
    report=dict(status='passed',verified_at=datetime.now(timezone.utc).isoformat(),
        source_and_output_hashes='passed',protocol_sha256=manifest['source_hashes']['research/protocol.json'],
        manifest_sha256=hashlib.sha256((destination/'manifest.json').read_bytes()).hexdigest(),
        grid_unique_runs=manifest['grid_unique_runs'],grid_summaries_reconstructed=len(summary),
        annual_rows_reconstructed=total_rows,e3_runs=20172,e3_annual_rows=221892,
        grid_model_replays=replays,boundary_endpoint_model_replays=len(endpoint_cache),
        pairwise_rows_verified=len(pairs),fiscal_rows_verified=len(fiscal),
        candidate_edges_verified=len(boundaries),shared_coordinates_verified=len(shared),
        e3_invalid_numeric_runs=int(e3.invalid_numeric.sum()),e3_out_of_domain_runs=int(e3.out_of_domain.sum()),
        e3_nonphysical_runs=int(e3.nonphysical.sum()),e3_clipped_runs=int(e3.any_clipping.sum()),
        unresolved_brackets=int(boundaries.termination.isin(['iteration_limit','invalid_or_domain_disconnected']).sum()))
    (destination/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
