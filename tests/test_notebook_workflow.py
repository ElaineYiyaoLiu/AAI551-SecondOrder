"""Exercise notebook code and exports without claiming Jupyter kernel coverage."""
import json
from pathlib import Path
from dataclasses import asdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
import pytest

from io_utils import load_scenarios, export_run
from scenario import EconomicScenario, ModelAssumptions
from simulator import ScenarioSimulator

ROOT = Path(__file__).resolve().parents[1]


def test_notebook_code_and_artifacts(tmp_path, monkeypatch):
    """Run all six code cells with fresh inputs and inspect exported artifacts."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/scenarios.json').write_bytes((ROOT / 'data/scenarios.json').read_bytes())
    notebook = json.loads((ROOT / 'main.ipynb').read_text(encoding='utf-8'))
    namespace = {'__name__': '__main__'}
    cells = [cell for cell in notebook['cells'] if cell['cell_type'] == 'code']
    assert len(cells) == 6
    try:
        for index, cell in enumerate(cells):
            exec(compile(''.join(cell['source']), f'notebook-cell-{index}', 'exec'), namespace)
        metadata = json.loads(Path('outputs/ubi_500.config.json').read_text(encoding='utf-8'))
        simulator = ScenarioSimulator(EconomicScenario(**metadata['scenario']),
                                      ModelAssumptions(**metadata['assumptions']), metadata['years'])
        pd.testing.assert_frame_equal(pd.read_csv('outputs/ubi_500.csv'), simulator.run(), check_dtype=False)
        assert metadata['schema_version'] == 1
        assert 'thousand USD' in metadata['units']
        figure = namespace['fig']
        assert len(figure.axes) == 2
        for axis in figure.axes:
            assert len(axis.lines) == 4
            assert len(axis.get_legend().texts) == 4
        with Image.open('outputs/policy_comparison.png') as image:
            assert image.width == 1540 and image.height == 560
            image.verify()
    finally:
        plt.close('all')


def test_custom_json_and_nondefault_sidecar(tmp_path):
    """Reconstruct an edited policy and research switches solely from its sidecar."""
    policy = EconomicScenario(name='edited', ubi=750, tax=15, speed=20)
    source = tmp_path / 'edited.json'
    source.write_text(json.dumps({'schema_version': 1, 'scenarios': [policy.to_dict()]}), encoding='utf-8')
    assumptions = ModelAssumptions(feedback=False, dividend=False, clipping=False,
                                   demand_strength=.84, tax_adoption_penalty=0)
    simulator = ScenarioSimulator(load_scenarios(source)[0], assumptions, years=3)
    target = tmp_path / 'nested/edited.csv'
    export_run(simulator.run(), simulator, target)
    metadata = json.loads(target.with_suffix('.config.json').read_text(encoding='utf-8'))
    assert metadata['assumptions'] == asdict(assumptions)
    reconstructed = ScenarioSimulator(EconomicScenario(**metadata['scenario']),
                                      ModelAssumptions(**metadata['assumptions']), metadata['years'])
    pd.testing.assert_frame_equal(pd.read_csv(target), reconstructed.run(), check_dtype=False)


@pytest.mark.parametrize('payload', [
    {'schema_version': True, 'scenarios': [{}]},
    {'schema_version': 1, 'scenarios': []},
    {'schema_version': 1, 'scenarios': [None]},
    {'schema_version': 1, 'scenarios': [{'unknown': 1}]},
    {'schema_version': 1, 'scenarios': [{}, {}]},
    {'schema_version': 1, 'scenarios': [{'tax': 41}]},
])
def test_invalid_json_schema(tmp_path, payload):
    source = tmp_path / 'invalid.json'
    source.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError):
        load_scenarios(source)
