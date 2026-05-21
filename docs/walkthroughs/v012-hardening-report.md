# v0.12.0 Stability Hardening Report

> **상태: 완료**  
> **날짜: 2026-05-21**

## 배경 (Background)

v0.11.0에서 Obscura 브라우저 제공자와 다중 플랫폼 바이너리 지원이 도입된 이후, 실제 사용 환경과 극한 상황에서 발생할 수 있는 여러 안정성 이슈가 확인되었습니다. 특히 P0/P1 등급의 보안 취약점과 동시성 제어 문제가 발견되어, v0.12.0에서는 기능 추가보다는 시스템의 견고함을 확보하는 데 집중하였습니다. 본 보고서는 발견된 7가지 주요 취약점에 대한 수정 사항과 현재의 안정성 상태를 기록합니다.

## 수정 목록 (Fixed Issues)

이번 릴리스에서 해결된 주요 안정성 및 보안 항목은 다음과 같습니다.

| ID | 항목 | 파일 및 위치 | Commit |
|---|---|---|---|
| **T03** | tar 경로 순회(Path Traversal) 보안 취약점 | `tui/screens/adapter_list.py` | `bbb13d6` |
| **T05** | PID 파일 원자적 쓰기 및 배타적 락 도입 | `binary/process.py` | `3924c00` |
| **T06** | Manifest 파일 동시 접근 제어(portalocker) | `loader.py` | `e903f44` |
| **T07** | 데이터 무결성을 위한 fsync 강제 호출 | `codegen/merger.py` | `9b236cd` |
| **T08** | Obscura 바이너리 다운로드 지수 백오프 재시도 | `commands/obscura.py` | `6e8c713` |
| **T09** | Session 및 Atomic IO 파일 락 체계 통일 | `session.py`, `atomic_io.py` | `74ee847` |
| **T10** | 예외 체인(raise from) 보존 및 로그 컨텍스트 강화 | `explorer/interactive.py` | `60a9b59` |

## 잔존 위험 (Residual Risks)

가이딩 작업을 통해 치명적인 문제는 해결되었으나, 기술 부채로 남아있는 하위 등급의 위험 요소는 다음과 같습니다.

- **P2: Any 타입 남용**: 일부 모듈에서 타입 힌트가 `Any`로 되어 있어 정적 분석 시 잠재적 오류를 놓칠 수 있음. (기록됨, 미수정)
- **P2: agent_md.py silent pass**: 특정 설정 파일 파싱 실패 시 경고 없이 넘어가는 구간이 존재함. (기록됨, 미수정)
- **성능 오버헤드**: `portalocker` 도입에 따른 파일 I/O 대기 시간이 미세하게 증가하였으나, CLI 도구 특성상 무시 가능한 수준으로 판단됨.

## 업그레이드 가이드 (Upgrade Guide)

v0.12.0은 하위 호환성을 완벽히 유지하도록 설계되었습니다.

- **무감 업그레이드**: 사용자는 기존 환경에서 `pip install --upgrade cliany-site`를 통해 즉시 업그레이드 가능합니다.
- **Breaking Changes 없음**: CLI 인터페이스나 JSON 출력 형식의 변경이 없으므로 기존 스크립트를 그대로 사용 가능합니다.
- **정리 불필요**: `~/.cliany-site/` 디렉터리의 데이터를 수동으로 삭제하거나 정리할 필요가 없습니다.

---
관련 상세 결정 사항은 [ADR-0007](../decisions/0007-v012-stability-hardening.md)에서 확인할 수 있습니다.
