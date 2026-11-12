# Observe late result lists after a confirmed form submission

The non-editable 0.16.400 candidate at
`1a08c5ad4e412caee18d3ede00e3fe7be51deab1` passed strict live model
preflight. Only **1/3** Python Docs generations and **3/9** planned
browser replays passed. The other six replays did not run because their
adapters were never generated.

Two Python Docs planning journals show a submitted search URL, an
observed result-region container without rows, and unrelated lists in
the accessibility observation. The model proposed the future list rows
in both turns. Exploration rejected both proposals with
`extract_selector_ungrounded` before extraction dispatch. This is
distinct from the older named-input failure in the separate 2/3 cohort.

A local Chromium fixture submits a real GET form and exposes the list
only after the planner has seen the empty region. The prior candidate
rejects the late positive case. The patched source obtains a fresh
accessibility observation and extracts the one actual title/link row;
if the list never appears it still rejects the plan without dispatch or
recording an extraction. Both paths use the same two scripted planning
turns.

This read-only observation applies to a single planned list extraction
after an observed same-origin form transition. It uses the existing
grounding budget, stops if the observed results URL changes, and accepts
only a newly and uniquely grounded target. It does not dispatch the
proposed selector against the page, repeat submission, add model turns,
or reinterpret missing rows as a confirmed empty result. A fresh real
cohort is still required on the patched candidate.
