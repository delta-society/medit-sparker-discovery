# Onboarding / Week 1 검증 — 2026-09-08

검증 환경: Claude Code 2.1.263, Linux, Haiku 4.5 (`claude-haiku-4-5-20251001`). 개인 설정·MCP를 제외한 임시 실습 폴더와 합성 업무를 사용했다. 대화 출력과 실제 생성 파일을 구분해 확인했다.

| 시나리오 | 관측 결과 |
|---|---|
| Skill 만들기 | 실습 폴더 `.claude/skills/sparker-practice/SKILL.md` 실제 생성 |
| 만든 Skill 호출 | 월요일 할 일 수집·금요일 결과 정리 입력을 표로 출력. 자료·완료 기준은 미확인 |
| 온보딩, 기존 제출, 저장 거절 | 주간보고 취합 원문만 재사용하고 대화 체험 안내. 파일 생성 없음 |
| MCP 미연결·회사 계정 연결 불가 | 미연결을 인정하고 도구/자료/결과 설계 체험. 설치·연결 성공 주장 없음 |
| 초안 기획서 제출 준비 | week 1, revision 1, draft 유지, 기획서만 포함한 ZIP 실제 생성. 앱 업로드 남음 표시 |
| PDF 건너뛰기·원본 제외 | PDF와 세션 원본을 생성/포함하지 않음 |

제출 ZIP은 별도 `camp_submit.py inspect`로 검증했다. 1,608 bytes, SHA-256 `d525b13c30db21b9bb3452af8a3b6aa6853300a6815268416b3df0301209e3fa`, 상태 `prepared_locally_not_submitted`. 참가자 앱이나 Slack에 실제 전송하지 않았다.

실행에서 발견한 교정: Haiku가 상대 교안 경로를 cwd에서 찾던 문제를 `${CLAUDE_PLUGIN_ROOT}`로 보완했다. 연습 스킬에 명시적 인수 전달과 기존 입력 재사용 규칙을 추가했다. 온보딩 예문에 없는 요일·담당자를 보충하지 않도록 수정했다. 이미 답한 Slack 두 항목을 반복 질문하지 않도록 조건을 명확히 했다.

로컬 회귀: 101 tests, 96 passed / 5 환경 skip. 두 신규 스킬의 frontmatter 검증과 Claude 플러그인 manifest 검증 통과. 패키지 테스트는 신규 진입점·교안이 배포 묶음에 포함되는지 함께 검사한다.

한계: 실제 회사 MCP 인증·실습 PC의 Claude 대화·Teams/Hook 설정·앱 업로드·Slack 게시·전체 수업 시간 리허설은 이 검증에 포함하지 않는다. Windows/macOS는 PR의 기존 native compatibility CI에서 helper와 배포 패키지를 검증한다.
