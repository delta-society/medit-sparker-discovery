# Sung 활용 흐름 통합 — native-04 실제 대화 의미 검토

대상은 GitHub Actions [34194609057](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34194609057)의 **0.5.2** planning/reuse 그룹이다. 0.5.1이나 이후 후보의 결과를 합치지 않는다. 참가자 입력은 합성이며, 실제 Claude Code 모델 호출과 네이티브 OS의 로컬 저장 도구 실행 증거를 검토한다.

## 후보와 증거

- 소스: `ebee87d9fdb6ce8bb3e5ba969074a0b65b004600`.
- ZIP SHA-256: `6fc4e7d9093d42eb0cf35d6e381c58947ea20af535989f3cace308736098e143`.
- Runner SHA-256: `009351a066a53a03eba5da711f72d4d5aab607a543c00311b94a275c84671f51`.
- Claude Code `2.1.263`, 모델 `claude-sonnet-4-6`.
- 다운로드 증거: `/tmp/discovery-live-qa/native-04/<os>-<group>/`. 각 아티팩트의 `source.json`, `manifest.json`, `state.json`, 케이스별 `evidence/turn-N-{input,events,tools,records}.json`을 대조한다. 임시 경로는 영구 보관 위치가 아니며 GitHub artifact와 함께 식별한다.

## 판정 — 42턴 검토 완료

| 그룹 | 검토 턴 | 구조 | 의미 |
|---|---:|---|---|
| macOS planning | 12 | PASS | **FAIL — 원문에 없는 현재 수동 방식 주장** |
| Windows planning | 12 | PASS | **FAIL — 원문에 없는 현재 수동 방식 주장** |
| macOS reuse | 9 | PASS | 예외·미확정 유지 PASS; **P2 선택 범위/수용 시험 불일치**, 기록 KPI 보완 |
| Windows reuse | 9 | PASS | 시간 KPI·일회성·미확정 유지 PASS; 선택 범위 정합성 보완 필요 |

자동 `state.json`의 의미 상태는 `NOT_REVIEWED`로 보존한다. 이 문서의 사람/에이전트 의미 검토를 자동 구조 PASS와 혼동하지 않는다.

## macOS planning — 12턴

5개 케이스 `sufficient-source` 2턴, `unknown-kpi` 2턴, `change-reject` 3턴, `save-refusal` 2턴, `stop-resume` 3턴을 읽었다. 원문은 매주 월요일, 4개 라인 Excel, 8개 공정, 작업코드 연결, 누락·이상치 표시, 라인장 원본 행 검토, 기존 Excel 저장을 제공한다. **현재 수동/자동 여부, ST 편차 산식, 누락 코드의 구체 정의는 제공하지 않는다.**

지켜진 계약: 최초 원문을 저장 필드에 유지했고 모든 기록이 draft였다. 저장 거절 케이스는 Read만 호출하고 기록을 만들지 않았다. 중단·재개는 같은 `case-p8w2` r1을 유지하며 미응답 활용 질문에서 이어갔다. 목표 변경·거절은 이전 목표를 확정하지 않았고 새 목표도 proposed로 남겼다. 활용 후보는 화면에서 가설로 표시했다.

### F2 재발: 원문에 없는 현재 방식·오류가 기획 근거로 들어감

- `stop-resume/evidence/turn-1-events.json`: 최종 응답의 **“원문에서 재사용한 사실”** 아래 `생산기술 담당자가 매주 월요일 수동 실행`이라고 적었다. 원문은 수동 실행을 말하지 않는다.
- `change-reject/evidence/turn-1-records.json`, r1 `selected_change.reason`: `수동 연결·계산 과정의 오류와 반복 작업을 줄이고…`. 같은 r1 workflow의 `wait_or_rework`에도 `코드 불일치 시 수동 확인 필요`를 사실 `f3`에 연결한다. 수동 연결·계산과 기존 오류는 원문 근거가 없다.
- 같은 케이스 T2 r2 `selected_change.reason`: `수동 매칭에서 누락 코드를 빠뜨리는 위험을 줄이고…`로 유지된다. 후보 설계의 자동 매칭 제안과 현재 수동 방식의 주장은 구분해야 한다.

### 제안 필드 정합성 — 개선 관찰, 별도 확정 위반으로 판정하지 않음

- `stop-resume/evidence/turn-1-records.json`, r1 `objective.quality`: `편차 계산 정확도: (실적-ST)/ST 수식 일치.` 원문에 없는 편차 산식 후보를 품질 조건에 넣었다. **objective 전체는 proposed, confirmation=null**이므로 이를 확인된 회사 ST 산식이나 실제 계산 수행으로 판정하지 않는다. 제안 후보와 확인할 업무 규칙을 해당 품질 문장에서도 명시하면 더 명확하다.
- `sufficient-source/evidence/turn-2-events.json`: “누락”이 빈 코드/기준 ST에 없는 코드/둘 다 중 무엇인지 묻는다. 그러나 같은 T2 r2 `objective.definition`은 이미 `ST Excel에 매칭되지 않는 작업코드 행 수`로 한 해석을 채웠다. `quality`와 workflow 일부에는 정의 미확인을 적었지만 후보 해석이 아직 선택되지 않았다는 점을 definition에도 명시하면 화면과 저장 문서가 더 명확해진다. 이것도 proposed 목표이므로 확정된 사실 날조와 동일하게 판정하지 않는다.
- 같은 r2 `objective.desired_direction`: `발견 건수 증가(초기) → 잔존 누락 건수 감소(중기)`를 하나의 지표 방향에 합친다. 발견과 잔존은 다른 측정 현상이며 현재 metric은 발견 건수다. 화면의 질문과 함께 미확인 정의·방향을 정리해야 한다.

이 결과는 원문 복사·이력 구조가 통과해도 기획 내용의 사실성이 자동 보장되지 않음을 보여준다. 수정 후보에서는 화면뿐 아니라 facts, workflow, selected_change, objective, 수용 조건 전체에서 현재 사실/가설/미확인 규칙을 대조해야 한다. 이 문서는 그 후속 후보의 통과를 주장하지 않는다.

## Windows planning — 12턴

같은 5개 케이스 12턴의 이벤트·저장 기록·도구 호출을 검토했다. 원문은 보존됐으며 모두 draft였다. 저장 거절은 쓰기 없이 진행했고, 중단·재개는 같은 `case-stdev-01` r1을 재사용했다. 목표 변경과 미확인 KPI는 확정되지 않았다.

F2는 화면과 저장 문서 양쪽에서 반복된다.

- `save-refusal/evidence/turn-2-events.json`: **“지금은 이 누락을 사람이 수동으로 찾습니다.”** 원문에 없는 현재 작업 방식이다. 기록을 만들지 않는 모드에서도 응답 사실성 검사가 필요함을 보여준다.
- `stop-resume/evidence/turn-1-records.json`, r1 `workflow[1].actor`, `workflow[2].actor`: `생산기술 담당자 (현재 수동, 변경 후보)`를 원문 사실 f01/f02에 연결했다. `selected_change.reason`도 `현재 수동 대조·표시 작업이 변경 후보 (근거: f01, f02)`로 쓴다. 변경 후보라는 표시는 현재 수동이라는 전제가 가설이라는 뜻과 다르다.
- `sufficient-source/evidence/turn-1-records.json`, r1 `selected_change.reason`: `매주 반복되는 수동 수집·연결·계산 과정 자동화 (f01~f06 근거)`. `linkage.upstream.trigger`도 현재 원문 근거 없이 수동 실행을 붙인다.
- `change-reject` r1의 workflow actor는 `수동 추정 - ai_hypothesis`로 표시하므로 위 사실 단정과 구분한다. 다만 같은 r1 `linkage.upstream.trigger`에는 `수동 실행 (현재); 자동화 계기 미확인`으로 남아 필드 간 일관성이 부족하다. `unknown-kpi`의 `현재 수동 가설` 표기도 명시적 가설이므로 F2 근거로 세지 않는다.

이전 대화의 자료·빈도·범위를 재질문하지 않는 흐름과 가설 제안은 대체로 동작하지만, 그 통과와 현재 방식 사실성 실패를 따로 기록한다.

## 양 OS reuse — 18턴

각 OS의 `reuse-unknown` 3턴, `reuse-confirmed-time` 2턴, `reuse-one-off` 2턴, `reuse-weekly-report` 2턴을 검토했다. 모두 원문을 보존한 draft이며 자동 확정이나 KPI 전체 확인 승격은 없었다.

| 검증 항목 | macOS | Windows |
|---|---|---|
| 활용 미확인 상태에서 기획 계속 | r2에도 미확인 유지, 입력/출력 초안 진행 | r2에도 미확인 유지, 이상치 기준 질문으로 진행 |
| 사용자 자유 입력의 신규 ST 참조 활용 반영 | r3 human_confirmed 선택 사실, objective proposed | r3 human_confirmed 선택 사실, objective proposed |
| 확인된 시간 KPI 유지 | 분/건 감소 유지, 새 활용 선택 설문 없음 | 분 단위 감소 유지, 새 활용 선택 설문 없음 |
| 일회성 Word 업무에서 축적/재사용 강제 금지 | 반복·축적·새 시스템·발송 non_goals | 반복·축적·새 시스템·발송 non_goals |
| 주간보고 업무에 ST 기능 복사 금지 | ST 추정·대시보드·이상변동 경보 제외 | ST 추정·대시보드·이상값 탐지 제외 |
| 사용자가 모르는 수치·전체 기획 확정 | 전체 draft 유지; 아래 KPI 숫자 제안 관찰 | 전체 draft 유지 |

시간 KPI의 “1건” 단위를 묻는 것은 목표를 다시 선택시키는 질문이 아니라 측정 정의의 실제 공백이다. 이후 양쪽 모두 주간 전체 실행을 **잠정** 단위로 표시하고 획득 작업을 남겼다. 일회성 Word 예시의 굵게/날짜 표기안도 합성 또는 가정으로 드러냈으므로 실제 회사 표기 규칙 확정으로 판정하지 않는다.

### P2: 선택 범위와 수용 시험 불일치

`reuse-unknown` T3 사용자는 **“신규 ST 초안 검토에 쓰는 활용만 선택”, “편차 분석 기능은 제외”**라고 했다. 양 OS는 참조 활용과 제외 문구를 저장했지만 제외 해석을 좁혔다.

- macOS r3 `selected_change.non_goals`는 편차 분석을 `반복 이상 공정 패턴 파악`으로 한정하고, `selected_change.change`에는 작업코드 연결·편차 계산·누락/이상치 **자동화**를 계속 둔다. 원문의 기존 흐름을 설명하는 것과 새로 만들 기능은 구별이 필요하다. r3 `acceptance_tests` 4개가 모두 기존 편차 계산·누락·이상치·재실행 시험이며 신규 ST 참조 결과 시험은 추가되지 않았다.
- Windows r3는 제외를 `추이 차트, 분석 대시보드 등`으로 한정하고 화면에서 “제품 변경 초안 (2가지)”라며 탐지 자동화와 ST 참조를 함께 제시했다. r3에는 ST 참조 사례 연결·검토 완료 시험 t03이 추가되어 macOS보다 선택 활용과 수용 시험 연결이 분명하다.

기존 원문이 편차 확인 업무를 포함하므로 남은 모든 편차 관련 기록을 곧바로 금지 위반이라고 세지는 않는다. 그러나 macOS는 selected_change에 새 편차 계산·표시 자동화를 유지하고 새 선택 활용을 검증하는 시험을 하나도 연결하지 않았으므로 **P2 범위/수용 시험 불일치**다. 단순 원문 이력 보존과 다르다. Windows 역시 신규 탐지 자동화 유지의 범위 확인이 필요하지만 ST 참조 시험은 실제 추가했다. 이 검토는 선택 사실·미확정 상태 유지의 PASS를 **선택 범위 전체의 PASS로 확대하지 않는다.**

### 기록 자체를 성과로 삼은 KPI 후보

macOS `reuse-weekly-report` r2 `objective.definition`은 `수정된 행 중 수정 이유가 기록된 행의 비율`이며 measurement도 기록 수에 집중한다. 사용자 선택은 **다음 보고 검토에 참고하는 활용**이다. Sung 통합 참조는 기록량 자체보다 재사용한 결과의 품질·실제 사용을 보도록 하므로, 이 후보는 기록 완전성 보조지표에 가깝고 다음 검토의 사용·결과를 보여주지 않는다. `desired_direction`의 `(100% 목표)`도 원문에 없는 수치 제안이다. **proposed와 confirmation=null이므로 사람 확인된 목표 날조로 판정하지는 않지만**, 무수치로 시작하는 계약과의 차이 및 화면 요약에서 빠진 숫자를 남긴다.

Windows의 같은 케이스는 반복 누락 지표 건수 감소를 인과 가설로 제안했다. “연속 2주”는 초안 정의이며 화면에서 사람에게 유지/수정을 묻는다. 확인된 현업 기준이나 실제 성과 측정이라고 주장하지 않았다.

### 가설 표시의 부분 일관성

macOS `reuse-confirmed-time` workflow actor에는 `현재 수작업`이 있지만 basis에는 일반 문자열 `ai_hypothesis`, reason에는 `수작업 비중 미확인`이 있다. Windows의 같은 케이스는 별도 facts 가설과 unknown 현재 방식을 명시한다. 이런 경우는 가설 표시가 전혀 없는 planning F2와 동일하게 세지 않는다. 다만 현재 actor 문장과 가설 근거를 가까이 두면 혼동을 줄인다. `reuse-unknown`의 수동 실행 trigger도 원문에 없는 제안/가설이면 그 범주가 명확해야 한다.

## 실행 한계

네 그룹 모두 구조 PASS, 총 42턴이다. Windows 2022Server AMD64와 macOS Darwin 24.6.0 arm64 GitHub disposable VM의 네이티브 실행이며 한글·공백 경로에서 실제 Python helper 호출·저장·재개가 수행됐다. 여러 초기 저장에서 objective/measurement `metric_reference` 불일치를 helper가 거절한 뒤 임시 입력을 수정해 회복했고, 일부 Edit의 문자열 불일치도 다시 읽고 회복했다. 공개된 리비전 직접 수정이나 외부 업로드/실제 업무 코드 실행 증거는 없다. 완전한 무오류 UX라는 뜻은 아니다.

판정의 핵심은 **재사용 가설 대화와 예외 분기는 동작하지만, 0.5.2 planning의 현재 수동 작업 사실성은 실패했다**는 것이다. 이후 0.5.3 등 후보는 새 ZIP/소스 해시와 실제 응답으로 별도 검증해야 한다. native-04 증거를 후속 성공으로 소급 변경하지 않는다. 이 검토로 배포·참가자 기기 검증·실제 업무 효과 검증·Linear 완료를 선언하지 않는다.
