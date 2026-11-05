# Transfer response in the simplified model

The calculation in `research/analytic_response.py` is independent of the simulator.
It fixes economic parameters, tax and adoption penalty across paired policies,
disables dividends, and disables the grouped demand, employment and concentration
clamps. The same year-zero state is used for every transfer. This isolates the
demand channel; it is not a formula for the full model.

## Recurrence and local derivative

Let T = 12u/1000 be the annual transfer in thousand USD for monthly UBI u.
Let s, p, v and tau be substitution, productivity, speed and tax expressed as
fractions, and let eta be the adoption penalty. Adoption has the closed form

\[
A_t=1-(1-v(1-\tau\eta))^t.
\]

Write g for demand strength, with g=0 when feedback is disabled. Define

\[
K_t=95\frac{1-sA_t}{1+0.55pA_t},\qquad
w_t=\frac{60}{95}(1+0.12pA_t).
\]

Because consumption is 0.75 times income, the simplified equations are

\[
E_t=K_t(1-g+gI_{t-1}/60),\quad
I_t=w_tE_t+0.12\max(0,95-E_t)+T,\quad I_0=60.
\]

On a fixed benefits branch, put z_t=1 if E_t<95 and z_t=0 if E_t>95.
Then I_t=(w_t-0.12z_t)E_t+11.4z_t+T. For a locally unchanged branch sequence,
the income derivative x_t with respect to T satisfies

\[
x_0=0,\qquad x_t=1+\rho_t x_{t-1},\qquad
\rho_t=\frac{gK_t}{60}(w_t-0.12z_t).
\]

Consequently,

\[
x_t=\sum_{j=1}^t\prod_{k=j+1}^t\rho_k,\qquad
\frac{\partial E_t}{\partial T}=\frac{gK_t}{60}x_{t-1},\qquad
\frac{\partial C_t}{\partial T}=0.75x_t.
\]

The empty product equals one. The sum follows by repeated substitution into
x_t=1+rho_t x_(t-1). Since x_0=0, year one has income response 1, consumption
response 0.75 and employment response 0. With g>0, employment first responds
in year two. With g=0, employment never responds to UBI through this channel.
Per monthly dollar of UBI, multiply these derivatives by 0.012.

For the allowed parameters K_t>0 and w_t-0.12z_t>0. Also
K_t w_t/60=(1-sA_t)(1+0.12pA_t)/(1+0.55pA_t)<=1.
Thus 0<=rho_t<=g<=0.84, and 1<=x_t<=sum_(j=0)^(t-1) g^j<=6.25 for t>=1.
These are local statements within the stated branches. The test suite checks
the product solution separately from the derivative recursion.

## Branches and scope

At E=95 the benefits rule has a kink. The implementation rejects a reachable
kink when employment has nonzero transfer sensitivity. Year one's employment
can equal 95 while its sensitivity is zero; the income derivative is still 1.
Finite policy differences equal derivative times transfer change only when the
whole segment stays on the same branch sequence. Tests verify the branch
sequence before using this identity.

The formula does not include dividend changes, concentration feedback into
dividends, clamp plateaus or derivatives across tax rates. Adoption remains
bounded under the allowed parameter ranges. Unclipped employment can exceed
the model's interpretive bounds. Such states are retained by the simulator and
must still be labeled in experiments.

## Verification and research decision

The numerical check covers the three planned economic layers, feedback on/off,
and monthly UBI 0/500 at tax 20: 12 paired configurations. Each compares all
11 years of independently calculated levels with the simulator, then compares
local responses with a one-dollar monthly increment. Separate tests exercise
both benefits branches, the kink, and rejection of full-model controls.
`python -m research.run_analytic_checks` saves the checks and source hashes.

The project can proceed as a model-specific robustness study. Its immediate
question is which policy rankings depend on the chosen feedback mechanisms and
clamps. The algebra above is a verification tool, not a claim of a new economic
theory. The main experimental protocol remains unfrozen until policy, budget
and boundary rules are specified.
