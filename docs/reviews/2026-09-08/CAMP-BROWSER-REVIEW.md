# Camp 실제 대화 → 브라우저 왕복 검토

2026-09-08, 합성 자료만 사용했다. 실제 Claude가 생성한 제출 ZIP 2개를 새 로컬 참가자 앱 인스턴스의 Chromium 파일 입력으로 업로드하고 내려받았다. 운영 서버·실제 참가자 계정은 사용하지 않았다. 이번 결과는 아래 2개 대화 시나리오와 격리 앱 왕복에 한정한 PASS다.

## 고정 대상과 증거

| 대상 | 식별자 |
|---|---|
| Claude 실행 | `linux-camp-01`, `claude-sonnet-4-6`, Claude Code `2.1.263`, Linux disposable-container |
| 플러그인 | `0.5.1`, ZIP SHA-256 `8285dd75065ca944883fa07855b066d0a0c777b225d4aa9e07f7e38533fce04a` |
| QA 실행기 SHA-256 | `9957269405bce75729090a9767ab069ff2ab60433788000ef993870e5afe8aac` |
| 참가자 앱 commit | `439d2ba491cef5f2a4c01947a03a1577491672d9` |
| 실제 브라우저 | Chromium `151.0.7922.34`, loopback 서버 외 브라우저 HTTP(S) 차단 |
| 대화 증거 | `/tmp/discovery-live-qa/runs/linux-camp-01/`의 manifest/state, 각 케이스 input/events/tools/records, work 파일 |
| 브라우저 증거 | `/tmp/discovery-live-qa/browser/live-01/`, `/tmp/discovery-live-qa/browser/live-02/`의 result.json, downloaded.zip, submission-history.png |

브라우저 드라이버는 pinned commit 대비 tracked 변경과 untracked 실행 소스/config를 검사했다. 생성 파일 `next-env.d.ts`만 명시적으로 제외하며 해당 파일 해시는 각 result.json에 기록했다. 이 임시 증거 경로는 장기 보관 위치가 아니다. 인계 시 합성 검토 산출물의 보관 위치를 연결하고, 시험 DB·서버 로그에는 합성 계정 정보가 있을 수 있으므로 무검토 공개하지 않는다.

## 실제 대화 4턴의 의미 검토

각 턴의 입력·최종 응답·도구 인수를 읽고, 준비된 기획서와 선택 세션 원본 바이트를 ZIP 내용과 직접 대조했다. 두 케이스 모두 기존 합성 초안 r1을 사용했으며 실제 참가자 대화 원본을 수집한 시험이 아니다. 선택 세션은 prepare가 만든 합성 JSONL fixture이고, ZIP 준비·검사는 실제 Claude의 도구 호출이다.

| 케이스 | 관측 결과 | 판정 |
|---|---|---|
| `camp-plan-only` T1 | 기획서만 요청에 따라 helper prepare 호출. r1 draft, 세션 없음, 로컬 준비/서버 미전송을 명시 | PASS |
| `camp-plan-only` T2 | 실제 inspect 호출 후 해시·회차·크기·리비전을 대조. 사용자가 미업로드라고 말한 상태를 유지 | PASS |
| `camp-multiple-sessions` T1 | 정확히 요청한 두 UUID를 `--session-file`로 전달. 원본 마스킹 없음·선택 외 세션 제외·draft·아직 제출 전을 명시 | PASS |
| `camp-multiple-sessions` T2 | 실제 inspect 결과와 준비 해시 일치. 기획서 1개·세션 2개와 draft 표시 유지. 자동 업로드 도구 호출 없음 | PASS |

기획서만 케이스의 두 턴은 약 29.86초/11.83초, 복수 세션은 34.82초/13.62초였다. 복수 세션 첫 턴에 `camp_submit.py plan.py ... || true`라는 잘못된 조회 시도가 있었고, 이후 올바른 `plan.py show`로 회복했다. 이 실패를 성공 증거로 사용하지 않았으며 최종 helper 결과와 파일을 검증했다. 두 케이스에서 원문·초기 리비전 입력 해시는 유지됐고 자동 확정은 없었다.

## 실제 업로드와 다운로드

| 실행 | 실제 모델이 생성한 입력 ZIP SHA-256 | 내용 |
|---|---|---|
| `live-01` | `0dccb57ca7e4c972ab0bce46c1123c96057e57dcc02310a85deaf3d49f6c4fa2` | 기획서만, 1,608 bytes |
| `live-02` | `b2ce97832d7483d9a555f3b2bad791d5a1a844c5e15b77e5a4e00de5264d8bd3` | 기획서 + 선택 세션 2개, 2,440 bytes |

복수 세션 UUID는 `1c708194-6116-4748-abf0-34573c3a996a`, `f3c2a039-c4f0-4c73-ace7-90724722c900`이다. ZIP에는 manifest·기획서·선택한 두 원본만 있고, 두 JSONL 및 plan.md의 바이트는 제공된 파일과 일치했다. 선택하지 않은 합성 세션은 포함되지 않았다.

각 브라우저 실행에서 다음 9항목을 확인했다. result.json의 checks 배열은 8개이며 소스 검사는 별도 source_guard 필드에 있다.

1. 앱 소스 commit과 변경 검사 및 생성 파일 예외 해시 기록.
2. 새 합성 참가자가 Chromium UI로 초대 수락·계정 활성화.
3. 실제 ZIP 파일 입력 업로드 성공 후 새로고침해 제출 표시 유지.
4. 참가자 Chromium 다운로드의 전체 SHA-256 및 Camp manifest가 입력과 일치.
5. 인증된 운영자 API의 같은 제출 ID 다운로드가 입력 SHA-256과 일치.
6. 같은 ZIP 재제출 시 새 제출 ID 생성, 이전 이력 보존, 활성 이력 1개.
7. 5 MiB 초과 UI 업로드 거부 및 제출 건수 유지.
8. **잘못된 주차 동작 관측**: 1회차 manifest ZIP을 UI에서 2회차로 선택하면 앱이 201로 받아 2회차에 표시.
9. 과제 제출 전후 사용량 token 값이 변하지 않음.

8번은 오제출 차단 PASS가 아니다. 현재 앱은 ZIP manifest의 주차를 검사하거나 UI 주차를 자동 설정하지 않는다. 참가자가 주차를 직접 확인해야 하며 이 제한을 배포 안내에 남긴다. 운영자 확인은 API 다운로드 시험이고 camp 어드민 화면 전체의 사용성 시험은 아니다. 로컬 합성 앱 왕복은 운영 배포·실제 계정 권한·원본 보관/삭제 정책·Windows/macOS 대화 QA를 대체하지 않는다.

## 최종 0.5.2 후보: linux-camp-02 → live-03/live-04

기존 0.5.1 결과와 구분해, 최종 후보의 실제 Claude 대화 4턴과 그 모델이 준비한 두 ZIP으로 브라우저 왕복을 다시 실행했다. **두 시나리오 의미 검토 및 두 브라우저 실행 모두 PASS**다.

| 고정 대상 | 값 |
|---|---|
| 실제 대화 실행 | `/tmp/discovery-live-qa/runs/linux-camp-02/`, 두 시나리오 각 2턴 |
| 패키지 버전·SHA-256 | `0.5.2` / `6fc4e7d9093d42eb0cf35d6e381c58947ea20af535989f3cace308736098e143` |
| CLI·모델 | Claude Code `2.1.263` / `claude-sonnet-4-6` |
| 실행기 SHA-256 | `009351a066a53a03eba5da711f72d4d5aab607a543c00311b94a275c84671f51` |
| 참가자 앱 | `439d2ba491cef5f2a4c01947a03a1577491672d9`, 새로운 loopback 서버·합성 DB/계정 |
| 브라우저 | Chromium `151.0.7922.34` |

`camp-plan-only`는 실제 helper로 기획서만 준비했고 다음 턴 실제 inspect로 같은 SHA를 확인했다. `camp-multiple-sessions`는 지정한 두 UUID만 전달해 prepare하고 다음 턴 inspect했다. 사용자 발화가 실제 앱에 업로드하지 않았다고 명시한 상태를 두 시나리오 모두 유지했다. 자동 확정·외부 업로드 호출·앱의 초안 자동 표시 주장은 없었다.

| 브라우저 실행 | 모델 생성 ZIP SHA-256 | 검증한 내용 |
|---|---|---|
| `/tmp/discovery-live-qa/browser/live-03/` | `0dccb57ca7e4c972ab0bce46c1123c96057e57dcc02310a85deaf3d49f6c4fa2` | 기획서만, 1,608 bytes |
| `/tmp/discovery-live-qa/browser/live-04/` | `74702761c49b27dbe837936b8e1a43eb85505d866b519a27efabb73573271df5` | 기획서 + 지정 세션 2개, 2,442 bytes |

복수 세션은 `1ccc3f5d-6000-4352-b3d8-6b80dbb35cff`, `f068222c-2057-47c5-8a5a-477d26f289f2`다. 두 ZIP의 기획서 바이트는 각 초기 r1 plan.md와 같고, 복수 세션의 두 JSONL 바이트는 각 제공 원본과 같다. 입력 manifest 해시도 모두 유지됐다. 기획서만 ZIP이 이전 run과 같은 해시인 이유는 동일 기획 내용·결정적 ZIP 출력이며, 이번 모델의 실제 prepare/inspect 호출은 `linux-camp-02`의 독립 도구 기록으로 확인했다.

두 브라우저 실행은 위 본문의 9개 항목을 다시 통과했다. 각 result.json에는 실제 브라우저 버전, 소스 검사 결과, 8개 checks, 최초/재제출 ID가 있다. source_guard는 tracked 소스가 고정 commit과 일치함을 확인했고, 유일한 생성 파일 예외 `next-env.d.ts`의 해시는 두 실행 모두 `0f70629890b72a0a82e91972cc032c04b658b26c265373cb711cf576bfbf8fcc`였다.

최종 후보에서도 1주차 ZIP을 UI에서 2주차로 고르면 접수된다. 이는 동일한 앱 제한의 재확인이며 오제출 차단 기능이 생겼다는 뜻이 아니다. 참가자 다운로드 및 인증된 운영자 API 다운로드는 입력 SHA와 일치했다. 5 MiB 초과 업로드는 거부되고 이력이 추가되지 않았으며, 동일 ZIP 재제출은 별도 이력을 남겼다. 모든 실행은 자체 생성한 서버만 종료했고 운영 서비스·실제 사용자 계정은 사용하지 않았다.
