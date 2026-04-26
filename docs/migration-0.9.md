# cliany-site 0.9.0 마이그레이션 가이드

## 개요

0.9.0은 **하드 전환 버전**입니다. 이전 버전에서 생성된 adapter는 자동으로 로드 거부됩니다.

## 필수 조치

### 1. 구 adapter 확인
```bash
cliany-site list --legacy --json
```

### 2. 구 adapter 재생성
```bash
# 각 도메인에 대해 재실행
cliany-site explore "https://example.com" "기존 워크플로 설명" --json
```

### 3. 새 adapter 검증
```bash
cliany-site verify example.com --json
```

## AGENT.md 자동 생성

0.9.0부터 `cliany-site explore` 성공 시 `./AGENT.md`가 자동으로 갱신됩니다.

```bash
# AGENT.md 상태 확인
cliany-site doctor --json | jq '.data.checks[] | select(.name=="agent_md")'
```

## 트러블슈팅

### "LegacyMetadataError: adapter needs re-generation"
구 adapter → 재생성 필요. `cliany-site explore <url> "<workflow>"` 실행.

### "schema_version=2 required"
metadata.json의 schema_version이 정수 2가 아님. 재생성.

### AGENT.md 충돌
```bash
CLIANY_NO_AGENT_MD=1 cliany-site explore ...  # AGENT.md 자동 갱신 억제
```
