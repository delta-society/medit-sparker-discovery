# 기존 제출 선반영 검증 — 0.2.2

sung의 Slack 실험에서 원문에 있는 시간과 측정 계기를 반복 질문했고, 메뉴의 짧은 이름으로 업무 범위를 좁힌 문제를 수정했다. SPEC S3의 후속 요청이며 기존 참가자 기록·계산·확정 계약은 바꾸지 않는다.

구현: `plugin/skills/plan/SKILL.md`와 `plugin/references/conversation.md`에서 첫 질문 전 원문 로딩·선반영 및 질문 후보 대조를 요구한다. 번들 원문 로딩은 `plugin/scripts/submission.py`가 담당한다. ST의 공정 단위·라인 구성 계기·단순/복잡 소요 시간·범위·자료 위치를 재사용하고, 비율·주기·산식의 미확인을 0이나 통상값으로 채우지 않는다. 일반 업무를 임의로 ST 번들로 대체하지 않는다.

검증:
- 단위 회귀 44 tests PASS, Claude manifest PASS. 신규 5개는 ST 선반영·ZIP 경로·다른 예시 구분·허용 이름·변경된 원문 거부를 검사한다.
- 문구만 보강한 초기 후보는 실제 대화에서 시간의 현재/목표 재질문과 미확인 비율 0% 추정이 나와 미통과로 남겼다. 경로 추측·권한 거절도 관찰됐다. 영수증: `/Users/Shared/DeltaSocietyOS/audit/sparker-source-first-20260908/`.
- 읽기 전용 도우미 추가 후 최종 ZIP의 실제 Claude Code 2턴에서 원문 도우미 호출·범위/공정 단위/라인 구성 계기/단순4h·복잡8h/엑셀 위치의 선반영을 확인했다. 첫 질문은 미확인 검토 기준, 다음 질문은 원문에 없는 검토자 시간 포함 범위였다. 기존 시간 수치·측정 계기·이미 답한 완료 기준을 다시 요구하지 않았고 미확인 비율 0% 추정도 사라졌다. 구조 검사 PASS, 두 최종 답변의 해당 질문 의미 대조 완료. 영수증: `/Users/Shared/DeltaSocietyOS/audit/sparker-source-first-retry-20260908/verification.json`.
- 도우미 추가 후 첫 실행은 API mid-response 서버 오류로 중단됐으며 성공으로 세지 않았다(`sparker-source-first-final-20260908`). 같은 ZIP으로 새 세션에서 재시도해 위 결과를 얻었다.
- ZIP SHA256: `13dae930e284908e75aa439965dc1d283d23aef2f9f5e02c9a48e8fb473e64ed`.

재현: ZIP을 새 Claude Code 세션에서 로드해 `/sparker-discovery:plan 예시 standard-time으로 KPI 설정을 실험하자. 파일 저장은 하지 마.`로 시작한다. 원문 도우미 실제 호출·초기 사실·질문을 검사한다. 이후 엑셀 정리/단위/수식이 시간 집중 구간이고 검토자 승인이 완료이며 엑셀과 기준 문서가 있고 확보 시간을 갱신에 쓰겠다는 답을 준다. 원문 시간·측정 계기·이미 답한 완료 기준을 재질문하지 않는지 확인한다. 원문에 없는 정기 주기와 실적을 확정하지 않아야 한다.

이번은 ST 예시의 질문 흐름과 원문 재사용 검증이다. 일반 제출 전수 대화·실제 참가자 성과·저장 전체 재시험으로 확대하지 않는다. 기존 저장·계산 시험 이력은 `kpi-verification.md`, 혼합 질문은 `mixed-question-verification.md`를 따른다.
