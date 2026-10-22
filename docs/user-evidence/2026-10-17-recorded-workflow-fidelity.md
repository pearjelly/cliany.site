# Recorded Workflow Fidelity

**Unpublished PR103, Issue106.** Current published master/tag remains
`4536dd562fdf703205be79918a67d1393cdda2f1`, version0.16.390. Shanghai October17
already has three actual formal GitHub releases; no fourth tag, merge or deployment.
Independent first use stays0/2 on fixed published0.16.387.

## Passing Cohort And New Counterexamples

Prior source `3835349d164ff2e005e2d1d28f6866d757308759` passed explicit-offline
3,850 tests540.18s, ordinary CI38978499872 and Chromium CI38978499880
(80 passed,1 deselected512.14s). A separately predeclared uninstrumented real study
passed3/3 fresh generations and9/9 changed-query/zero-match row checks; its immutable
report SHA remains `22b66ae137628e18505cd5c945a6ff44bd773ed3075244fb4b35109feee730fa`.
The separate v3 diagnostic passed3/3,9/9, SHA
`5ecd7e2d8a8b97f84e9bb632ca8de7f43f8b54f3b858a85f8dd009e807d5a648`.
Those finite successful cohorts do not prove arbitrary recorded stages or bindings.

The new controlled read-only staged-search review reproduces two wrong successes:

1. Two identical Continue clicks advance the normal page to group2. Generated CLI
   silently deletes one and returns group1:Gamma rows with success. SDK and HTTP
   preserve both clicks and return the expected group2:Gamma rows.
2. An explicitly declared query input in a later group also changes an earlier
   matching input that belongs to a fixed Alpha baseline. All three entrypoints
   return Gamma instead of Alpha for the baseline. CLI additionally deletes the
   later input/submission, reading Preview rows instead of the requested Gamma
   group. For no-match, SDK/HTTP lose the nonempty fixed baseline; CLI still returns
   unrelated Preview rows. Successful status is not business correctness.

Reviewed native controls failed2 tests108.08s. All twelve per-entrypoint/query
comparisons retain their full arrays: five correct observations and **seven wrong
successes**, not seven independent people or live-provider failures. The first
27.31s attempt failed because the test passed SDK params positionally; that fixture
error is retained separately and is not product evidence. Focused red retained
12 failures and9 passes0.42s. Original fixture responses, expected normal-page rows,
logs and generated artifacts remain outside the repository, unchanged.

## Correction

Both renderers now preserve recorded business action order and multiplicity rather
than applying target/value-based deduplication. Identical click, submit, navigation
or input identities can denote different workflow stages. This can emit more
recorded steps than the old incorrect cleanup; it is not an automatic retry.
Predeclared probes still do not enter business replay, and the explorer's existing
bounded duplicate-completed-collection check is unchanged. Return arrays are not
selected, flattened or deduplicated to pass an oracle.

A single `action_index` substitutes only that owned type/select input. One argument
genuinely used in several inputs declares `action_indices`, a nonempty unique list
of owned integer indices, mutually exclusive with the scalar form. No fingerprint
broadcast is inferred. A default matching several remaining recorded values fails
with `ambiguous_default` rather than choosing a scope. Existing valid inline and
URL placeholders remain supported; non-value bindings and clobbered parameters
remain rejected. Prompt guidance and partition-repair ownership cover both forms
without increasing model, action, navigation or correction budgets.

SDK and merge rebase explicit bindings through complete original index mappings,
including probe gaps, without mutating original argument lists. New probe-bearing
history snapshots retain full command declarations, including original bindings;
old histories stay unchanged. Invalid/ambiguous legacy SDK binding metadata returns
`E_VERIFY_STATIC` before browser work, including dry-run; HTTP uses the existing
JSON422 mapping, with a fixed reason rather than input values or exception bodies.
This is not general validation of every possible historical metadata shape.

Existing generated command files and pinned archives are not patched. Newly
generated or normally merged code receives the renderer correction; an old saved
CLI still contains its old emitted steps/placeholders. Upgrading runtime alone does
not retroactively repair that code. Do not infer a user's old multi-input intent;
regenerate with an explicit workflow/binding declaration when needed.

## Source Evidence And Remaining Gates

Corrected source passed three native controls165.99s. CLI/SDK/HTTP agree with all
returned normal-page collections for changed Gamma and legitimate no-match, across
the two-click wizard, fixed Alpha baseline plus variable query, and an explicitly
multi-bound query used in both groups. Eighteen per-entrypoint/query comparisons
pass, and generated core hashes remain unchanged. These are controlled recorded
plans on an owned fixture, not real model discovery or independent-user acceptance.
Strict CLI verify-before/after controls are added for the frozen full/CI reruns.

Reviewed focused controls passed97 in1.05s; broad non-embodied/non-perf regression
passed3,805 with92 deselected65.72s. That broad run predates five final history/mapping
checks and is not the full frozen suite. Ruff and Mypy127 passed. A pytest temporary
garbage-directory cleanup warning remains recorded; it is not a business failure or
proof of a browser leak, and no user directory was removed.

Freeze combined source, rerun complete explicit-offline/static/case/package/build
and exact-SHA ordinary/Chromium CI. Then require fresh real
`doctor --llm-live --require-capability generate_adapters --json` and separately
predeclared real studies with all-returned-row oracles; retain any failure. A real
fixed-baseline comparison is a new explicitly requested multi-scope cohort, not a
way to regrade the old failed single-search outputs. Preserve all prior scores,
including bb diagnostic1/3,3/9 planned checks and official3902/3,6/9 checks.

Later publication still needs fresh online capacity, meaningful version/changelog/
roadmap/site/notes, final-master and tagged gates, exact GitHub/PyPI artifacts,
correct Vercel production/aliases, official installed-package workflow acceptance
and final strict remote distribution audit. No independent-user credit or candidate
promotion follows from these source checks. Issues33/55/100/102/104/105/106 stay open.
