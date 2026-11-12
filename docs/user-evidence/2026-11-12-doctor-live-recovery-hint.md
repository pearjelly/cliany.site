# Live preflight recovery guidance

The [v0.16.400 combination study](https://github.com/pearjelly/cliany.site/pull/136#issuecomment-6818924036)
preserved a provider connection failure after its earlier successful
preflight. A separately planned check on the same installed candidate later
stopped at strict live preflight: exit 1, `E_LLM_UNAVAILABLE`,
`transport_reason=tls_connection_closed`, local prerequisites ready and live
generation not ready. No model exploration started in the second study.

The nested check already advised inspecting the service address, proxy and
network. The top-level JSON hint instead told the caller to run the exact
preflight command again. Those are different instructions when the network
has not recovered.

A loopback fixture accepted the first TLS record and closed the connection
before any HTTP response. The installed combination wheel and patched
source used a fresh local Chromium CDP session and a dummy fixture key.
Both attempted one TLS handshake, exited 1 with the same error and transport
reason, and kept live generation blocked. The patched top-level hint
surfaced the network checks and stated that the failure does not establish
whether the key is valid. Offline tests also cover certificate verification,
DNS, refused connections, timeouts, HTTP 502 and authentication.

This is guidance for a blocked user, not provider recovery or a change to
retry policy. Neither failed live check is replaced, and no generated
adapter or independent first-use result is credited.
