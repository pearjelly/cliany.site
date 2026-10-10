# LLM failure and retry diagnostics

From v0.16.381, a recognized HTTP status takes precedence over response-body gateway keywords. HTTP 401/403 stops after one visible attempt with CLI `E_LLM_AUTH_FAILED`; other rejected HTTP requests stop with `E_LLM_UNAVAILABLE` and `retryable=false`. Check the selected service's key, permissions, endpoint and request configuration before retrying. Do not send keys to a different service as a diagnostic shortcut.

The existing retry set remains HTTP 429/500/502/503/504. Typed timeouts and network failures can also use the configured outer attempts and backoff. The OpenAI-compatible client's 120-second network-operation timeout and zero SDK-internal retries are unchanged; these are not whole-workflow deadlines. Retried requests may incur model cost.

## Progress events

`explore --json` keeps its result envelope on stdout and progress on stderr. A failed model attempt can now emit an additional event before the existing `explore_llm_attempt_done`:

```json
{"event":"explore_llm_attempt_error","step":0,"attempt":1,"reason":"timeout","status_code":null,"retryable":true,"ts":0}
```

`reason` is one of `authentication_failed`, `rate_limited`, `upstream_http_error`, `request_rejected`, `http_error`, `timeout`, `connection_error`, `upstream_unavailable` or `unknown`. Numeric HTTP status, when present, is preserved without response bodies. A category is a diagnostic classification, not proof of a provider's internal cause. In particular, legacy connection/gateway text matching remains a heuristic when no typed transport or HTTP status is available.

`retryable` describes the failure, not whether another attempt actually follows: the final transient failure can remain retryable. Use the existing done event's `outcome` and `backoff_ms` to see scheduled recovery. Custom reporters implementing only the existing attempt-start/done callbacks still work; the error callback is optional.

The new error event and retry warning exclude prompts, model response text, exception text, endpoint URLs and credentials. This is not a privacy guarantee for the entire pre-existing progress stream: other events intentionally contain the requested workflow URL or action descriptions. Share only a sanitized subset.

The controlled benchmark stores bounded `attempt_errors` with step, attempt, category, status and retryability. Historical reports without those events cannot identify the cause of old long waits and are not rescored. Unknown or malformed event values are not copied into reports.

## Before live exploration

```bash
cliany-site doctor --llm-live --require-capability generate_adapters --json
```

Continue only after this real preflight passes. A failed preflight is availability evidence, not a failed or successful generated workflow. [Issue 38](https://github.com/pearjelly/cliany.site/issues/38) still requires provider/public-site tail measurement; independent first-user acceptance remains separate. Existing adapters, semantic grounding, zero-match declarations and extraction quality gates are unchanged. CLI/live doctor diagnostics do not claim SDK/HTTP exploration-envelope parity.
