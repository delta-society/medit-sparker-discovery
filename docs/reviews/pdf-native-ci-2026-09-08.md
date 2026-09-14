# Native PDF CI — 2026-09-08

이 문서는 0.5.0 후보의 **과거 검증 기록**이다. 아래 자동 PDF 생성 흐름과 테스트 수치는 해당 스냅샷에만 적용한다. 현재 PDF는 사용자 요청 시 생성하며, 동작과 검증 경계는 [PDF 내보내기](../pdf-export.md)를 따른다.

검증 스냅샷: `974b293`, 브랜치 `codex/pdf-native-ci-20260908`.
공유 작업 폴더의 브랜치·인덱스는 변경하지 않고 별도 스냅샷으로 실행했다. 운영 배포는 하지 않았다.

- 실제 PDF: https://github.com/delta-society/medit-sparker-discovery/actions/runs/34195156027
- 전체 호환성: https://github.com/delta-society/medit-sparker-discovery/actions/runs/34195156060
- Windows 2022 / macOS 15 / Ubuntu 24.04에서 설치된 Chrome으로 PDF 생성 통과.
- 배포 ZIP을 한글·공백 경로에 추출한 뒤 CLI new → finalize 자동 PDF → pdf 재사용 → 원본 해시 보존을 확인했다. 잘못된 Mermaid가 실패로 처리되는 실제 브라우저 검사도 통과했다.
- 전체 회귀: Ubuntu/Windows Python 3.9·3.13, macOS Python 3.13. 각 101개 helper 검사 중 96 통과, 5개 별도 브라우저 검사 생략. 별도 PDF CI가 실제 브라우저 smoke를 수행한다. AR 12개 및 Windows Git Bash·PowerShell smoke 통과.
- 최초 Windows/Python 3.13 실행에서 Camp 제출의 stat/fstat ctime 차이로 정상 파일을 변경 파일로 판단하는 결함을 발견했다. 각 API의 전후 전체 메타데이터와 API 간 파일 식별자·크기·mtime을 비교하도록 보완했다. ctime 의미 차이 회귀와 실제 변경 거절 검사를 모두 통과했다.

배포 준비 ZIP: `.sparker-discovery/native-ci-release/sparker-discovery-0.5.0.zip`.
SHA-256: `c85db89de6b1e44c39cfff98e38084c031834180eaebb980125aa2c68469361e`.

이 결과는 GitHub의 네이티브 OS 러너 검증이다. 참가자 개인 PC, 조직 보안 정책, Claude Code 실제 대화 전체, Camp PDF 업로드까지 검증한 것은 아니다. 당시 로컬 디자인 검증에 없었던 네이티브 OS 러너 증거를 보완하며, 이후 버전이나 참가자 실기기의 검증 상태를 갱신하지 않는다.

2026-09-14 기록 복구 시 GitHub에서 위 두 실행의 소스가 `974b293ef85e296c5d45f515701227217b838e69`이고 모든 PDF 3개·호환성 5개 작업이 성공한 것을 재확인했다. 새 PDF 실행이나 현재 배포본 인수 검증을 수행한 것은 아니다.
