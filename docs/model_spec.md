# Model specification and limits

The exact default equations and initial state are preserved in reference/model.ts.
The Python implementation follows the upstream order: adoption; demand from prior
consumption; output; employment; labor income and benefits; pretax profit and AI
tax; profit and dividend using prior concentration; income; consumption; annual
fiscal balance; concentration. Both the base year and 10 subsequent years are saved.

Money is annual thousand USD per model household. UBI is entered in monthly USD,
so 500 becomes 6 annual thousand USD. Employment means labor utilization in percent.
Concentration is an illustrative index, with no underlying wealth distribution.
Adoption is a fraction in [0,1]. Demand has default clamp [.65,1.4]; employment
[35,99]; concentration [35,90]. Annual government balance is relative to a base
budget, not a complete public accounting system. Its cumulative sum excludes interest.
Household income does not separately deduct labor taxes.

Research controls vary demand strength [0,.84] and tax adoption penalty [0,.9].
The clipping switch groups demand, employment and concentration clamps together;
adoption bounds and nonnegative flow rules remain in force. Raw values, clamp
flags and out_of_domain are exported. Negative dividend or nonphysical states
may occur outside the interpretive domain when grouped clamps are disabled.
Such rows must be retained and labeled, not interpreted as realistic forecasts.

The pilot pairs policies at every common assumption setting, excludes year zero
from mean outcomes and computes incremental cumulative deficit relative to the
same-setting no-policy run. Grid shares are design-dependent, not probabilities.
These are illustrative structural experiments; they do not identify causal effects
in an observed economy.
