# Doctor endpoint privacy and validation

The published PyPI 0.16.398 wheel was downloaded and checked against its
official SHA-256. In an isolated runtime with a fresh local Chromium CDP
connection, ordinary `doctor --json` copied a configured OpenAI-compatible
URL to the response. A dummy marker in the URL appeared in JSON. An address
without a scheme instead returned `E_UNKNOWN` and lost its structured
endpoint check. No real credential or model request was used.

The same CLI checks on patched source report only whether a custom address
is configured. An address rejected by the existing normalizer produces a
structured `E_INVALID_PARAM` / `invalid_openai_base_url` check, including
when live generation capability was requested. That failure never starts
the provider check. The default and valid custom cases remain ready for
local use. The SDK and HTTP doctor share these checks; their controlled
regression exercises both success and invalid configuration without
changing the selected provider or its normalization rules.

For automation, read the boolean `openai_base_url.details.configured`;
the raw `base_url` field is intentionally no longer returned. Historical
benchmark inputs can still be interpreted without copying an address into
the report. Other diagnostic fields may contain local information, so do
not publish full raw output. This is a configuration and privacy fix,
not live model recovery or independent first-use evidence.
