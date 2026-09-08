# 목표 KPI·업무 앱 연결 계약 — 0.4.0

## 순서와 책임

1. 제출 업무는 **변경 후보**다. 원문과 기존 목표를 먼저 회수한다. 제공된 로컬 문서·대화만 읽고 외부 앱에 접속하지 않는다. 기존 목표가 있으면 출처와 정의를 재사용한다. 없으면 업무 결과에서 KPI·품질·단위·출처·원하는 방향과 `변경 → 사람 행동/유효 결과 → 목표 KPI` 인과 가설을 먼저 제안한다. 병목/작업시간 하나로 목적을 대체하지 않는다. 납기 준수, 재발, 품질 통과, 유효 갱신, 회수 결과 등 일반 업무 결과도 가능하며 노동시간 분모를 강제하지 않는다.
2. 참가자가 KPI를 모르면 후보를 업무 말로 설명하고 선택/수정/기타/아직 모름을 묻는다. 숫자 목표·현재값은 발명하지 않는다. KPI의 정의(필요하면 산식), 유효 품질, 단위, 측정 출처, 변화 방향 및 인과 가설을 보여준 뒤 실제 사람 확인을 받는다. 선택 미결은 proposed/unknown 초안이다. 입력·출력·시험 설계는 계속한다. 정의 미확정 때문에 모든 설계를 중단하지 않으며 finalize만 보류한다.
3. **기존 업무 앱의 입력·계기·출력 면을 먼저 재사용**한다. 어떤 원천 레코드가 어떤 이벤트로 시작되는지, 결과는 어느 업무 레코드/필드/상태에 돌아가고 누가 무엇을 하는지 제안한다. 새 입력 폼·대시보드·파일 다운로드 제품을 기본값으로 만들지 않는다. 새 표면이 정말 필요하면 기존 기능 검토와 예외 이유를 명시한다. 특정 앱(Confluence 포함)을 모든 사례 기본값으로 고정하지 않는다. 로컬 plan.md는 기획 기록이지 새 업무 제품 UI가 아니다.
4. 회사 정합성 판정과 실제 측정 운영은 외부 프로그램의 책임이다. **플러그인은 KPI와 외부 프로그램의 연결을 설계할 책임이 있다.** 입력/출력 계약과 같은 사례 ID를 측정 이벤트·지표 참조에 매핑한다. 원천 자료 접근, 자동 게시, MCP/계정/비밀값/런타임 변경은 실행하지 않는다. API명·필드 존재·권한·연동 가능성을 추측으로 확정하지 않는다.
5. 미확인 앱/레코드/필드/API는 unknown 또는 draft로 두고 기존 `acquisition_tasks`의 담당 후보·획득 방법·완료 조건에 연결한다. 정상 이벤트→기존 결과 레코드→측정 이벤트, 중복 재실행, 원천 누락/권한 실패→성공 상태/성과 이벤트를 만들지 않음의 수용 시험을 설계한다. 실행 결과나 운영 준비 판정이 아니다.
6. 확정 전 목표·연동·기술 규칙·정상/예외 시험 전체를 보여주고 최종 확인한다. 미확정 KPI는 완성/확정 불가. 사람이 확인한 KPI와 연동 획득 작업이 있으면 앱 바인딩이 미확인이어도 **미결 연결을 포함한 계획**으로 확정할 수 있다. 이것은 구현 착수/외부 발신 승인이 아니다.

## 기록 우선 보정 — 외부 전달은 선택

최신 사용자 보정: “어디로 넘길지 보다는 기록해두는게 좋은것 같아.” 위 외부 측정 연결은 선택 사항으로 좁힌다. KPI 정의/확인, 기능 인과 관계, 기존 업무 앱 입출력 재사용은 유지한다. 목적은 기획서에 KPI·기능·기록할 결과/근거·관측과 추정·실패/수정 이력을 연결해 남기는 것이다. 이 플러그인이 운영 관측값을 자동 수집한 것은 아니다.

기본 `linkage.measurement.status=record_only`. 호환 필드 이름은 유지한다. `metric_reference`는 목표 KPI 참조, `event_mapping`은 언제 무엇을 기록하는지, `record_mapping`은 업무/실행 ID와 결과/근거의 대응, `dedupe`는 중복 방지/수정 이력, `failure`는 미확인/실패 보존, `basis`는 기록 설계 근거다. complete 시 이 문자열들은 필요하지만 app, objective.measurement_owner, 외부 전달처 획득 작업은 필요 없다. 초기 초안은 빈칸 가능. 어디로 넘길지 질문으로 대화를 되돌리지 않는다. 전달을 실제 설계하는 경우만 기존 unknown/draft/bound 계약을 선택한다. record_only는 입력/출력 앱 상태로 사용할 수 없다.

## 저장 API

신규는 `plan.py template --linked` / Python `plan.template(linked=True)`.
`planning_scope: product`와 **`planning_contract: objective-linkage-v1`**를 함께 사용한다.
0.3 `template --product` 및 기본 template, 계약 표식 없는 모든 과거 저장 JSON/Markdown은 기존 동작으로 보존한다. 기존 확정본은 reopen 후 새 리비전에서만 계약을 추가한다. 최초 submission은 그대로 보존한다. 새 계약을 사용한 뒤 update에서 표식을 제거하는 하향 전환은 거부한다.

`objective`:
- 문자열: `outcome`, `metric_reference`, `definition`, `quality`, `unit`, `source`, `desired_direction`, `causal_relation`, `alignment_owner`, `measurement_owner`.
- `metric_reference`는 기존 지표 ID/문서 참조. 아직 등록 전이면 **제안된 로컬 참조**임을 표시해 외부 등록 ID처럼 쓰지 않는다. source는 현재값이 아니라 측정 출처의 정의이며 미확인 실제 필드 확보는 작업으로 남긴다.
- `status`: `unknown | proposed | human_confirmed`; `acquisition_ids`: 기존 작업 ID 목록.
- `confirmation`: 미확정은 null. 확인 시 `{actor:"human", quote:<실제 발화>, explicit:true, definition_sha256:<정의 해시>}`. 해시는 `linkage.objective_digest(objective)`로 계산한다(스크립트 디렉터리를 import 경로로). 위 문자열 10개가 확인 대상이며 하나라도 변경하면 다시 확인해야 한다. 도우미는 발화 진위를 인증하지 않는다.
- 수치 목표/기준선/생산력 계산 필드는 추가하지 않는다. 실제 숫자 목표가 제공되면 출처와 함께 원문에 보존하고 외부 측정 프로그램에 맡긴다.

`linkage`:
- `surface_strategy`: 초기 `""`, `reuse_existing`, 또는 `new_surface_exception`.
- `reuse_basis`: 기존 기능 재사용 근거 또는 새 표면 예외 이유.
- `upstream`: `app`, `record_id`, `trigger`, `fields`.
- `downstream`: `app`, `record_mapping`, `fields`, `status_mapping`, `dedupe`, `failure`.
- `measurement`: `app`, `metric_reference`, `event_mapping`, `record_mapping`, `dedupe`, `failure`.
- 각 연결 객체는 위 문자열에 `status: unknown | draft | bound` (measurement에만 기본 `record_only` 추가), `basis` 문자열, `acquisition_ids` 목록을 더한다. fields/매핑은 소스→대상 이름과 변환 규칙을 서술한 문자열(임의 API 스키마 객체 아님). trigger/event_mapping에는 발생 조건·원천 이벤트·측정 이벤트·필드/업무 ID 대응을 적는다.
- `bound`는 모든 계약 문자열과 근거가 채워진 **문서상 바인딩**. live/verified 운영 상태는 지원하지 않는다. `unknown/draft`는 부분 문자열/빈칸 허용; complete 시 최소 하나의 유효 획득 작업 참조 필요. 각 작업에 미결 필드·권한·매핑을 구체적으로 적는다. 측정 참조가 있으면 objective 참조와 일치해야 한다.

초기 template는 그 상태로 validate/new/show 가능하다. 문자열을 미리 전부 채우지 않는다. `validate --complete`는 기존 제품 완성 요건 + 사람 확인된 objective + 표면 전략/근거 + 입력/출력의 bound 또는 획득 작업, 그리고 기본 KPI 기록 계약(선택적 외부 전달은 bound 또는 획득 작업)을 요구한다. 단순 문자열 검사는 내용의 진실성·인과 타당성·API 준비를 증명하지 않는다.

최종 확인의 `scopes`는 `["user_result", "selected_change", "acceptance_tests", "objective", "linkage"]`. 목표 확인과 전체 계획 확정은 서로 다르다. 기존 3개 scope는 레거시에만 유효하다. new/update/save/show/resume/history/reopen/finalize/export의 기존 CLI는 변경하지 않는다. 새 Markdown은 목표·방향·인과 가설·연결 매핑/미결·획득 작업을 포함하고 구버전 렌더러는 변경하지 않는다.

## 대화 수용 기준

- 알려진 KPI 없는 시작: KPI를 먼저 제안하고 아직 모름 답이면 초안 유지, 나머지 설계 진행, 가짜 확인 없이 finalize 보류.
- 업무 결과 KPI를 선택해도 총 사람시간 입력을 요구하지 않음. 자유 답변으로 정의를 바꾸면 기존 KPI 확인 해시가 무효.
- 앱 불명: 입력 폼/다운로드를 바로 확정하지 않고 기존 앱 후보·획득 작업과 unknown 계약. 앱 계약 자료 제공 후에만 bound; API 접속 성공이라고 말하지 않음.
- 원문→목표→기존 앱→대표 한 건→이벤트 연결/중복/실패 시험이 같은 ID를 사용. KPI 질문 턴은 AR/ST 금액 예시 stdout 전용 규칙보다 우선하며 계산 예시는 별도 턴에서 기존 도우미 계약대로 실행.
