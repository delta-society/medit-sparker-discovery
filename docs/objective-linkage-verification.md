# 목표 KPI·기록 우선 플러그인 검증 — 0.4.0

## 현재 범위

목표 KPI 정의·사람 확인·기능 인과 연결 → 기존 업무 앱 입출력 재사용 → KPI 관련 결과/근거 기록 → 구현 명세. 외부 전달처 지정은 선택이며 기본 record_only에서는 app/측정 담당 프로그램/전달처 확보 작업 없이 완성·확정 가능하다. KPI 미확정은 초안 유지. 미확인 앱은 획득 작업으로 설계 진행한다.

## 실행 증거 — 2026-09-08

- `python3 -m unittest discover -s plugin/tests -q`: 62 tests, 1.305s, OK.
- `claude plugin validate ./plugin`: Validation passed. 매니페스트 검사이며 실제 호스트 대화 검증이 아니다.
- `python3 scripts/build-package.py --output /Users/hermes/deliverables/sparker-discovery-plugin.zip`: exit0. ZIP 30 files, 81898 bytes, SHA-256 `a6f28f83c3c19079dea86687f6992ff6bc6bc642229aaabcab4c33c9af38fff9`.
- 최종 ZIP을 임시 폴더에 풀어 그 plan.py로 기존 익명 품질 사례 r000006을 읽고 objective/linkage와 record_only를 추가한 r000007 초안 저장·readback·Markdown export 실행. 결과 `ZIP_HELPER_SAVE_READBACK_OK`, `KPI_UNCONFIRMED_COMPLETE_BLOCKED`, `EXPORT_READBACK_OK`. 기존 리비전은 수정하지 않았다. 개인 실습 원문은 이 레포에 넣지 않는다.
- 회귀는 구버전 실제 fixture/Markdown 바이트 보존, 신규 계약 하향 방지, KPI 미확정/정의 변경 확인 무효화, 초안 허용, 일반 업무 결과 KPI, 미확인 앱 획득 작업, bound≠live, HTML/Markdown 이스케이프, record_only 무전달처 finalize와 기록 누락 차단을 포함한다. 테스트의 확인 발화·KPI·앱 매핑은 합성이며 실제 사용자 확정이나 성과 증거가 아니다.

## 수정 경로

`plugin/scripts/{plan,linkage,submission}.py`, `plugin/tests/test_linkage.py` 및 기존 제품/제출 회귀, `plugin/skills/plan/SKILL.md`, `plugin/references/{objective-linkage,conversation,data-contract,implementation-example}.md`, 매니페스트 0.4.0, 개발 명세와 사용 안내·검증 포인터. 과거 KPI 계산 도우미는 호환용 보존하며 새 운영 측정 프로그램을 만들지 않았다.

## 미검증/경계

실제 설치된 Claude Code에서 최종 ZIP의 시작→후속 보정→전체 확정까지 LLM 대화 재시험은 미실행. 앞선 공급자 HTTP402는 과거 경로의 제한이며 이번 ZIP의 실제 실패로 집계하지 않는다. 코딩 하위 작업은 600초 제한으로 종료됐고 상위 에이전트가 잔여 코드/문서·기록 우선 보정·시험·패키지를 직접 완결했다. 실제 Confluence/API/운영 프로그램 접속·게시·실행 데이터 수집·개별 KPI 확정·사용자 기기 설치/업데이트·Git push는 실행하지 않았다.
