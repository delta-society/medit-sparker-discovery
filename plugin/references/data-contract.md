# 저장 도우미 계약 (Python 3.9+ / 표준 라이브러리)

> 최신 기록 우선 보정: KPI·기능 인과 관계와 결과/근거 기록은 남기되 외부 전달처 선택은 필수가 아니다. `record_only`가 기본이며 app/측정 담당 프로그램 미지정으로 확정을 막지 않는다. 기존 업무 앱 입출력 재사용은 유지한다. 상세와 이전 측정 연결 문구의 적용 경계는 `objective-linkage.md` 「기록 우선 보정」을 따른다.

이 도우미는 업무 분류나 AI 응답을 만들지 않는다. Claude가 대화에서 계획을 작성하며 도우미는 구조 검사·불변 저장·한국어 Markdown 내보내기만 한다. 인터넷·인증 정보·소스 연결을 사용하지 않는다.

## 실행

`<PLUGIN>`은 현재 로드된 SKILL.md에서 두 단계 상위의 절대 경로다. POSIX 예시이며 Windows는 `python3` 대신 `py -3`과 사용자의 절대 경로를 쓴다. 인수/제출 원문을 셸에 직접 붙이지 않는다. JSON은 Claude의 파일 작성 도구로 안전한 새 파일에 쓴다.

```sh
python3 "<PLUGIN>/scripts/plan.py" --help
python3 "<PLUGIN>/scripts/plan.py" template --linked
python3 "<PLUGIN>/scripts/plan.py" validate --input "<새 plan 입력.json>"
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" new case-abc --input "<새 plan 입력.json>"
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" show case-abc
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" history case-abc
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" resume case-abc
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" update case-abc --expected-revision 1 --reason "사용자가 보정한 내용과 실제 이유" --input "<새 plan 입력.json>"
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" reject case-abc --expected-revision 2 --candidate candidate-a --reason "실제 사용자 거절 이유"
```

`save`는 `update`의 별칭이다. new 외의 모든 변경은 최신 리비전과 이유를 요구한다(확정은 이유 대신 확인 파일). 초안에서도 JSON 타입/원문/참조/입력 획득 작업 구조는 검사한다. 빈 완성 항목을 남긴 초안 저장은 허용하지만 `--complete`/finalize는 거부한다.

```sh
python3 "<PLUGIN>/scripts/plan.py" validate --complete --input "<최종 초안 plan.json>"
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" finalize case-abc --expected-revision 4 --confirmation "<실제 확인.json>"
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" export case-abc --output "<존재하지 않는 인계 파일.md>"
python3 "<PLUGIN>/scripts/plan.py" --root "<승인한 로컬 폴더>" reopen case-abc --expected-revision 5 --reason "사용자의 수정 요청 원문"
```

`show`/`resume`은 JSON record를 반환한다. 재편집 입력은 **record.plan 객체만**이다. 출력에는 revision, status, plan_sha256이 있으므로 읽어 사용하고 숫자를 추측하지 않는다.

## plan 필드

신규/수정은 `template --linked`: `planning_scope: product` + `planning_contract: objective-linkage-v1` + `objective` + `linkage`다. 필드/상태/확인 해시 계약은 [objective-linkage.md](objective-linkage.md)를 따른다. 초기 미확인 template는 초안 저장 가능하다. 기본 template와 `--product`는 과거 API/JSON/Markdown 호환을 유지한다. baseline/comparison/옛 kpi 계산은 신규 요구가 아니며 기존 기록에서만 보존한다. 알 수 없는 키/계약은 거부한다.

| 필드 | 구조·의미 |
|---|---|
| submission | `{text, source}` 최초 제출 원문/출처. 생성 후 불변. 잘못된 원문도 덮어쓰지 말고 facts에서 정정한다. |
| facts | `[{id,text,source,kind}]`. kind: `submitted`(제공된 자기보고/자료), `human_confirmed`(실제 발화 근거), `ai_hypothesis`. source에 실제 원문 위치나 대화 발화를 적는다. |
| user_result | `{user,result,use_when}` 결과 사용자 역할·결과·사용 시점. 모르면 가설이라고 명시한다. |
| workflow | `[{step,actor,input,output,wait_or_rework,basis}]`. actor에는 담당 역할만 적고 수행 방식을 섞지 않는다. basis에 사실 ID/AI 가설 여부를 적는다. 원문에 없는 수행 방식·출력·대기 상태는 현행 사실이 아니다. 대기 정보가 없으면 wait_or_rework는 미확인이다. 대기 없음과 미확인을 구분한다. |
| bottlenecks | `[{id,claim,evidence:[fact-ID],counterevidence:[반증 신호],status}]`. status: `hypothesis`, `human_confirmed`, `rejected`. AI 가설 근거도 사실 목록에 가설로 남긴다. 근거 부재를 숨기지 않는다. |
| selected_change | `{candidate_id,change,reason,non_goals:[...]}`. 제품 모드에서는 주어진 목표로 바로 기획하며 candidate_id=null과 빈 후보 목록을 허용한다. 레거시 모드만 확정 전 candidate_id 필요. 병목 가설이 입증되지 않아도 탐색용 변경을 선택할 수 있다. |
| responsibilities | `{ai:[...],code:[...],human:[...]}`. 하지 않는 역할은 이유와 “사용하지 않음”을 명시한다. |
| acquisition_tasks | `[{id,what,owner,method,done_when}]`. 담당 미확정이면 “담당 후보(확인 필요)”와 배정 방법을 적는다. |
| inputs | `[{name,source,access,acquisition_id}]`. access는 `user_reported`, `verified`, `unknown`, `missing`. 사람에게 접근이 있다는 말이 도구 연결/자동 접근 검증을 뜻하지 않는다. unknown/missing에는 실제 획득 작업 ID 필수. 이미 접근 가능하면 acquisition_id는 null 가능. |
| quality_conditions | `[구체적인 품질 조건]` |
| acceptance_tests | `[{id,type,input,steps:[...],expected,pass_condition,runner}]`. type `normal`/`exception` 둘 다 필요. 단계·예상 결과·통과 판정·담당이 구체적이어야 한다. 실행하지 않은 시험 결과를 추가하지 않는다. |
| implementation_steps | `[{action,owner,output,verify}]`. 의존 순서대로 작성. 구현 대상 파일/인터페이스/검증 책임을 업무에 맞게 제안한다. |
| baseline | people_time, end_to_end, rework, actual_use, additional_cost 각각 `{status,value,unit,per,source}`. status: `unknown`, `self_report`, `measured`. unknown은 value:null, 실측 0은 measured/value:0. 수 또는 원문 범위 문자열. 시간은 minutes. |
| comparison | `{same_work_unit,quality_guard,collection,future_check,frequency}`. 동일 물량/품질, 시작·종료·재작업 수집 방법/담당, 향후 비교 시점, 빈도 미확인 구분. |
| next_action | `{owner,action,done_when}` |
| open_questions | `[남은 공백]`. 대화에서 이 목록을 한꺼번에 질문하지 않는다. 구현에 필요한 미확인은 획득 작업으로도 명시한다. |

## 제품 모드 출력과 완료

`planning_scope: product`는 회사/과제에서 주어진 범위 안의 제품 기획이다. `plan.md`와 export는 제품 목표·입력·사용 흐름·규칙·정상/예외 시험·만들 파일/검증·다음 행동만 출력한다. 원문/facts/옛 KPI/비교 값은 JSON에서 보존하며 전달물에 자동 복사하지 않는다. 사용자에게 JSON 전체를 코딩 에이전트 입력으로 주지 않는다.

계약 표식 없는 0.3 제품 모드의 완료/렌더링은 그대로 유지한다. 새 linked 계약은 기술 요건에 더해 사람 확인된 목적 KPI·표면 재사용 검토·앱/측정 연결(bound 또는 획득 작업)을 요구하고 이 내용을 Markdown에 출력한다. 과거 기록은 원래 렌더러로 읽는다. 수정 시 새 리비전에만 계약을 추가하고 확정본은 reopen부터 한다. JSON 보존/문서상 bound를 외부 접속·측정 성공으로 보고하지 않는다.

## 확인 파일

실제 사용자가 전체 핵심과 시험을 본 후 확정했을 때만 작성한다. 아래는 **형식 설명**이지 재사용 가능한 확인 증거가 아니다. `quote`에 예시 문자열을 복사하지 않는다.

- actor: `human`
- quote: 이번 사용자의 실제 확인 발화 그대로
- revision: 사용자가 검토한 최신 draft 리비전 (정수)
- plan_sha256: 해당 draft의 show 출력값
- scopes: 새 linked 계약은 `["user_result", "selected_change", "acceptance_tests", "objective", "linkage"]`; 레거시는 앞의 3개만. 목표 정의의 실제 확인은 objective.confirmation에 별도 기록한다.
- explicit: `true`

도우미는 실제 발화 진위나 인간 신원을 인증할 수 없다. AI가 작성한 확인 파일로 가짜 사람 증거를 만들면 안 된다. 정상 인수 테스트에서만 “합성 테스트 발화”를 사용하며 실제 참가자 증거라고 보고하지 않는다.

## 저장·복구·보안

`<root>/<case-ID>/r000001/{plan.json,plan.md}`처럼 매번 새 리비전 폴더를 만든다. 이전 record 해시 체인과 plan 해시, JSON↔Markdown 일치를 읽을 때 검증한다. JSON/Markdown은 임시 폴더에 동기화 후 폴더 rename으로 함께 공개한다. `.lock` 폴더는 동시 저장을 거절하며 `--expected-revision`은 오래된 초안의 덮어쓰기를 막는다. 원본/기존 export 파일은 자동 덮어쓰지 않는다. 확정 다음 변경은 reopen이 필수이며 기존 확인은 무효화된다(과거 확인은 역사에 유지).

ID는 소문자 ASCII 영숫자와 하이픈 1–64자, Windows 예약 이름 금지. 루트·하위·입력·출력 경로의 기존 심볼릭 링크는 거절한다. macOS `/tmp`는 링크이므로 `/private/tmp` 또는 실제 경로를 사용한다. Windows junction은 지원 Python에서 탐지한다. 이 도구는 **사용자 소유 로컬 디렉터리, 적대적 동시 경로 교체가 없는 환경**을 전제한다. 권한 있는 로컬 사용자의 변조를 막는 보안 DB/서명/감사 인증 도구가 아니다. 해시 체인은 우발적 변조 탐지이지 위조 불가능한 증거가 아니다.

중단 시 마지막 완성 rNNNNNN은 유지한다. `.pending-*`는 읽기 대상이 아니며 자동 삭제/채택하지 않는다. `.lock`가 남으면 쓰기 프로세스가 종료되었는지 사용자가 확인한 뒤 잠금만 수동 제거한다. 중간 리비전 누락, 해시 불일치, 편집된 Markdown은 조용히 건너뛰지 않고 오류를 반환한다. 정상 저장 전후 자동 외부 동작은 없다.

## 0.4.2 저장 검증 보완

렌더러와 원본 JSON 문자열은 그대로 유지하며 Markdown은 UTF-8 바이트로 비교한다. 따라서 CRLF/CR이 들어 있는 기존 리비전도 줄바꿈 자동 변환 없이 검사한다. 기록과 파일을 재작성하거나 과거 해시를 바꾸지 않는다.

입력 JSON과 실제 저장 레코드는 각각 2,000,000바이트 이하이다. 저장 레코드에는 들여쓰기·메타데이터·확정 발화도 포함되므로 입력 한도 안이어도 저장 한도를 넘으면 거절할 수 있다. 실제 직렬화 크기를 확인하고 staging 파일에 load와 같은 검증을 수행한 뒤에만 새 리비전을 공개한다. 크기 초과·공개 전 검증 실패 시 이전 리비전은 그대로 읽고 수정할 수 있다.

이전 버전에서 CR 때문에 읽히지 않던 기록은 바이트가 원래 렌더러 출력과 일치하면 수정 없이 읽을 수 있다. 이미 2MB를 넘겨 저장된 과거 기록은 자동 복구하지 않는다. 원본을 보존한 별도 복구가 필요하며 리비전을 임의 삭제하거나 내용을 직접 줄이지 않는다.
