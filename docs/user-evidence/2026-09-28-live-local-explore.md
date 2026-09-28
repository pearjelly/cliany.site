# Live model exploration on an isolated local page (2026-09-28)

## Scope

The target was the repository's local `tests/embodied/pages/action_replay.html`, served on `127.0.0.1:48765`. Runtime adapters were written only under isolated `/tmp` cliany-site directories; initial runs also replaced the process `HOME`, while later controls preserved it. The configured OpenAI-compatible provider passed `doctor --llm-live --require-capability generate_adapters --json` before each live exploration. No generated adapter or session file was edited or committed.

## Published baseline

PyPI-installed v0.16.363 returned `E_PAGE_NOT_READY` after the browser event bus timed out on its first navigation in an auto-launched headless Chrome while the whole process used a temporary `HOME`. The local HTTP server saw no request. Direct HTTP access to the page succeeded. This reproduced the timeout without PyPI, npm, or crates.io, but did not by itself establish a default-browser defect.

After an independently launched Chrome had opened the page through its native CDP endpoint, v0.16.363 completed real-model exploration and generated `apply-color-selection` and `read-result`. The first command successfully typed Ada, selected Blue, and clicked Apply. The second command navigated back to the source page, extracted `untouched`, and returned `E_EMPTY_RESULT` even though extracted text was nonempty. The split command could not preserve the intended workflow result.

## Unreleased candidate

The next-version worktree now rejects an extract-only follow-up command when prior interaction actions would be lost on independent replay, and tells the model to combine the dependent steps. Generated data commands also trust the existing mode-aware extraction quality result instead of requiring list-shaped data. A fresh live-model run produced one parameterized `apply-name-color-and-read` command with all four actions. Its isolated Chrome replay returned `ok=true`, `quality.status=ok`, and `Ada:Blue`; changing both parameters returned `Grace:Red` with the same success status. This is a real model and browser run on a controlled local page, not evidence of third-party site availability or TypeSafe Jev accuracy.

The local URL's raw domain includes a port (`127.0.0.1:48765`), while the invocable and verifiable CLI group is `127.0.0.1_48765`. The candidate adds `explore.data.command_group` to expose that identifier without changing the source domain.

## Remaining boundary

The successful exploration above used an explicitly managed, pre-opened CDP browser. A subsequent controlled comparison kept the real macOS `HOME` while pointing cliany-site's runtime `home_dir` to `/tmp`; two fresh auto-launched headless Chrome instances reached the local page and completed navigation. The browser library logged an 8-second page-readiness warning in both runs, so this is not a latency guarantee. With the whole `HOME` replaced by `/tmp`, a fresh auto-launched browser still timed out after an extra three-second wait. The temporary system `HOME` is therefore an important confound in the failed cold-start tests; do not claim the normal default headless path is broken from those runs.

Keeping real `HOME` and isolated runtime data also let a fresh headless Chrome reach PyPI's `Client Challenge` page. The published PyPI adapter then failed with `E_SELECTOR_NOT_FOUND` rather than a navigation timeout. This confirms the online search remains blocked by the observed site page, independently of the temporary-HOME navigation artifact. No package-search candidate was promoted.
