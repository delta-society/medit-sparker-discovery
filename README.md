# AI Sparker — 함께 실습하는 Claude Code 플러그인

Claude Code와 대화하며 AI 도구를 익히고, 내 업무에 적용할 기획서를 만들어보세요.

처음 시작하는 분은 **온보딩**, 1주차 수업을 진행하는 분은 **Week 1**을 실행하면 됩니다. 한 번에 한 단계씩 안내하며, 이미 작성한 업무 설명과 기획서는 이어서 사용할 수 있습니다.

## 1. 설치하기

Claude Code를 실행한 뒤, **Claude Code 대화창**에 아래 명령을 한 줄씩 입력하세요.

```text
/plugin marketplace add delta-society/medit-sparker-discovery
/plugin install sparker-discovery@sparker
```

설치가 끝나면 Claude Code를 종료하고, 자신의 실습 폴더에서 다시 실행하세요. ZIP을 다운로드하거나 이 저장소를 복제할 필요는 없습니다.

## 2. 실습 시작하기

**처음이라면:**

```text
/sparker-discovery:onboarding
```

실습 폴더를 확인하고, 첫 대화와 Claude에게 업무 지침을 알려주는 `CLAUDE.md` 작성부터 시작합니다.

**1주차 수업을 시작하거나 이어가려면:**

```text
/sparker-discovery:week1
```

Week 1에서는 다음을 함께 해봅니다.

- 반복할 요청을 **Skill**로 만들고 직접 실행하기
- 외부 도구를 연결하는 **MCP**를 이해하고 연결 상태 살펴보기
- 작업을 나누는 에이전트, 자동 동작을 연결하는 Hook, 기능을 묶는 Plugin 알아보기
- 기존 업무 설명으로 목표·입력·결과·완료 기준이 담긴 기획서 만들기
- 참가자 앱 제출 파일과 Slack에 올릴 다음 주 준비 글 만들기

“Skill부터”, “MCP부터”, “기획만”, “제출부터”처럼 말해 원하는 단계로 이동할 수 있습니다. 어려우면 “쉽게 설명해줘”, 시간이 부족하면 “건너뛰기”라고 말하세요. MCP가 연결되어 있지 않아도 개념과 활용 방법을 먼저 익힐 수 있습니다.

## 이미 설치했다면 업데이트하기

아래 명령은 **터미널**에서 실행하세요.

```sh
claude plugin marketplace update sparker
claude plugin update sparker-discovery@sparker
```

업데이트 후 Claude Code를 다시 시작하세요. 기존 실습 폴더와 기획서는 지우지 않습니다.

## 준비물

| 준비물 | 필요한 때 |
|---|---|
| 실행 가능한 Claude Code | 모든 실습 |
| 자신의 로컬 실습 폴더 | 실습 파일과 기획서를 보관할 때 |
| 기존에 제출한 업무 설명 | 내 업무 기획을 시작할 때. 대화에 붙이거나 파일 경로를 알려주세요 |
| Python 3.9 이상 | 기획서 저장과 제출 파일 준비. 첫 대화·Skill 체험에는 필요하지 않습니다 |
| Chrome 또는 Microsoft Edge | PDF를 만들기로 선택했을 때만 필요합니다 |

이미 Chrome이나 Edge가 설치되어 있다면 추가 설치나 확장 프로그램, `/chrome` 설정은 필요 없습니다. PDF를 건너뛰어도 기획서는 보관됩니다.

## 기획서와 과제 제출

기획서는 대화로 보정한 뒤 **참석자가 내용을 확인하고 동의하면 확정**합니다. 아직 모르는 자료나 규칙은 남겨두고 초안으로 이어갈 수도 있습니다.

제출 파일은 실습 폴더에 준비됩니다. 파일을 검토한 뒤 [Sparker 참가자 앱](https://leaderboard-production-eac2.up.railway.app/)에 로그인해 해당 회차 과제로 직접 업로드하세요. 파일 준비와 앱 제출은 별개입니다. Slack에는 다음 주에 실행할 기능과 그 결과로 새로 가능해질 일을 정리해 직접 게시합니다.

세션 원본을 제출 파일에 넣을지는 따로 선택합니다. 원본을 포함하면 선택한 세션의 대화·응답·실행 결과가 들어가므로 내용을 확인하세요. 캠프의 대화 기록 운영 정책과 제출 파일 선택의 차이는 [상세 사용 안내](docs/plugin-guide.md#캠프-과제-제출)를 참고하세요.

## 필요한 기능만 바로 실행하기

| 명령 | 하는 일 |
|---|---|
| `/sparker-discovery:onboarding` | 첫 준비와 대화 체험 |
| `/sparker-discovery:week1` | 1주차 실습 진행·재개 |
| `/sparker-discovery:plan` | 업무 기획서 작성·수정·재개 |
| `/sparker-discovery:submit` | 과제 제출 파일 준비 |

더 자세한 저장·PDF·제출 방법은 [상세 사용 안내](docs/plugin-guide.md)에서 확인할 수 있습니다.
