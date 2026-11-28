# SecondOrder Scenario

What happens to employment and household spending as firms adopt AI? This Python notebook follows four cases over ten years: no new policy, a household transfer, a tax on AI profits, and both policies together.

Start with the settings in `data/scenarios.json`. Change how fast AI is adopted, how much work it replaces, or how much productivity it adds. The notebook plots the results and saves the annual values and run settings.

## Setup on macOS

1. Install [Python 3.13](https://www.python.org/downloads/).
2. On GitHub, select **Code → Download ZIP** and extract it. In Terminal, type `cd `, drag in the extracted directory containing `README.md` and `main.ipynb`, and press Enter.
3. Run these commands from that directory.

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --prefix .venv --name secondorder --display-name "Python 3.13 SecondOrder"
.venv/bin/python -m pytest -q
.venv/bin/python -m jupyterlab main.ipynb
```

## Run the notebook

1. In JupyterLab, select the **Python 3.13 SecondOrder** kernel. Choose **Kernel → Restart Kernel and Run All Cells**.
2. Inspect the annual table, four-policy plot, paired comparison, and sensitivity sweep. The final cell prints `CSV round trip verified: 11 annual rows`.
3. In the file browser, open `outputs/policy_comparison.png`, `outputs/ubi_500.csv`, and `outputs/ubi_500.config.json`. The CSV includes year zero and ten simulated years. The JSON records the scenario, assumptions, and horizon.
4. To try a different input, open `data/scenarios.json` in VS Code. In the `ubi_500` entry, change `ubi` from 500 to 750 and save. Keep the scenario name. Restart and run all cells again, inspect the plot and configuration file, then restore the input to 500.

Dependencies are listed in [requirements.txt](requirements.txt). NumPy supplies the sensitivity grids and comparisons, pandas handles the annual tables and CSVs, and Matplotlib draws the plots. The remaining dependencies support Jupyter and Pytest. Use VS Code to edit the supporting modules.

## Repository structure

| Path | Role |
| --- | --- |
| [main.ipynb](main.ipynb) | Runs and compares scenarios |
| [scenario.py](scenario.py) and [simulator.py](simulator.py) | Validate inputs and compute the annual recurrence |
| [analysis.py](analysis.py) | Aligns years, compares runs, sweeps parameters, and finds crossing brackets |
| [io_utils.py](io_utils.py) and [visualization.py](visualization.py) | Read JSON, export CSV with its configuration, and plot results |
| [data/](data/) and [reference/](reference/) | Policy inputs and pinned TypeScript reference values |
| [tests/](tests/) | Model, boundary, export, and research checks |
| [research/](research/) and [outputs/](outputs/) | Experiment scripts, records, and figures |
| [docs/](docs/) | Model notes and validation |

## Validation

The 54 tests check the yearly update order, boundary cases, invalid inputs, and CSV exports. They also compare 715 values with the TypeScript model. On macOS, the notebook ran from a fresh Jupyter kernel with the default inputs and a second set of inputs. See the [macOS acceptance runs](https://github.com/ElaineYiyaoLiu/AAI551-SecondOrder/actions/workflows/course-acceptance.yml) and [validation report](docs/validation_report.json).

Run the same standalone check from the project directory with the virtual environment’s interpreter.

```bash
python -m research.validate_notebook --transport tcp
```

## Course requirements

| Part 1 | Where to check |
| --- | --- |
| 1. Related classes | `ScenarioSimulator` contains an `EconomicScenario` and `ModelAssumptions`. These classes validate the inputs and run the model. |
| 2. Functions | `compare_runs`, `sensitivity_sweep`, and `crossing_brackets` in `analysis.py` support the comparisons. |
| 3. Advanced libraries | NumPy builds grids and checks values, pandas handles records and CSV, and Matplotlib plots policy paths. |
| 4. Exceptions and tests | The notebook catches `ValueError` for invalid parameters and `FileNotFoundError` for an absent input. Pytest checks both and verifies model behavior. |
| 5. Data I/O | The notebook reads scenario JSON, writes CSV and configuration JSON, then reads the CSV back. |
| 6. Loops and conditions | The simulator iterates through years and applies feedback, dividend, and clipping branches. The analysis iterates through a parameter sweep. |
| 7. Data types | A list stores scenarios and dictionaries store annual records. Numeric inputs and string names identify cases, and a tuple holds reference field names. |
| 8. Special methods | `EconomicScenario.__str__` formats the inputs. The dataclass supplies fieldwise `__eq__`. |
| 9. Documentation | Module headers, docstrings, and comments explain the code. The model specification records units and update order. |
| 10. `__name__` | `scenario.py`, `simulator.py`, and `research/run_pilot.py` have direct-execution guards. |

| Part 2 | Where to check |
| --- | --- |
| Comprehensions | `main.ipynb` collects runs by policy name. |
| Standard library | `io_utils.py` reads and writes JSON with `json` and handles paths with `pathlib`. |
| Generator | `ScenarioSimulator.annual_records` yields one annual record at a time. |
| Special function | `analysis.crossing_brackets` uses `zip` to pair adjacent sample coordinates and differences. |

See the [tests](tests/) and [validation report](docs/validation_report.json) for the checks, and the [project video](#project-video) for the live demo.

## Model source and project member

The Python implementation follows the pinned [SecondOrder TypeScript model](https://github.com/ElaineYiyaoLiu/secondorder-site-public/tree/fbec49b96bf875dfa469e170f682d4659e656fd3/apps/scenario). The policy inputs are manually specified illustrative scenarios developed with AI assistance. The simulator generates the output data. See the [model specification](docs/model_spec.md) for units and assumptions. To regenerate the TypeScript reference values, run `node reference/generate.mjs` with Node 24.

Elaine Liu developed the original model and its Python version, including the notebook, tests, and experiments. The instructor approved individual work and the use of AI assistance for code, documentation, tests, and analysis.

| Name | Stevens email | Stevens ID |
| --- | --- | --- |
| Elaine Liu | yliu351@stevens.edu | 20029197 |

## Project Video

[Watch the project video on YouTube](https://youtu.be/E__5ooSOruw)

## Experiments

The [mechanism runs](docs/e2_results.md) show what changes when individual model settings are switched off. The [grid results](docs/e3_e5_results.md) show where policy rankings change and which options fit each budget cap. The [protocol](research/protocol.json) records the inputs and comparison rules.

From the repository root, use the virtual environment to restore and verify the saved evidence. Restoration verifies the included file hashes and needs about 125 MB of additional space.

```bash
python -m research.verify_mechanisms
python -m research.restore_grid_evidence
python -m research.verify_policy_grids
python -m research.analyze_policy_grids
```
