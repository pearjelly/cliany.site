# Chrome Startup Cancellation Ownership

## Observed Official394 Failure

A non-editable official PyPI394 native control sent actual SIGINT during the
first ordinary0.5-second readiness sleep of headless doctor. The CLI returned
exit130/E_CANCELLED, but the Chrome it had started remained alive after CLI
exit. An observer verified that process's identity, creation time and unique
test profile, then stopped only that owned browser. No sleep was extended,
model called, user browser reused or generated file changed.

## Staged Correction And Retained Failures

Ten new cleanup regressions failed on the old launcher. Catching failed
startup and cleaning its owned process made75 focused tests pass, but two
native source controls still left the browser and port alive. A further native
diagnostic recorded a pending asyncio cancellation count of1 when synchronous
startup returned, with no launcher exception. That failed prototype is not a
passing repair. One new async handoff regression then failed while its
external-browser counterpart passed.

The revised source adds a cancellation checkpoint after local startup has
returned and before availability is handed back. On pending cancellation,
clean only the newly created process, reap it and clear owned state. Launcher
exceptions and failed second discovery use the same bounded cleanup. Preserve
the original error even if ordinary OS cleanup fails; terminate/wait5 seconds,
then kill/wait5 seconds when needed. Do not search for or kill a process by
port, change the40 polling iterations, increase model budgets or modify an
existing user's profile/session/adapter.

The subsequent focused set passed95 tests. A new native signal control
returned exit130/E_CANCELLED with both the owned process and its port gone;
the observer did not need to clean anything. A real-browser CI regression
also verifies that a new Chrome can immediately start on the same port. These
source checks still require new exact-commit and actual-package gates.

## Boundaries

Cleanup is bounded and cannot guarantee an OS process will cooperate. Normal
successful ownership transfer and reuse of an existing browser remain intact.
This stage-specific evidence does not explain the earlier99/1 browser-suite
failure or120-second observer timeout in Issue116. All original failures stay
separate. Issue117 tracks the new defect; candidate cases are not promoted.
Independent first use remains0/2 on the unchanged fixed387 trial. Maintainers,
assistance and retries do not fill those participant slots.
