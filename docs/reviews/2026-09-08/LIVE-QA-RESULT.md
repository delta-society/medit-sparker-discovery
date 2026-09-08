# 실제 Claude QA 인수 기록

후속 main 병합 통합본은 **0.6.1**이다. main의 선택형 PDF·marketplace·온보딩·Week 1을 보존하고 아래 기획 QA 변경을 통합했다. [병합 리뷰](MERGE-REVIEW.md)를 따른다. 아래 0.5.7 모델 대화 결과와 패키지 해시는 당시 인수 증거이며 통합본의 전체 모델 재시험으로 확대하지 않는다.

기획 변경의 실제 대화 판정: **0.5.7 Haiku 4.5의 사용자 지정 핵심 3턴 인수 게이트 PASS**.

사용자는 소요 시간을 줄이기 위해 이후 Claude 호출을 Haiku 4.5로 지정했고, “Haiku에서 통과하면 통과로 처리”하도록 인수 기준을 변경했다. 새 후보의 핵심 활용 선택 3턴을 최종 게이트로 삼는다. 이전 Sonnet 결과를 Haiku 결과로 바꾸거나 새 후보의 전체 OS 시험으로 확대하지 않는다.

## 현재 후보

| 항목 | 값 |
|---|---|
| 플러그인 | sparker-discovery 0.5.7 |
| 소스 | `40805f29a3056a11027effd5015a2dbb3c16ee1b` |
| ZIP SHA-256 | `de19675b8687b81378fdedc1a53a335df87ebd20e8457272be2f1cb7cd808d23` |
| 새 대화 모델 | `claude-haiku-4-5-20251001` |
| CLI | Claude Code 2.1.263 |
| 패키지 | `.qa-runs/releases/sparker-discovery-0.5.7.zip` |
| 원격 변경 | [PR #5](https://github.com/delta-society/medit-sparker-discovery/pull/5), 기반 PR #2 |

ZIP의 21개 파일을 원격 소스와 바이트 대조했다. [패키지 근거](PACKAGE-PROVENANCE.json)에 해시를 기록했다. 0.5.5 근거는 [별도 보존](PACKAGE-PROVENANCE-055.json)했다.

0.5.7은 Haiku가 참조를 잘못된 `skills/plan/references`에서 찾은 뒤 임의 JSON을 저장하던 실패를 보완한다. Claude가 치환하는 `${CLAUDE_PLUGIN_ROOT}`의 절대 참조 경로를 제공하고, helper의 template/new/update 및 과제·리비전·파일 위치 확인을 저장 완료 조건으로 명시했다. 두 리뷰어가 이 변경을 검토했으며 플러그인 회귀 93개가 통과했다. 실행기 회귀는 48개가 통과했다.

## 실제 검증 범위

| 후보·모델 | 실행 | 결과 |
|---|---|---|
| 0.5.7 Haiku 4.5 | linux-057-haiku45, 활용 미확인→선택/제외 3턴 | PASS; [독립 검토](HAIKU-ACCEPTANCE.md) |
| 0.5.5 Sonnet 4.6 | Linux 충분 원문 2턴 + 별도 planning retry 10턴, 확정/내보내기 3턴 | scoped PASS; [검토](LINUX-CONTROLS-REVIEW.md) |
| 0.5.5 Sonnet 4.6 | Linux 활용 선택 3턴 + 별도 retry 6턴 | 4사례·9턴 scoped PASS; [검토](LINUX-055-REUSE-REVIEW.md) |
| 0.5.5 Sonnet 4.6 | Linux Camp 경계 10턴·ZIP 준비 4턴, Chromium 왕복 2회 | scoped PASS; [경계](CAMP-LIVE-SEMANTICS.md)·[브라우저](CAMP-BROWSER-REVIEW.md) |
| 0.5.5 Sonnet 4.6 | native-07 Windows 기획 12턴, 양 OS Camp 24턴·확정 6턴 | scoped PASS; [검토](NATIVE-LIVE-REVIEW.md) |
| 0.5.5 Sonnet 4.6 | native-07 양 OS 활용 선택 18턴 | 구조 PASS, 근거 없는 현행 수작업 단정 F2/P2 남음; [검토](NATIVE-055-REUSE-REVIEW.md) |
| 0.5.5 Sonnet 4.6 | native-07 macOS 기획 일부 / native-08 별도 재시험 | 수집기 문제로 일부 중단; native-08 재시험 10턴 구조 PASS, 최신 사용자 인수 게이트가 아님 |

기존 Sonnet F2는 사실과 다르게 해결됐다고 쓰지 않는다. 사용자 지정 Haiku 결과만 새 게이트에 사용한다. 자동 구조 결과의 `NOT_REVIEWED`도 보존하며 의미 검토는 실제 발화·도구·저장 리비전·해시를 대조한 별도 문서에서 제공한다.

## 실패와 보완의 추적

Sung 첨부 0.4.2의 활용 가설 선제안·선택 흐름을 기존 보완 위에 선별 통합했다. 31개 파일 중 24개는 기존 Git 파일과 같고 7개는 별도 변경이었다. 작성 환경이나 단일 출발 커밋은 첨부만으로 단정하지 않는다. [통합 근거](SUNG-INTEGRATION.md)를 따른다.

이전 실제 대화의 원문 정제·근거 없는 현행 업무 단정·거절 세션 임의 대체·제외 기능 재도입을 보완했다. 0.5.5는 선택 활용이 기존/제공 자료를 읽도록 하고 제외된 자료 생산 기능을 새로 구현하지 않도록 했다. 범위 제외 효과는 확인됐지만 Sonnet 네이티브의 현행 업무 단정은 위와 같이 남았다.

실패한 new가 남긴 빈 폴더를 리비전으로 간주하던 검사기는 ba4afd4에서 보완했다. 문서가 허용한 작업 폴더 직접 저장을 기본 숨김 폴더 전용 수집기가 놓친 경우는 23ed4bf에서 보완했다. 작업 폴더 직계 과제와 기본 저장소 모두 전체 Store 검증을 적용하고, 두 위치의 이력을 구분해 삭제·손상·저장 거절·승인 집합 변경·링크를 검사한다. 원래 실패를 제품 저장 실패나 성공으로 바꾸지 않는다.

추가 Sonnet 5 실행은 사용자의 Haiku 변경 요청으로 중단했다. 0.5.5 Haiku는 잘못된 참조 경로와 helper 미사용 때문에 실패했고 원래 증거를 보존했다. 0.5.6은 경로를 보완했지만 임시 입력을 과제 폴더에 넣은 오류를 복구하다 원문을 빠뜨려 실패했다. 0.5.7은 linked template에 submission/facts를 유지하고 입력을 과제 폴더 밖에 작성하도록 보완했다. 새 실행을 기존 실패 파일에 덮어쓰지 않았다.

## 완료 범위와 인수 자료

DEL-485와 DEL-490은 각각 0.5.5의 실제 Linux 격리 QA, 양 OS Camp 및 브라우저 검증 근거로 Done 처리했다. 최종 새 후보의 모델 기준은 위 Haiku 게이트로 구분한다.

- 실제 MacBook 설치·사용 확인(DEL-483), 강사 시간 리허설(DEL-441), 교육 배포 인수(DEL-486)는 담당자가 수행한다. [운영자 준비표](../../operator-readiness.md)에 설치·업데이트·복구·인계 절차가 있다.
- 네이티브 근거는 Windows Server 2022와 macOS 15 VM이다. Windows 10/11·OneDrive·기업 보안 소프트웨어·실제 MacBook 검증을 대신하지 않는다.
- 현재 후보는 수동 Camp ZIP이다. 기획서 PDF와 자동 전체 대화 텔레메트리는 포함하지 않는다. DEL-489 확정 정책과 DEL-507~512의 병행 구현 경계를 유지한다.
- 참가자 앱은 ZIP/업로드 주차 불일치를 거부하지 않고 draft 상태를 자동 표시하지 않는다. 일부 모델 안내의 표시 가능성 추측은 한계로 남긴다.
- 합성 입력과 시험 계정만 썼다. 모델의 공격 거절 관측과 별도의 네트워크 차단 시험을 구분하며 모든 미래 공격·업무 판단의 안전성을 보장하지 않는다.

최종 핵심 검토는 원문 보존, 정상 r1/r2 저장, 미확정 목표·확인 경계, 선택 범위와 제외 기능 반영을 통과했다. user_result에 초기 주간 검토 요약이 남은 P3 정합성 한계는 검토 문서에 기록한다. 사용자가 지정한 제한된 Haiku 인수 기준의 PASS이며 모든 필드·모델·OS의 완전성을 뜻하지 않는다.

최종 소스의 [호환성 CI](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34200275116)와 [호환성 CI](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34200271149)가 통과했다. 자체 컨테이너·네트워크·앱 서버와 임시 CI 인증을 정리했으며 원본 사용자 인증은 변경하지 않았다. 로컬 증거 `.qa-runs/evidence-2026-09-08/index.json`은 수집 파일의 해시를 제공하며 인증값 검사 후 보존한다.
