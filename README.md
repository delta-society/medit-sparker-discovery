# AI Sparker — 내 업무로 배우는 AI 실습

## 3주차 코드 기반 평가·한 장 PDF

공통 Sparker 플러그인을 업데이트한 뒤 `/sparker-discovery:week3`으로 시작합니다. Camp 진입은 `/sparker-camp:start 3주차 수업`입니다. 이전 코드를 읽고 여섯 기준으로 상세하게 묻고 답하며, 참가자가 전체 초안을 검토한 뒤 한 장 PDF 평가서를 받습니다. 진행은 `.sparker-evaluation`에 저장해 재개할 수 있습니다. 입력·출력 연결과 제품 수정은 필수가 아니며 기존 1·2주차는 보존합니다. PDF는 Python 3.9+와 기존 Edge/Chrome을 사용합니다. 기존 설치자는 공통 업데이트 안내를 따르며 새 ZIP 설치는 필요하지 않습니다.

## 2주차 구현 확장

기본 시작은 `/sparker-camp:start`, 직접 진입은 `/sparker-discovery:week2`입니다. 기존 기획 읽기 → 제품 생성·로컬 웹 화면 → 실제 스펙 설명 → workstream 선택·완료 기준 → 실행 → 예상·수정 전후 비교 → 정상/예외/다른 입력/재실행 검증 → 시연·재개/선택 제출 준비로 이어집니다. 원본 기획·Week1 기록·Camp 수집 계약을 바꾸지 않습니다. 실제 업로드·업무 성과는 별도입니다. 구현 기록은 별도 `.sparker-implementation`에 저장하며 기존 학습 진행 스키마에 추가하지 않습니다. 상세는 플러그인의 `references/week2-implementation.md`를 따릅니다.


Claude와 작은 작업을 해보고, 반복 요청을 만들고, 내 업무에 쓸 기획서까지 완성합니다. 이미 설명한 업무나 작성한 기획서는 이어서 사용할 수 있습니다.

## 설치와 시작

**[AI Sparker 공통 설치 안내](https://github.com/delta-society/medit-sparker-plugin#설치)**에서 설치하세요. 자신의 실습 폴더에서 Claude Code를 열고 한 줄을 입력합니다.

```text
/sparker-camp:start
```

필요한 연결을 확인하고 처음 시작하거나 이전 실습을 이어갑니다. 이 저장소는 교육 기능의 소스와 사용법을 관리합니다.

## 1주차에 해볼 일

- 업무 메모로 Claude와 작은 작업 해보기
- 반복 요청을 **Skill**로 만들어 실행하기
- 외부 자료를 가져오는 **MCP** 연결 알아보기
- 내 업무의 결과·입력·완료 기준을 기획서로 정리하기
- 과제 파일과 다음 주 준비 글 만들기

한 번에 한 행동씩 안내합니다. “쉽게 설명해줘”, “건너뛰기”, “기획만”, “제출부터”라고 말해도 됩니다. 추가 기능 체험은 기본 실습 뒤 원할 때 진행합니다.

## 저장과 제출

기획서는 내용을 확인하고 동의하면 확정합니다. 모르는 자료나 규칙은 남겨두고 초안으로 이어갈 수도 있습니다.

`/sparker-discovery:week1-submit`은 1주차 기획서 ZIP을 만듭니다. 파일을 확인한 뒤 [참가자 앱](https://leaderboard-production-eac2.up.railway.app/)의 같은 회차에 직접 올리세요. **파일 준비와 실제 제출은 별개**입니다. PDF는 개인 보관·공유용 선택 사항이며 제출 ZIP에는 포함되지 않습니다.

다음 주 준비 글은 Slack에 직접 게시합니다. 기획서는 중복 첨부하지 않습니다.

[실습·재개·제출 상세 안내](docs/plugin-guide.md) · [공통 업데이트 안내](https://github.com/delta-society/medit-sparker-plugin#업데이트)

## 주차별 제출 명령

- `/sparker-discovery:week1` → `/sparker-discovery:week1-submit`: 기획서 ZIP (초안 가능, 요청한 경우만 선택 원본 포함).
- `/sparker-discovery:week2` → `/sparker-discovery:week2-submit`: 구현 보고서와 검증된 코드·실행 방법·시험 결과 ZIP. 미완료도 중간 보고서는 만들 수 있지만 완료 ZIP 검사는 생략하지 않습니다. 앱의 2주차 구현 ZIP 접수 지원은 별도 확인이 필요합니다.
- 기존 `/sparker-discovery:submit`과 “제출 준비해줘”는 확인된 주차를 재사용합니다. 주차가 불명확하면 한 번 묻고, 임의로 1주차를 고르지 않습니다.

모두 로컬 파일 준비이며 자동 업로드하지 않습니다. 최신 배포는 [공통 Sparker 설치·업데이트 안내](https://github.com/delta-society/medit-sparker-plugin)를 따릅니다.

## 0.12.0 — 3주차 PDF 직접 제출

`/sparker-discovery:week3-submit` 또는 3주차 맥락의 `/sparker-discovery:submit`은 최신 검토 완료 평가 PDF만 제출합니다. 최초 한 번만 기존 웹 로그인 후 **터미널 연결에 동의하고 제출**을 누릅니다. 이후 30일 연결 유효기간 동안 다른 PDF·리비전·case도 터미널 제출 요청만으로 웹 확인 없이 전송하고 서버 receipt를 재조회합니다. 제출 전용 기기 인증은 프로젝트 밖 `~/.config/sparker-report/`에 0600으로 보관하며 `submission_bridge.py --logout`으로 서버 연결을 해제합니다. 만료/해제된 인증은 제출을 차단하며 재연결이 필요합니다. 코드·원문·Camp 토큰은 전송하지 않으며 보고서 확정과 전송 동의는 별개입니다. timeout은 접수 완료가 아닙니다. 같은 명령으로 재개하면 동일 intent를 조회합니다.

업데이트 후 Claude Code에서 `/reload-plugins`를 실행하세요. 명령이 보이지 않으면 세션을 다시 시작하고 0.12.0 로드를 확인하세요. ZIP을 사용한다면 새 ZIP을 고정 디렉터리에 풀어 `claude --plugin-dir <directory>`로 다시 로드하세요. 구 0.11 PDF는 SHA receipt가 없어 같은 confirmed 기록으로 `evaluation.py --root <root> --case <case> pdf --refresh` 재출력이 필요합니다(재평가/재로그인 요구 아님).
