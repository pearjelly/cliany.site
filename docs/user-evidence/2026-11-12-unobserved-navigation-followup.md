# Observe the destination before a second click

[Issue #141](https://github.com/pearjelly/cliany.site/issues/141) records the
third Python Docs exploration on the unpublished, non-editable 0.16.400
wheel from `02b9e5fd66660a84d740131881757a5f87325ec2`. Strict live doctor
passed. The model selected two different links from one homepage AX
observation: Search page and Complete table of contents. It included the
second link in the executable actions even though its description called
it an unexecuted fallback.

The runtime could not resolve the second target. The journal reports
`action_execution_failed`, started dispatch and no execution receipt;
no adapter was generated and the three planned replays did not run.
The [whole cohort](https://github.com/pearjelly/cliany.site/pull/136#issuecomment-6820665697)
completed 2/3 workflows and verified 6/9 planned replays. This is separate
from the earlier late-extract rejection and from the published 0.16.398
duplicate-click case. The original private failure journal has SHA-256
`d5bac96818e0074efc92a746e66912bcba6800ac5682f60556667e90b05e121d`.

A local Chromium fixture reproduces the missing second target on the
previous source: the first link opens the destination and the executor
then fails on the fallback link. The correction uses the observed
same-tab anchor to a different document to reject adjacent clicks from
that observation before dispatch. The existing repair budget permits a
new plan with one click, followed by input grounded in the new page. A
repeated invalid plan fails with `navigation_followup_unobserved`, no
navigation and a planning-only failure record. Repeated clicks on one
link retain `duplicate_navigation_click`.

This does not infer intent from the description or change execution of
single clicks, same-document links, downloads or new-tab links. It
does not retry an action, rewrite a generated adapter, or establish
real-model or independent-user acceptance of the correction.
