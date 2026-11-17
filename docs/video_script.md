# Project video rehearsal

Target length: 3 minutes 40 seconds. Record the running program and live code editor. Use no slides or screenshots. This is a rehearsal script; no video has been recorded or uploaded.

## 0:00-1:20: pitch

SecondOrder Scenario explores how AI adoption can affect employment, household income, consumption and government finances. It is intended for students and researchers who want to compare assumptions and follow how a change moves through a model.

The simulator combines labor substitution, productivity growth and adoption speed with two policy options: a monthly household transfer and a tax on AI-related profits. It compares four policies under the same economic conditions and shows their annual paths. Demand feedback can be switched off to isolate its role, and sensitivity analysis shows how outcomes change as an input varies.

The program produces tables, plots and reusable CSV files. Its equations have been checked against the original implementation, and its tests cover invalid inputs, boundary cases and exports. These are illustrative scenarios with explicit assumptions. The benefit is a transparent comparison whose inputs and calculations can be inspected.

## 1:20-3:20: live demonstration

- **1:20-1:45:** Show `data/scenarios.json` in VS Code and point to substitution, productivity, speed, UBI and tax. Open `main.ipynb`, select the Python 3.12 SecondOrder kernel and restart and run all cells. Show the annual table and four-policy plot as they appear.
- **1:45-2:15:** Show the paired employment and income differences and the feedback-on/off output. Explain that each policy faces the same economic conditions, while demand uses the previous year's consumption.
- **2:15-2:40:** Edit the existing UBI-policy monthly input from 500 to 750 in the JSON file, save, restart and run all cells again, and point to the changed results. Rehearse the exact input path and cell location beforehand; do not claim this edited input is part of the frozen research experiment.
- **2:40-3:00:** Show the UBI sensitivity table, substitution brackets and the two handled exceptions. Explain what the actual displayed outputs mean. A bracket identifies a sampled crossing interval; an empty result is also meaningful.
- **3:00-3:20:** Open the newly generated `outputs/ubi_500.csv` and matching configuration sidecar. Show the notebook's successful read-back assertion. Restore the edited JSON input after rehearsal or recording so the repository's frozen inputs remain intact.

## 3:20-3:40: technical close

The notebook imports the supporting modules. EconomicScenario validates policy inputs, and ScenarioSimulator contains that scenario and produces annual records. The analysis module compares runs, while the I/O module preserves both outputs and their configuration. NumPy, Pandas and Matplotlib support the calculations, tables and figures. The README includes setup instructions and the requirement mapping.

Before recording, time a full rehearsal on the actual machine. Keep the pitch between one and two minutes and the live run near two minutes. Verify the final duration is three to four minutes, upload to YouTube as Unlisted, check access, and add the actual link to the Project Video section. Personal details and desktop installation checks remain separate submission tasks.
