# 실제 Claude QA 최종 인수 기록

현재 판정: **0.5.5 재검증 진행 중**. 이 문서만으로 전체 QA·운영 배포 완료를 뜻하지 않는다.

## 후보와 변경

| 항목 | 값 |
|---|---|
| 플러그인 | sparker-discovery 0.5.5 |
| ZIP SHA-256 | `49578b41bd10617837a76c0ca7edfd5355bf0b918cabe0b8ae7c269614883037` |
| CLI / 실제 모델 | Claude Code 2.1.263 / claude-sonnet-4-6 |
| 패키지 | `.qa-runs/releases/sparker-discovery-0.5.5.zip` (현재 QA 작업 사본의 로컬 파일) |
| 원격 변경 | [PR #5](https://github.com/delta-society/medit-sparker-discovery/pull/5), 기반 PR #2 |

Sung 첨부 0.4.2의 활용 가설 선제안·선택 흐름을 기존 보완 위에 선별 통합했다. 31개 파일 중 24개가 기존 Git 파일과 같고 7개가 별도 변경이었다. 정확한 작성 환경·단일 출발 커밋은 첨부만으로 확정하지 않는다. [분석 및 통합 결정](SUNG-INTEGRATION.md)에 근거가 있다.

실제 대화에서 발견한 원문 정제, 근거 없는 현행 수동 작업 단정, 거절된 세션을 사용자 선택 없이 기획서 전용 ZIP으로 바꾸는 문제를 보완했다. 0.5.2에서도 현행 수동 표현이 한 저장 초안에 재발했으므로 이전 PASS를 전체 성공으로 확대하지 않았다. 0.5.3은 저장 직전 근거 대조를 추가했으나 검토 결과에 원문에 없는 수정 요청 절차가 남았다. 0.5.4는 근거가 행 전체를 지지하는지 확인하고, 저장 거절의 답변에도 같은 기준을 적용한다. 활용 선택에서 제외한 기능이 기존 구현·시험에 남았던 문제도 기획서 전체의 범위 대조로 보완했지만 0.5.4 실제 활용 선택에서도 제외된 계산 기능을 선행 구현으로 되살렸다. 0.5.5는 선택한 활용이 기존/제공 자료를 읽도록 설계하고, 제외한 자료 생산 기능은 새로 구현하지 않도록 명시했다. 이 변경의 실제 효과는 별도 새 후보 시험으로 확인한다. 회귀 테스트 91개 통과는 실제 대화 의미 통과와 구분한다.

## 검증 결과

| 영역 | 최종 후보 실행 | 판정 / 보고서 |
|---|---|---|
| 원문 근거·주입 | linux-055-planning + 별도 retry | 충분 자료 2턴 및 별도 retry 10턴 PASS; [의미 검토](LINUX-CONTROLS-REVIEW.md) |
| 저장/확정 거절·중단/재개 | linux-055-planning-retry, linux-055-finalize | 제어 흐름 및 확정/내보내기 3턴 PASS; [검토](LINUX-CONTROLS-REVIEW.md) |
| Camp 경계 입력 | linux-055-edges | 5종·10턴 PASS; [제출 대화](CAMP-LIVE-SEMANTICS.md) |
| 실제 대화 ZIP→브라우저 | linux-055-camp, live-09-retry/live-10 | 2종·4턴 및 두 브라우저 왕복 PASS; [브라우저 검토](CAMP-BROWSER-REVIEW.md) |
| Windows/macOS 네이티브 | native-07 + native-08 | 양 OS Camp 24턴·확정 6턴, Windows 기획 12턴 PASS. macOS 기획 재시험·양 OS 활용 선택 진행 중; [네이티브 검토](NATIVE-LIVE-REVIEW.md) |
| 활용 선택·목표 보존·일회성·주간 보고 | linux-055-reuse + retry | Linux 4종·9턴 PASS, 양 OS 결과 검토 중; [검토](LINUX-055-REUSE-REVIEW.md) |

초기 실패 실행은 삭제하거나 성공 실행과 합치지 않는다. 구조 실행기의 `NOT_REVIEWED` 값도 그대로 보존하고, 각 검토 문서에서 발화·도구 호출·저장 리비전·파일 해시를 대조한 의미 판정을 별도로 제공한다.

## 운영 인수에 남는 범위

- 실제 MacBook 설치·사용 확인(DEL-483), 강사의 발표/실습 시간 리허설(DEL-441), 교육 배포 인수(DEL-486)는 별도로 남는다. 준비물은 [운영자 실행 준비표](../../operator-readiness.md)에 있다.
- Windows Server 2022 runner와 macOS 15 VM의 결과다. Windows 10/11·OneDrive·기업 보안 소프트웨어·ARM64·개인 MacBook에서의 설치 성공을 대신하지 않는다.
- 현재 후보는 수동 Camp ZIP이다. 기획서 PDF 내보내기와 자동 전체 대화 텔레메트리는 포함하지 않는다. DEL-489에서 확정한 정책은 유지하며, 자동 수집 구현·실제 저장 권한·복구/분석 인수는 DEL-507~512에서 추적한다.
- 참가자 앱은 ZIP의 주차와 업로드 대상 주차 불일치를 서버에서 거부하지 않는 현행 한계가 있다. 같은 주차 선택과 제출 기록 대조가 필요하다. QA의 잘못된 주차 수용 관찰을 정상 차단으로 쓰지 않는다.
- 합성 입력과 시험 계정만 사용했다. 공격 지시를 실행하지 않은 모델 관측과 네트워크 격리의 독립 차단 시험을 구분한다. 모든 미래 프롬프트 주입·임의 업무 판단의 안전성을 보장하지 않는다.

## 네이티브 재시험 차단 근거

0.5.3 원격 aa8bcd2의 [Actions 실행 34196034344](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34196034344)는 request-matrix 작업도 시작하지 못했다. check-run 101963843792의 GitHub annotation은 최근 결제 실패 또는 지출 한도 증액 필요를 이유로 명시한다. 모델·제품 코드 실패가 아니며 로그가 없는 것을 PASS로 해석하지 않는다. 사용자에게 조직 Billing & plans 복구를 요청했다. 복구 전 다른 조직/저장소로 우회하거나 네이티브 미실행을 Linux 결과로 대체하지 않는다.

0.5.2 원격 실행 34194609057 및 macOS 확정 재시도 34195413508의 실제 OS 증거는 각 보고서에 보존한다. 해당 후보의 발견 사항 때문에 최종 0.5.5의 네이티브 PASS로 승계하지 않는다.

복구 관측: 이후 e181e00 소스의 호환성 CI [34197474831](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34197474831)과 [34197469479](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34197469479)가 실제로 실행되어 성공했다. 이에 3a13754에서 최종 0.5.5의 [native-07 실제 대화 시험](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34197747230)을 시작했다. 운영 결제 설정을 이 작업에서 변경한 것은 아니며, 실행 차단의 해소만 관측했다.

검사기 보완 중: 실패한 `new` 명령이 남긴 빈 폴더를 유효 리비전으로 간주하던 문제는 ba4afd4에서 보완하고 43개 검사기 테스트를 통과했다. 별도로 native-07 macOS planning은 문서가 허용한 작업 폴더 직접 저장에 성공했으나, 기본 숨김 폴더만 읽는 수집기가 저장을 놓쳐 중단됐다. 이 실행은 제품 저장 실패나 전체 PASS로 기록하지 않는다. 승인된 작업 폴더의 직계 과제 저장도 전체 Store 검증을 적용하도록 보완했다. 두 저장 위치의 이력 키를 구분하고 삭제·손상·저장 거절·승인 집합 변경·심볼릭 링크 차단을 확인한 검사기 회귀 48개가 통과했다. macOS의 미완료 네 사례는 native-08 별도 실행으로 재검증한다.

DEL-490은 같은 0.5.5 후보의 양 OS Camp 24턴, Linux 경계 10턴·ZIP 준비 4턴과 두 Chromium 왕복의 독립 검토를 완료하여 Done 처리했다. 나머지 실행의 진행 상태와 구분한다. 사용자 요청에 따라 시작한 `linux-055-sonnet5`는 후속 Haiku 4.5 선택으로 중단했다. 부분 증거는 보존하고 PASS를 부여하지 않는다. 새 `linux-055-haiku45`는 `claude-haiku-4-5-20251001`에서 핵심 활용 선택 3턴을 시험하며 기존 Sonnet 4.6 결과와 별도로 기록한다. 전체 OS 시험을 새 모델로 반복한 것은 아니다. 이후 새 Claude 대화 호출은 사용자 지정 Haiku 4.5를 사용한다.
