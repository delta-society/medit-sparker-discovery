# AGENTS.md — AI Sparker Discovery

이 파일은 개발 에이전트가 필요한 맥락을 찾는 안내다. 제품 명세나 작업 이력을 복제하지 않는다. 사용자 지시와 확인된 제품 변화에 맞춰 수정·축소하며, 과거 작업의 임시 조건을 영구 규칙으로 만들지 않는다.

## 제품과 저장소 경계

AI Sparker는 참가자가 자신의 업무로 AI를 연습하고, 목적·KPI·입력·완료 기준을 담은 기획서를 만드는 교육 도구다. 이 저장소는 **교육 스킬·기획/제출 도우미·발표 자료**를 관리한다. 기획서 확정, 실제 업무 프로그램 구현, 성과 측정은 서로 다른 완료 단계다.

| 대상 | 찾아갈 곳 |
|---|---|
| 교육 대화·기획·제출 준비·교육 자료 | 이 저장소의 `plugin/`, `curriculum/`, `examples/` |
| 공통 설치 marketplace·Camp 시작/계정 연결·수집 훅 | [medit-sparker-plugin](https://github.com/delta-society/medit-sparker-plugin) |
| 참가자 로그인·교재·과제 업로드 | [medit-sparker-leaderboard](https://github.com/delta-society/medit-sparker-leaderboard) |
| 운영진 관측·관리·수집 기록 조회 | [medit-sparker-console](https://github.com/delta-society/medit-sparker-console) |
| 팀 결정·운영 인계 / 실행 과제 | DWM `mbk-medit` / Linear의 해당 이슈 |

Discovery와 Camp의 배포 창구는 공통 marketplace `sparker`다. Discovery 코드는 이 저장소에 두고, 공통 저장소가 `plugin/`의 commit을 지정해 배포한다. 배포 변경에서는 **소스 main·marketplace 지정 SHA·실제 설치본**을 각각 확인한다. 소스 병합만으로 참가자 업데이트나 서버 배포가 끝났다고 판단하지 않는다.

## 필요한 만큼 맥락 읽기

단순 문구 수정에 전체 문서나 모든 이전 작업을 읽을 필요는 없다. 작업에 맞춰 아래에서 선택한다.

| 작업 | 우선 참고 |
|---|---|
| 참가자 명령·설치 안내 | [README.md](README.md), [사용법](docs/plugin-guide.md), 해당 `plugin/skills/*/SKILL.md` |
| 기능 범위·완료 기준 | [SPEC.md](SPEC.md)의 해당 항목 |
| 기획 대화·KPI·원문 재사용 | `plugin/references/conversation.md`, `objective-linkage.md`, `data-contract.md` |
| 저장·확정·수정·재개 | `plugin/scripts/plan.py`, 관련 `plugin/tests/`, 데이터 계약 |
| 제출 ZIP / PDF / OS 호환 | [Camp 제출](docs/camp-submission.md) / [PDF](docs/pdf-export.md) / [호환성](docs/platform-compatibility.md) |
| 실제 모델 QA·인수 | 최신 main의 `docs/claude-qa.md`, `docs/operator-readiness.md`, 해당 검증 영수증과 이슈 |
| 발표·수업 구성 | `curriculum/`의 해당 회차 어젠다·발표자 메모·자료 |
| 변경 이유·이전 검증 | [세션 인계](docs/session-handoff.md), 관련 `docs/*verification.md`, `docs/reviews/`, PR |

인계 문서와 검증 영수증은 **그 시점·버전의 증거**다. 예전의 “미실행”이나 “완료”를 현재 상태로 복사하지 않는다. 작업 제목의 `(done)`도 전체 제품 인수를 뜻하지 않는다. 과거 대화가 필요하면 관련 작업의 사용자 결정·최종 결과부터 읽고, 현재 코드·PR·이슈와 대조한다.

작업을 시작할 때 현재 branch·변경 목록을 확인한다. 이 프로젝트에서는 여러 작업이 같은 폴더를 사용했고, 별도 checkout에서 main에 반영한 뒤 원래 폴더에 이전 변경이 남은 적이 있다. 기존 변경을 reset·clean·자동 덮어쓰기로 정리하지 말고, 최신 main이 필요한 작업은 격리 checkout/worktree에서 진행할 수 있다. 파일이 없거나 문서가 충돌하면 checkout 시점을 먼저 확인한다. 공개 main에서 제거한 내부 헌법을 오래된 로컬 사본만 보고 복원하지 않는다.

DWM/Linear는 팀 결정·운영 상태가 필요한 작업에 사용하고, 설치된 스킬의 연결 절차와 현재 제공 도구를 따른다. 일반 코드 수정의 필수 선행 조회로 만들지 않는다. 운영 기록, 현재 서버 상태, 접근 권한은 구분한다. 계정 목록·환경변수·접속 주소·도구 가용성을 이 파일에 고정하거나, 과거 접속 실패를 현재도 불가능하다는 근거로 삼지 않는다.

## 참가자 경험에서 유지할 의도

- 한국어로 한 번에 중요한 판단 하나를 돕는다. 기존 업무 설명과 답변을 재사용하고 AI가 초안을 먼저 제안한다. 사실·가설·미확인을 구분하며 KPI 수치나 사람의 동의를 만들어내지 않는다.
- 일반 시작은 `/sparker-camp:start`, 바로 기획은 **`/sparker-discovery:plan`**이다. 기획을 직접 요청하면 온보딩·Skill/MCP 실습·Camp 계정 연결을 선행 관문으로 되돌리지 않는다. 건너뛴 교육을 완료로 기록하지 않는다.
- 교육 시간과 환경 제약을 고려한다. 기획 대화는 저장 준비와 분리해 진행할 수 있다. 파일 저장·제출 준비에는 Python 3.9 이상, PDF에는 Chrome/Edge가 필요하다. 필요해진 단계에서만 준비를 안내한다.
- 기획 완료에 실제 사내 앱 접속이나 기술 명세 전부를 요구하지 않는다. 기존 앱 입출력을 우선 활용하고 미확인 접근·자료는 확보할 일로 남긴다. 저장·제출 요청을 기획 확정 동의로 해석하지 않는다.
- 제출 ZIP은 기획서만 담는 것이 기본이다. 원문 포함은 별도 명시적 선택이며, **ZIP 구성과 Camp 서버 수집 설정은 별개**다. 파일 준비와 앱 업로드 성공도 구분한다.
- PDF는 개인 보관·공유용 선택 산출물이다. 제출 필수로 만들거나 PDF 실패 때문에 기획 진행을 막지 않는다. 실습 진행 정보와 기획서 리비전도 서로 다른 기록이다.

이 의도를 바꾸는 요청이면 해당 스킬·참조·참가자 안내를 함께 맞춘다. 개발용 `AGENTS.md`의 문구만 바꿔 설치된 참가자 스킬의 동작이 변경됐다고 보고하지 않는다. README는 참가자 안내로 유지한다.

## 변경과 검증

요청 범위의 구현·로컬 검증·발견한 결함 수정까지 이어간다. 이미 허용된 가역적 수정과 검증마다 승인을 다시 받지 않는다. 실제 외부 발신·운영 계정/수집 변경은 해당 요청의 권한 범위를 확인하며, 내부 코드 작업으로 권한이 확대되었다고 추정하지 않는다.

검증은 변경에 맞게 선택한다. 실행 명령의 최신 기준은 `.github/workflows/`와 해당 도우미의 `--help`다.

```sh
# 저장·제출 등 Python 도우미
python3 -X utf8 -m unittest discover -s plugin/tests -v
# AR 합성 계산을 바꿀 때
python3 -X utf8 -m unittest discover -s examples/germany-ar -p 'test_*.py' -v
# QA 실행기를 바꿀 때 (해당 tests/가 있는 checkout)
python3 -X utf8 -m unittest discover -s tests -v
# 스킬/매니페스트 변경 시, Claude CLI가 있는 환경
claude plugin validate ./plugin
```

문서만 고치면 링크·명령·내용 일치와 diff를 확인한다. 저장/패키징을 바꾸면 기존 리비전 호환·한글/공백 경로·LF/CRLF·실제 해제 패키지를 관련 회귀로 확인한다. 불변 fixture를 포맷 정리 대상으로 바꾸지 않는다. 스킬 대화 변경은 도우미 테스트만으로 입증되지 않으므로 합성 업무로 실제 호스트 대화를 확인하고, 실행하지 못한 부분을 명시한다.

실제 모델·브라우저 업로드·운영 수집 검증은 로컬 회귀와 구분한다. 모델/CLI·소스 SHA·패키지·시나리오·관측 결과를 남긴다. Linux/WSL·CI VM의 성공을 참가자 Windows/macOS 실기기나 강사 시간 리허설의 성공으로 확대하지 않는다. API 인증이 필요한 QA는 준비된 격리 환경과 해당 QA 지침을 사용한다. 참가자 원문·자격 증명·개인 기획 저장소는 공개 소스나 배포 ZIP에 넣지 않는다.

## 이 안내를 갱신하는 기준

저장소 책임, 진입 명령, 데이터 계약, 검증 방법이 바뀌면 관련 구현·문서와 이 안내를 함께 갱신한다. 반복된 실패에서 배운 내용은 재발 방지에 필요한 최소 범위만 남긴다. 해결된 임시 우회·중복 지시·오래된 상태는 제거하고, 상세 이력은 기존 검증 문서나 PR에 둔다. 버전·완료 숫자·담당자 목록을 여기에 누적하지 않는다.

스킬 description은 적용할 작업을 짧고 구체적으로 설명하고, 상세 흐름은 필요한 참조로 분리한다. 개발 에이전트의 능력과 참가자용 Claude 스킬의 실행 조건은 다를 수 있으므로 특정 모델을 위한 지침 축소를 참가자 스킬에 일괄 적용하지 않는다.

작성 근거(2026-09-14): 이 프로젝트의 기존 5개 작업과 원격 main 대조. 배포 역할은 [Discovery PR #11](https://github.com/delta-society/medit-sparker-discovery/pull/11), 참가자 흐름은 [PR #12](https://github.com/delta-society/medit-sparker-discovery/pull/12)를 참고했다. 문서 구성은 [OpenAI: Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)의 조건부 맥락 로딩·명확한 완료 범위·낡은 지침 재검토 관점을 적용했다. 이 근거들은 현재 버전의 고정 선언이 아니다.
