"""AAI551 strict JSON input and CSV output with configuration sidecars.

Author: Elaine Liu, with AI development assistance.
"""
import json
from dataclasses import asdict
from pathlib import Path
from scenario import EconomicScenario


def load_scenarios(path):
    """Read schema v1; distinguish missing files from malformed input."""
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid scenario JSON: {exc.msg}") from exc
    if not isinstance(payload, dict) or set(payload) != {'schema_version', 'scenarios'}:
        raise ValueError("expected schema_version and scenarios only")
    if type(payload['schema_version']) is not int or payload['schema_version'] != 1:
        raise ValueError("unsupported schema version")
    if not isinstance(payload['scenarios'], list) or not payload['scenarios']:
        raise ValueError("scenarios must be a nonempty list")
    try:
        scenarios = [EconomicScenario(**item) for item in payload['scenarios']]
    except TypeError as exc:
        raise ValueError("scenario must be an object with known fields") from exc
    if len({s.name for s in scenarios}) != len(scenarios):
        raise ValueError("scenario names must be unique")
    return scenarios


def export_run(frame, simulator, path):
    """Save CSV and sidecar containing assumptions, scenario and horizon."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    path.with_suffix('.config.json').write_text(json.dumps({
        'schema_version': 1, 'scenario': simulator.scenario.to_dict(),
        'assumptions': asdict(simulator.assumptions), 'years': simulator.years,
        'units': 'annual thousand USD per model household; employment percent; concentration index'
    }, indent=2), encoding='utf-8')
