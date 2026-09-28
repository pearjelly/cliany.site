# Live model exploration on an isolated local page (2026-09-28)

## Scope

The target was the repository's read-only `tests/embodied/pages/action_replay.html`, served on `127.0.0.1:48765`. Runtime adapters were written only under fresh `/tmp` HOME directories. The configured OpenAI-compatible provider passed `doctor --llm-live --require-capability generate_adapters --json` before each live exploration. No generated adapter or session file was edited or committed.

## Published baseline

PyPI-installed v0.16.363 returned `E_PAGE_NOT_READY` after the browser event bus timed out on its first navigation in an auto-launched headless Chrome, before the local HTTP server saw a request. Direct HTTP access to the page succeeded. This reproduces a cold-start browser path problem without PyPI, npm, or crates.io; it does not prove the precise cause.

After an independently launched Chrome had opened the page through its native CDP endpoint, v0.16.363 completed real-model exploration and generated `apply-color-selection` and `read-result`. The first command successfully typed Ada, selected Blue, and clicked Apply. The second command navigated back to the source page, extracted `untouched`, and returned `E_EMPTY_RESULT` even though extracted text was nonempty. The split command could not preserve the intended workflow result.

## Unreleased candidate

The next-version worktree now rejects an extract-only follow-up command when prior interaction actions would be lost on independent replay, and tells the model to combine the dependent steps. Generated data commands also trust the existing mode-aware extraction quality result instead of requiring list-shaped data. A fresh live-model run produced one parameterized `apply-name-color-and-read` command with all four actions. Its isolated Chrome replay returned `ok=true`, `quality.status=ok`, and `Ada:Blue`; changing both parameters returned `Grace:Red` with the same success status. This is a real model and browser run on a controlled local page, not evidence of third-party site availability or TypeSafe Jev accuracy.

The local URL's raw domain includes a port (`127.0.0.1:48765`), while the invocable and verifiable CLI group is `127.0.0.1_48765`. The candidate adds `explore.data.command_group` to expose that identifier without changing the source domain.

## Remaining boundary

The auto-launched Chrome cold-start navigation still timed out on this host. The successful exploration used an explicitly managed, pre-opened CDP browser. A separate browser/launcher diagnosis is needed before claiming that the default headless path works here. No package-search candidate was promoted.
