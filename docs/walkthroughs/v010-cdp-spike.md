# T01 스파이크: CDP Network/Console 가용성 검증

**날짜:** 2026-05-07  
**태스크:** T01 — Spike CDP Network/Console 경유 browser_use 가용성 검증  
**결론:** **방안 A 채택**

---

## 탐색 목표

browser_use BrowserSession 을 통해 CDP `Network.enable` / `Console.enable` 을
호출할 수 있는지 확인. 불가능하면 방안 B(aiohttp WebSocket 직접 접속) 준비.

---

## 방안 A — browser_use BrowserSession + cdp_use CDPClient

### 탐색 과정

1. `browser_use.browser.session.BrowserSession` 소스 확인
   - `_cdp_client_root: CDPClient | None` private attr 존재
   - `cdp_client` property 가 이를 노출: `BrowserSession.cdp_client → CDPClient`

2. `cdp_use` 패키지 구조 확인
   - `CDPClient.send` → `CDPLibrary` (domain-specific async methods)
   - `CDPLibrary.Network` → `NetworkClient` (`enable`, `disable`, cookie methods 등)
   - `CDPLibrary.Console` → `ConsoleClient` (`enable`, `disable`, `clearMessages`)

3. 실제 사용 패턴 확인 (`browser_use/browser/session.py:1477`)
   ```python
   await cdp_session.cdp_client.send.Network.enable(session_id=cdp_session.session_id)
   ```

### 검증된 API

```python
# Network 도메인 활성화
await browser_session.cdp_client.send.Network.enable(session_id=session_id)

# Console 도메인 활성화
await browser_session.cdp_client.send.Console.enable(session_id=session_id)

# 이벤트 핸들러 등록 (향후 T15/T16 에서 사용)
browser_session.cdp_client.register.Network.requestWillBeSent(handler)
browser_session.cdp_client.register.Console.messageAdded(handler)
```

### 결론

방안 A 완전히 유효. `BrowserSession` 연결 후 `cdp_client` 에서 직접 CDP 도메인
커맨드를 보낼 수 있다.

---

## 방안 B — aiohttp WebSocket 직접 접속 (불채택)

`ws://localhost:9222/devtools/page/{targetId}` 에 직접 연결하는 방안.  
browser_use 의 세션 관리, 이벤트 버스, 세션 풀과 충돌할 수 있음.  
방안 A 가 유효하므로 불필요. 구현 생략.

---

## 구현 결과

`src/cliany_site/browser/cdp.py` 에 두 함수 추가:

```python
async def enable_network_capture(browser_session, *, session_id=None) -> None:
    await browser_session.cdp_client.send.Network.enable(session_id=session_id)

async def enable_console_capture(browser_session, *, session_id=None) -> None:
    await browser_session.cdp_client.send.Console.enable(session_id=session_id)
```

테스트: `tests/test_cdp_capabilities.py` — 10개 테스트 전부 PASS (Chrome 없이 mock 기반).

---

## 하위 태스크 영향

| 태스크 | 경로 | 비고 |
|--------|------|------|
| T15 | Network intercept | `enable_network_capture` + `register.Network.*` 사용 |
| T16 | Console log capture | `enable_console_capture` + `register.Console.messageAdded` 사용 |
| T18 | HAR 기록 | `Network.requestWillBeSent` + `Network.responseReceived` 이벤트 누적 |
