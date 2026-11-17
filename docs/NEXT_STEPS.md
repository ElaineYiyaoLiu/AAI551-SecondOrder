# Next steps

E0 reference checks, E1 simplified analytical checks, E2 mechanisms and E3-E5 policy grids, boundary refinement and fiscal comparisons are complete. Research protocol 1.0 and the original model are unchanged. Evidence and figures are in docs/e3_e5_results.md and outputs/policy_grids/validation.json. The 54 functional tests pass.

1. Independently review the main claims and figure inputs for the November 19 reproducibility milestone. Numerical reconstruction of E3-E5 is already complete; avoid repeating completed simulations without a reason.
2. Complete actual Windows/macOS installation and standalone TCP Jupyter checks where those environments are available. Earlier in-process execution remains verified; desktop acceptance is pending.
3. Write the November 24 paper draft using paper/template.tex and docs/paper_style.md. Use verified E1-E5 evidence, review the mathematical claims and literature, then compile and inspect the complete manuscript. The current paper is still a scaffold.
4. Review the paper on November 25 and revise before the internal November 29 target.
5. Rehearse docs/video_script.md, record the 3-4 minute live demonstration, upload the video as Unlisted, and add its real link plus personal email and Stevens ID to README before submission. The official deadline is December 16.

After a fresh checkout run `python -m research.restore_grid_evidence` before the full research verifier or figure builder. The restore command uses only included, hash-checked parts; no external dataset or credentials are needed. Existing completed experiments are never overwritten. The notebook uses the small original policy inputs and does not run the large research grids.
