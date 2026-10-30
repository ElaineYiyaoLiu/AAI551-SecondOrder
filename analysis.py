"""AAI551 paired comparisons, parameter sweeps, and sign-change brackets.

Author: Elaine Liu, with AI development assistance.
"""
from dataclasses import replace
import numpy as np
import pandas as pd
from simulator import ScenarioSimulator


def compare_runs(reference, candidate):
    """Return candidate minus reference, requiring unique identical year sequences."""
    if reference.year.duplicated().any() or candidate.year.duplicated().any() or not np.array_equal(reference.year, candidate.year):
        raise ValueError("runs must have identical, unique years in the same order")
    fields = ['employment', 'income', 'balance', 'consumption']
    delta = candidate[fields].reset_index(drop=True) - reference[fields].reset_index(drop=True)
    delta.insert(0, 'year', reference.year.to_numpy())
    return delta


def sensitivity_sweep(scenario, field, values, assumptions=None):
    """Sweep one validated scenario parameter and summarize years 1 through 10."""
    if field not in ('substitution', 'productivity', 'speed', 'ubi', 'tax'):
        raise ValueError("unsupported scenario parameter")
    records = []
    for value in values:
        frame = ScenarioSimulator(replace(scenario, **{field: float(value)}), assumptions).run()
        records.append({field: float(value), 'mean_employment': frame.employment.iloc[1:].mean(),
                        'mean_income': frame.income.iloc[1:].mean()})
    return pd.DataFrame(records)


def crossing_brackets(x, differences):
    """Return sampled exact zeros and adjacent strict sign changes; not root proofs."""
    x, y = np.asarray(x, dtype=float), np.asarray(differences, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) < 2:
        raise ValueError("need equal one-dimensional arrays with at least two points")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not (np.diff(x) > 0).all():
        raise ValueError("finite values and strictly increasing x required")
    brackets = [(float(a), float(a)) for a, b in zip(x, y) if b == 0]
    for left, right, yl, yr in zip(x[:-1], x[1:], y[:-1], y[1:]):
        if (yl < 0 < yr) or (yr < 0 < yl):
            brackets.append((float(left), float(right)))
    return sorted(brackets)
