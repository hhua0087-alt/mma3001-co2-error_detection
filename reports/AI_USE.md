# AI use and verification

OpenAI Codex provided substantial assistance with code generation, debugging,
experiment design suggestions, interpretation, plots, English drafting and the
modular submission refactor. The contribution was extensive rather than limited
to spelling or formatting. The exact model identifier was not independently
recorded. Packaging work took place on 24 to 25 October 2026.

The workflow checks generated suggestions against numerical evidence: CUSUM
scaling equivalence, input-time causality, fault labels, reset behaviour,
unmodified source hashes, reproduction of eight-input NN weights, default metrics
and the full sensitivity grid. The six-input attempt was retained despite weaker
results in common conditions. The 20 ppm, 48-reading counterexample and the
selected CUSUM's poorer moderate-spike coverage are disclosed.

These automated checks are not a claim that the student independently inspected
every code line or validated real sensor faults. The student must add their own
actual checks, decisions, errors identified and learning reflection to the personal
report. Do not replace this with invented claims of manual review. The author is
responsible for all submitted code, results, references and explanations.

Course data were retained locally and were not uploaded as part of packaging.
No inference about real sensor health follows from simulated labels or passing
implementation tests. No remote GitHub publication is claimed by this document.
