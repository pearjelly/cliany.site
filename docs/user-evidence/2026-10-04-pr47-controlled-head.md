# PR #47 fixed-head controlled benchmark (2026-10-04)

The predeclared local three-task matrix ran ten fresh live explorations per task on clean commit `4d90e3c796760319221e92e62c674d05ccf6b004`, using `deepseek-v4.1-flash` and headless Chromium. The report was written outside the repository at `/tmp/cliany-pr47-strict-30-20261004-4d90e3c.json`; it records `git_dirty=false`, a successful 3.89-second preflight, and `eligible_for_issue_acceptance=true`.

| Task | Correct / total |
| --- | ---: |
| Form result | 10 / 10 |
| Filter catalog | 10 / 10 |
| Semantic reorder | 10 / 10 |
| **Total** | **30 / 30** |

All 40 changed-input replays passed both returned-value and independent DOM oracles. No successful envelope contradicted those oracles. Nearest-rank exploration latency was 15.3 seconds at p50, 105.9 seconds at p90, and 186.4 seconds at p95; the maximum was 213.64 seconds, with five of 30 explorations over 60 seconds. The two slowest trials spent 205.34 and 182.64 seconds in individual successful model waits. There were zero recorded command-partition repair attempts, so this run does not demonstrate that the repair path improved live reliability.

This is a controlled local sample, not a public-site success rate or independent first-user acceptance. It is the eighth 30-trial sample in the October plan; earlier scores varied from 21/30 to 30/30. The [Python documentation candidate](2026-10-03-python-docs-browser-candidate.md) has separate normal-site evidence and remains unpublished pending a public adapter package URL and independent-user feedback.
