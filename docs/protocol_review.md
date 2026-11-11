# Experiment protocol

Version 1.0 fixes the E2–E5 design before the main experiments. The existing
100-run pilot and simplified analytical checks informed the design. Their
outputs are exploratory evidence available before this freeze.

The four policies form a 2 by 2 comparison: monthly UBI of 0 or 500 dollars,
and AI tax of 0 or 20 percent. These levels are retained from the original pilot
to compare transfers, taxation and their combination under the same assumptions.
The three economic layers span central, productivity-led and substitution-led
settings. They are illustrative parameter combinations.

E2 uses all 16 combinations of demand feedback, dividends, grouped clamps and
tax-induced adoption suppression. The first three are the model's existing
Boolean switches. Suppression uses penalty 0.45 when on and zero when off.
Demand strength stays at 0.42. With three layers and four policies, this gives
192 runs. Each policy is paired with the no-policy run at the identical layer
and switch setting. On-minus-off contrasts hold all remaining settings fixed;
interactions are preserved.

E3 restores all three Boolean mechanisms and uses inclusive 41 by 41 grids over
demand strength [0, 0.84] and adoption penalty [0, 0.9]. This gives 20,172 runs.
The primary metric averages candidate-minus-baseline employment over years
1–10. Year zero remains in the trace and is excluded from outcome summaries.
Employment is measured in percentage points; income and fiscal quantities use
the model's thousand-dollar household units. The fiscal metric is the signed
ten-year incremental deficit relative to the paired no-policy run.

The protocol defines an absolute employment tie tolerance of 1e-9 percentage
points. All co-winners remain visible. Finite out-of-domain trajectories are
retained as diagnostics, with flags inherited from either side of a pair. They
are excluded from in-domain ranking maps. Nonfinite quantities yield explicitly
invalid runs and null summaries; a computation exception fails stage validation.
No configuration is silently discarded.

E4 compares inclusive 21, 41 and 81 point grids and refines adjacent sign-change
edges by bisection to coordinate width 1e-6 or 30 iterations. Exact ties,
no-crossing cases, disconnected domains and unresolved brackets are retained.
The sampled grid does not establish completeness of a boundary search.

E5 uses cumulative incremental-deficit caps of 0, 30 and 60 thousand dollars per
model household. A UBI of 500 dollars per month implies 60 thousand over ten
years before endogenous offsets; 30 is the intermediate allowance. Feasibility
uses the signed fiscal metric, so fiscal savings remain visible. These cutoffs
are design choices. Policy rankings and grid shares describe this stress test.

Each stage records exact protocol and source hashes, resolved run inputs,
environment versions and output hashes. Validation reconstructs summaries from
saved traces without using the runner's summary function. E2 also reconstructs
all 192 trajectories and checks every switch combination. Any later design
change requires a new protocol version and an explicit reason.

Notebook execution and model experiments have separate acceptance checks. Two
fresh-process, in-process Jupyter kernels check code execution, rich figure
output, default and edited JSON inputs, and CSV reconstruction. Standalone
ZeroMQ transport and macOS installation remain environment checks;
they do not change the recurrence or prevent deterministic Linux experiments.
