# SecondOrder Scenario

This is a Python simulator for exploring how AI adoption affects employment, household income, consumption, and government finances. It compares scenarios with different assumptions about labor substitution, productivity growth, adoption speed, UBI, and AI taxation.

The notebook shows annual trajectories, policy comparisons, demand-feedback effects, sensitivity analyses, and CSV exports. The model also supports experiments on how these assumptions affect policy rankings.

## Validation

The initial implementation passes 14 tests, including 715 numerical comparisons with the original TypeScript model. A 100-run exploratory pilot is included in `outputs/pilot/`.

The notebook’s code cells have been checked sequentially. Full Jupyter kernel execution and installation checks on Windows and macOS are still pending. Details are in `docs/validation_report.json`.

The model uses illustrative assumptions. Its outputs describe simulated scenarios rather than calibrated economic forecasts.

## Setup on Windows

Install Python 3.12 from python.org and enable the installer PATH option.
Download this repository using Code > Download ZIP, extract it, and open a
PowerShell terminal in the extracted directory containing this README.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name secondorder --display-name "Python 3.12 SecondOrder"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m jupyterlab main.ipynb
```

## Setup on macOS

Install Python 3.12 from python.org. Download and extract the repository ZIP.
Open Terminal, type `cd `, drag the extracted project folder into the terminal,
press Enter, and run:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --prefix .venv --name secondorder --display-name "Python 3.12 SecondOrder"
.venv/bin/python -m pytest -q
.venv/bin/python -m jupyterlab main.ipynb
```

In JupyterLab choose the **Python 3.12 SecondOrder** kernel. Use Kernel > Restart
Kernel and Run All Cells. Open the comparison figure and final exported table.
Edit UBI or tax in `data/scenarios.json`, then restart and run all cells again.
Run outputs are written under `outputs/`; input and reference files are included.
Open supporting `.py` modules in VS Code for editing.

Optional research pilot, from the project directory with the venv activated:

```bash
python -m research.run_pilot
```

Running the simulator requires no Node or API key. To regenerate the TypeScript
reference data, developers use Node 24: `node reference/generate.mjs`.

## Files

| Path | Purpose |
| --- | --- |
| main.ipynb | Main notebook for running and comparing scenarios |
| scenario.py | Validated EconomicScenario and ModelAssumptions |
| simulator.py | ScenarioSimulator composition, recurrence and annual generator |
| analysis.py | Paired comparison, sweep and crossing brackets |
| io_utils.py | JSON input and CSV plus configuration output |
| visualization.py | Annual comparison plots |
| data/scenarios.json | Four artificial policy inputs |
| tests/test_model.py | Functional and parity tests |
| reference/ | Attributed upstream TypeScript and generated expectations |
| research/run_pilot.py | 5 x 5 assumption pairs x 4 policies |
| outputs/pilot/ | Annual rows, paired summaries and source hashes |
| docs/ | Model interpretation, validation and next tasks |
| paper/main.tex | Incomplete English paper scaffold |

## Course requirement mapping

| Part 1 | Implementation evidence |
| --- | --- |
| 1 Classes and relationship | ScenarioSimulator contains EconomicScenario and ModelAssumptions; constructors, validation and run methods |
| 2 Functions | compare_runs, sensitivity_sweep and crossing_brackets in analysis.py |
| 3 Libraries | NumPy grid and comparison, Pandas records/I/O, Matplotlib figures |
| 4 Exceptions and Pytest | ValueError for invalid input; FileNotFoundError for absent input; notebook catches both; tests verify behavior |
| 5 I/O | data/scenarios.json to annual CSV and configuration sidecar; notebook reads export back |
| 6 Loops and conditions | Annual recurrence, sweep and pilot loops; validation and mechanism branches |
| 7 Data types | Lists of policies, dictionaries of rows, numeric values, names and tuple field lists |
| 8 Special methods | `EconomicScenario.__str__`; dataclass-generated fieldwise `__eq__` |
| 9 Documentation | Module headers, class/function docstrings and model_spec.md |
| 10 `__name__` | scenario.py, simulator.py and research/run_pilot.py entry guards |

Part 2 uses these four components: comprehensions in input and pilot processing;
standard library json/pathlib/dataclasses; annual_records generator; zip in
validation, brackets, plots and paired pilot processing.

Rubric: numerical parity and edge cases address correctness (20); mappings above
address Part 1 (20) and Part 2 (10). Separate modules, meaningful names and
docstrings address code quality (20). This README, inputs and setup support
documentation (8). Pitch (5) and live demonstration (7) require the future video.
The video and remaining execution checks are pending.

## Sources and authorship

The simulator implements the equations from [SecondOrder Scenario](https://github.com/ElaineYiyaoLiu/secondorder-site-public/tree/fbec49b96bf875dfa469e170f682d4659e656fd3/apps/scenario) in Python. The original equations are in `lib/model.ts`, and the parameter bounds are in `lib/scenario.ts`. The reference source and generated outputs are included in `reference/` for numerical comparison.

Policy inputs are manually specified illustrative scenarios developed with AI assistance. Output data are generated by the simulator; no observed macroeconomic dataset is used. Units and assumptions are documented in `docs/model_spec.md`.

Author: Elaine Liu. AI assistance was used for code drafting, documentation, test design, and exploratory analysis. Individual work and AI use have been approved by the instructor.

- Email: to be added before submission.
- Stevens ID: to be added before submission.

## Project Video

YouTube Unlisted link: pending. The video will include a short introduction and a live demonstration of the notebook.

## Research

The research extension examines how demand feedback and other model assumptions affect policy rankings. The main experiments, analytical verification, and paper are in progress. The experiment plan is in `research/protocol.json`.
