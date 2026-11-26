"""Regression checks for ties, fiscal signs and boundary stopping behavior."""
import json
from pathlib import Path

import pytest

from research.run_policy_grids import classify, refine_edge, run_node, winners


def test_policy_ties_budget_and_invalid_exclusion():
    """Negative deficits are savings; co-winners survive, ineligible rows do not."""
    rows=[dict(policy='baseline',ranking_eligible=True,mean_employment_delta=0,cumulative_incremental_deficit=0),
          dict(policy='saving',ranking_eligible=True,mean_employment_delta=2,cumulative_incremental_deficit=-3),
          dict(policy='tie',ranking_eligible=True,mean_employment_delta=2+5e-10,cumulative_incremental_deficit=30),
          dict(policy='invalid',ranking_eligible=False,mean_employment_delta=100,cumulative_incremental_deficit=-10)]
    assert winners(rows,1e-9,0)==['saving']
    assert winners(rows,1e-9,30)==['saving','tie']
    assert classify(1e-9,1e-9)==0
    assert classify(-2e-9,1e-9)==-1


def test_strict_boundary_bracket_and_invalid_midpoint():
    """An off-grid root remains bracketed; invalid midpoint stops refinement."""
    result=refine_edge(lambda x:x-.314159,0,1,-.314159,.685841,1e-9)
    left,right,fl,fr,steps,reason=result
    assert left<=.314159<=right and right-left<=1e-6
    assert fl<0<fr and steps<=30 and reason=='width_tolerance'
    assert refine_edge(lambda x:None,0,1,-1,1,1e-9)[-1]=='invalid_or_domain_disconnected'
    assert refine_edge(lambda x:x,0,1,0,1,1e-9)[-1]=='sampled_tie'


def test_zero_feedback_policy_tie_and_fiscal_accounting():
    """UBI employment neutrality at zero feedback retains its fiscal cost."""
    protocol=json.loads((Path(__file__).resolve().parents[1]/'research/protocol.json').read_text())
    configs,traces,rows=run_node(protocol,protocol['economic_layers'][0],0,0,'test')
    assert rows[1]['mean_employment_delta']==pytest.approx(0,abs=1e-12)
    assert rows[1]['cumulative_incremental_deficit']==pytest.approx(60,abs=1e-10)
    assert set(winners(rows,1e-9))=={'no_policy','ubi_500','tax_20','combined'}
    assert set(winners(rows,1e-9,0))=={'no_policy','tax_20'}
    assert len(configs)==4 and all(len(trace)==11 for trace in traces)


def test_evidence_restoration_and_tamper_rejection(tmp_path):
    """A missing file restores exactly; altered pieces fail before publication."""
    import hashlib
    from research.restore_grid_evidence import restore
    content=b'complete annual evidence\n'
    part=tmp_path/'part';part.write_bytes(content)
    recipe={'annual.csv':{'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest(),
        'parts':[{'path':'part','sha256':hashlib.sha256(content).hexdigest()}]}}
    (tmp_path/'evidence_parts.json').write_text(json.dumps(recipe))
    assert restore(tmp_path)==['annual.csv']
    assert (tmp_path/'annual.csv').read_bytes()==content
    assert restore(tmp_path)==[]
    (tmp_path/'annual.csv').unlink()
    part.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Changed evidence part'):
        restore(tmp_path)
    assert not (tmp_path/'annual.csv').exists()
