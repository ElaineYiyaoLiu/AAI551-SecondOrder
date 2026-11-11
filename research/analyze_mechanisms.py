"""Build the E2 report and figure from independently verified saved results."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from research.verify_mechanisms import verify_mechanisms

ROOT = Path(__file__).resolve().parents[1]
SWITCHES = ('feedback', 'dividend', 'clipping', 'adoption_suppression')
POLICIES = ('ubi_500', 'tax_20', 'combined')
LAYERS = ('central', 'productivity_led', 'substitution_led')


def analyze_mechanisms():
    """Save traceable, conditional contrasts without changing computed evidence."""
    destination = ROOT / 'outputs/mechanisms'
    validation = verify_mechanisms(write_report=False)
    summary = pd.read_csv(destination / 'summary.csv')
    contrasts = pd.read_csv(destination / 'contrasts.csv')
    selected = []
    for mechanism in SWITCHES:
        other_switches = [key for key in SWITCHES if key != mechanism]
        rows = contrasts.loc[(contrasts.mechanism == mechanism) &
            contrasts[other_switches].eq(True).all(axis=1) & contrasts.policy.isin(POLICIES)]
        selected.append(rows[['layer', 'policy', 'mechanism',
                              'mean_employment_delta_on_minus_off', 'ranking_eligible']])
    selected = pd.concat(selected, ignore_index=True)
    if len(selected) != 36 or not selected.ranking_eligible.all():
        raise ValueError('Unexpected conditional contrast inputs')
    selected.to_csv(destination / 'figure_inputs.csv', index=False)
    limit = max(abs(selected.mean_employment_delta_on_minus_off).max(), 1e-12)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.8), sharey=True, layout='constrained')
    for axis, layer in zip(axes, LAYERS):
        values = selected.loc[selected.layer == layer].pivot(index='mechanism',
            columns='policy', values='mean_employment_delta_on_minus_off').reindex(
                index=SWITCHES, columns=POLICIES).to_numpy()
        image = axis.imshow(values, cmap='coolwarm', vmin=-limit, vmax=limit, aspect='auto')
        axis.set_title(layer.replace('_', ' ').capitalize())
        axis.set_xticks(range(3), ['UBI $500', 'AI tax 20%', 'Combined'])
        axis.set_yticks(range(4), ['Demand feedback', 'Dividends', 'Grouped clamps', 'Adoption penalty'])
        for row, column in np.ndindex(values.shape):
            axis.text(column, row, f'{values[row, column]:.3f}', ha='center', va='center',
                color='white' if abs(values[row, column]) > limit * .65 else 'black')
    fig.colorbar(image, ax=axes, label='Employment effect (percentage points)', shrink=.85)
    fig.suptitle('Mechanism on minus off, with the other mechanisms on', fontsize=13)
    fig.savefig(destination / 'conditional_contrasts.png', dpi=160)
    plt.close(fig)
    full = summary.loc[summary[list(SWITCHES)].eq(True).all(axis=1)].set_index(['layer', 'policy'])
    lines = ['# E2 mechanism experiment', '',
        'The frozen version 1.0 design produced 192 runs, 2,112 annual rows and',
        '384 matched on-minus-off contrasts. Independent checks reconstructed',
        'all trajectories, paired summaries and mechanism contrasts.', '',
        'All 192 runs remain in domain. No grouped clamp activated in this E2',
        'design; its on-minus-off effects are zero here. Boundary behavior is',
        'reserved for the wider assumption grids and refinement experiments.', '',
        'With all mechanisms on, mean employment differences from the matched',
        'no-policy run over years 1–10 are:', '',
        '| Economic layer | UBI $500 | AI tax 20% | Combined |',
        '| --- | ---: | ---: | ---: |']
    for layer in LAYERS:
        values = [full.loc[(layer, policy), 'mean_employment_delta'] for policy in POLICIES]
        lines.append('| ' + layer.replace('_', ' ').capitalize() + ' | ' +
                     ' | '.join(f'{value:.4f}' for value in values) + ' |')
    lines.extend(['', 'Values are percentage points. UBI has zero employment effect when demand',
        'feedback is off. Restoring feedback gives UBI effects of 2.7115–4.0439',
        'percentage points across these layers with the other mechanisms on.',
        'Tax-induced adoption suppression accounts for 1.0437–1.6953 percentage',
        'points of the tax-only policy effect under the same conditional comparison.',
        'Dividend contrasts are smaller and vary by policy. These conditional',
        'ablations retain interactions and should not be summed as a decomposition.', '',
        '![Conditional E2 employment contrasts](../outputs/mechanisms/conditional_contrasts.png)', '',
        'Source tables are `outputs/mechanisms/summary.csv`, `contrasts.csv` and',
        '`figure_inputs.csv`. Complete configurations and hashes are in `manifest.json`;',
        'all annual traces are in `annual.csv.gz`. `validation.json` records the',
        'independent reconstruction. All source configurations, including the',
        'zero-effect cases, remain in the saved results.', '',
        'Run `python -m research.verify_mechanisms` to check the saved results and',
        '`python -m research.analyze_mechanisms` to rebuild this report and figure.',
        'To recompute E2, preserve or move the existing result directory first;',
        '`python -m research.run_mechanisms` refuses to overwrite completed runs.', ''])
    report = ROOT / 'docs/e2_results.md'
    report.write_text('\n'.join(lines))
    paths = [report, destination / 'figure_inputs.csv', destination / 'conditional_contrasts.png']
    evidence = {'status': 'passed', 'rows_in_figure': len(selected),
        'protocol_sha256': validation['protocol_sha256'],
        'experiment_manifest_sha256': validation['manifest_sha256'],
        'analysis_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'matplotlib': matplotlib.__version__,
        'output_hashes': {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in paths}}
    (destination / 'analysis_manifest.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return evidence


if __name__ == '__main__':
    print(json.dumps(analyze_mechanisms(), indent=2))
