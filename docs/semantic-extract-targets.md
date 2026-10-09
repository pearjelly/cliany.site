# Semantic extract targets

From v0.16.380, fresh browser exploration records an extract target from the actual pre-extract AX snapshot and its observed DOM mapping. Newly generated commands resolve that target on the current page before reading data. This prevents a missing or renamed result container from silently becoming a successful empty result.

## Recorded identity

An action can retain optional `extract_target` metadata containing its role, stable name, observed identity attributes and supported row suffix. Read-only regions use observed AX roles and explicit accessible labels where available; changing count text or package names are not frozen as the region identity. Unnamed regions need a unique role or a distinguishing observed attribute. Grounding replaces model-provided target claims and survives adapter generation and merging.

Generated atom-based commands pass this recorded recipe through `browser extract --target-json`. It is not permission to invent a selector or name. The option validates its JSON shape before connecting to the browser. The ordinary manual extraction interface is unchanged.

## Replay and empty results

Replay captures current AX semantics, resolves the target and verifies exactly one mapped DOM root. It rechecks after waiting for result loading, and the JavaScript reader guards root existence again at read time. Missing or unresolved equal-score targets and missing/non-unique roots return `E_SELECTOR_NOT_FOUND`; an unsettled target can return `E_PAGE_NOT_READY`. A native collection shape incompatible with the extraction mode returns `E_PARSE_FAILED`.

Zero matches can still return `ok=true` when the intended container exists and the command declares `expects_nonempty=false`. That declaration does not excuse a missing count, unresolved container, missing required field or partial result. Existing quality rules remain in effect.

## Runtime compatibility

New semantic adapters and semantic atoms import a capability available in v0.16.380 and newer supporting runtimes. On the public v0.16.379 runtime, strict verification and direct dispatch reject such a new adapter with `E_VERIFY_STATIC` / `commands_unloadable`, before browser or model work. Check the installed package version and upgrade the runtime before retrying strict verification; do not remove the capability import from generated code.

Existing generated adapters are not rewritten or retrofitted. To compare a fresh generation safely, select an empty `CLIANY_RUNTIME_HOME`, explore the same observed workflow, and run `cliany-site verify <domain> --strict --json` before replay. Keep the original installation unchanged until the new command has passed its own changed-input result check. Never hand-edit files marked automatically generated.

## Supported boundary

List mode supports observed native `ul`/`ol` regions and table mode supports native `table`. Arbitrary ARIA collections, inaccessible frames and custom DOM readers are not established by this change. Duplicate names, attribute reuse and unnamed regions can still make identity unresolvable or unsuitable; not every layout change preserves a usable identity. The existing 100-row cap and field-quality checks remain, so correct returned rows do not prove complete collection.

The [dated layout review](user-evidence/2026-10-09-semantic-extract-layout-review.md) records the original wrong success, retained failed reference study, three fresh live source explorations and six independent-browser replays. It does not establish public-package availability, general reliability, faster generation or independent first-user acceptance; those remain separate gates.
