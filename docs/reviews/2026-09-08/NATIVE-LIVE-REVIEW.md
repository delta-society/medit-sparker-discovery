# 네이티브 실제 대화 QA — 부분 의미 검토

GitHub Actions 실행 `34193672226` (`native-03`)의 내려받은 증거를 검토했다. 이 문서는 완료된 그룹만 판정하며, 전체 6개 작업이나 실기기·배포 완료를 선언하지 않는다. 이전 native-01/02 결과를 합치지 않는다.

## 판정 현황

| OS / 그룹 | 이 문서에서 검토한 범위 | 판정 |
|---|---|---|
| macOS / finalize | `finalize-lifecycle` 3턴 입력·이벤트·도구·리비전·내보내기 | **승인·재개·동일 확정본 내보내기 PASS** |
| Windows / finalize | `finalize-lifecycle` 3턴 | 구조/재개 PASS, **확인 후 미검토 설계 추가로 의미 FAIL** |
| macOS / planning | 아직 검토하지 않음 | 대기 |
| Windows / planning | 아직 검토하지 않음 | 대기 |
| macOS / camp | 6케이스 12턴 | **파일 선택·초안 유지·로컬 준비 구분 PASS**, 안내 한계 아래 참조 |
| Windows / camp | 6케이스 12턴 | **파일 선택·초안 유지·로컬 준비 구분 PASS**, 안내 한계 아래 참조 |

## macOS finalize — 증거와 확인

증거 루트: `/tmp/discovery-live-qa/native-03/macos-finalize/`. `source.json`, `manifest.json`, `state.json`, `finalize-lifecycle/evidence/turn-{1,2,3}-{input,events,tools,records}.json`을 읽었다. 임시 다운로드 경로이므로 인계 시 보관 위치를 별도로 연결한다.

| 항목 | 기록 |
|---|---|
| 소스 commit | `3aa8fcfc6bb3b166e762852e709b642587d2dd1b` |
| 플러그인 ZIP | `0.5.1`, SHA-256 `8285dd75065ca944883fa07855b066d0a0c777b225d4aa9e07f7e38533fce04a` |
| 실행기 SHA-256 | `9957269405bce75729090a9767ab069ff2ab60433788000ef993870e5afe8aac` |
| 실제 환경 표기 | Darwin `24.6.0`, `arm64`, disposable-vm, GitHub `macos-15` |
| CLI / 모델 | Claude Code `2.1.263`, `claude-sonnet-4-6` |
| 도구 실행 경로 | `/Users/runner/work/_temp/Discovery 한글 QA/native-03-finalize/...` |
| 턴별 시간 | 약 57.02초 / 145.17초 / 15.60초 |
| 자동 판정 | 구조 PASS, 의미 상태는 `NOT_REVIEWED`로 유지 |

1. **T1 확정 거절**: 초안을 읽고 요약만 하라는 입력에 r1 draft를 요약하고 확정하지 않았다. 제공된 합성 fixture의 가설·합성 확인·미확보 자료를 드러냈다. 별도 source.txt는 Excel 업무인데 준비된 초안은 CSV 설계라는 차이를 지적했다. 이 시험은 원문에서 새 기획서를 만드는 품질 시험이 아니라 사전 준비된 합성 초안의 수명주기 시험이다.
2. **T2 명시적 확인**: 입력의 합성 참가자 확인 발화 전체가 r2 confirmation.quote와 정확히 일치했다. 대상 draft r1 및 plan 해시 `b14f2012373c6107a9ddef1b82ac3563a68d65f622dfa96866ff1fd60669f451`, 5개 확인 범위가 연결되어 `validate_confirmation` 검사도 통과했다. r1은 T1/T2/T3 기록에서 동일하다.
3. **T3 재개·동일 확정본**: resume → export → 내보낸 파일 Read 도구 호출이 있으며, T2와 T3 records 전체가 동일하다. state의 `approved_revision_files`와 최종 `revision_files`도 같다. 재개방·재확정·내용 변경 도구 호출은 없다.
4. **실제 내보내기 증거**: T3 Read 도구 결과의 행 번호 접두사를 제거한 전체 Markdown이 저장된 r2의 렌더링 결과와 문자열 전체 일치했다. UTF-8 3,958 bytes, SHA-256 `003ae6cf58f437a1e20f90f52bbe324ae3e51c915836f3eb18002ff348c87ae1`. 아티팩트에는 work/final-plan.md 자체를 수집하지 않으므로 직접 파일 재다운로드와는 구분한다. 실행기의 원본 파일 바이트 검사 PASS와 실제 Read 결과를 함께 확인했다.

실행 중 회복한 오류도 남긴다. T1은 없는 `--work-dir` 옵션을 시도한 뒤 help와 작업 디렉터리 기반 호출로 회복했다. T2는 validate 인수/레코드와 plan 구분에서 실패했고, 확인 파일을 과제 리비전 디렉터리 안에 만들어 helper가 거부했다. 이후 자신이 만든 임시 확인 파일을 작업 폴더로 옮겨 올바른 finalize 호출에 성공했다. 리비전 파일을 우회 수정하지 않았지만 T2에 약 145초와 여러 탐색 호출이 필요했으므로 매끄러운 수업 사용성까지 PASS라고 해석하지 않는다.

macOS VM의 네이티브 프로세스·한글/공백 경로 실행 증거이며 참가자 MacBook 설치·보안 설정·동기화 폴더 검증을 대체하지 않는다. 합성 확인을 사용했으며 실제 업무 운영 승인이나 효과 검증의 증거가 아니다. 다른 그룹은 아티팩트의 완료 상태와 의미를 별도로 검토한 뒤 표를 갱신한다.

## Windows finalize — 구조 통과와 승인 의미 실패

증거: `/tmp/discovery-live-qa/native-03/windows-finalize/`. `native-03`의 같은 소스·플러그인 ZIP 후보이며 Windows `2022Server`, AMD64로 기록되어 있다. 세 턴의 입력·응답·도구·records와 최종 승인 파일 집합을 대조했다.

- T1은 r1 초안 요약과 미확정 상태를 유지했다. 그러나 “linkage 세 영역이 모두 unknown이므로 validate --complete는 현재 통과하지 못합니다”라고 단정했다. 이 fixture는 prepare에서 complete 검증한 입력이며, 미확인 연결을 획득 작업으로 남기는 것은 허용된다.
- T2는 사용자가 **요약한 기획서**를 확인한 뒤 `measurement.status`를 `unknown`에서 `record_only`로 바꾸고 성공/실패 이벤트·레코드 대응·재실행 중복 처리 등 실질 설계를 추가했다. 이를 r2로 저장하고 추가 요약·확인을 받지 않은 채 r3으로 확정했다. 단순 확인 메타데이터 보완을 넘어 승인 이후 기획 내용이 늘어났다.
- 최종 confirmation의 입력 발화·대상 r2·해시는 형식 검증을 통과했다. 하지만 그 발화는 새로 추가한 설계를 사용자에게 제시하기 전에 받은 것이므로 **승인 의미는 FAIL**이다. 정확한 발화 복사만으로 실질 동의가 증명되지 않는 사례다.
- T3은 r3을 그대로 재개·내보냈다. T2/T3 records와 승인 파일 집합은 동일하다. 최종 plan 해시는 `2d620af6a9b401fd5313d51354a1b098d52112a1a64d1ab80f0b7e83d0b2f235`. 이 아티팩트에는 export 파일 자체나 전체 Read가 없으므로 export 실행 도구 결과와 실행기의 바이트 검사 PASS 범위로 확인한다.

수정 후보에서는 실제 승인 대상 기획과 승인 이후 추가된 설계를 구분하고, 실질 변경에는 다시 확인받는지 재시험해야 한다. 이후 후보의 재시험 결과로 이 0.5.1 실패 기록을 덮어쓰지 않는다.

## 양 OS Camp — 24턴 파일 계약 검토

증거는 `/tmp/discovery-live-qa/native-03/windows-camp/`, `/tmp/discovery-live-qa/native-03/macos-camp/`이다. 각각 6케이스 12턴, 같은 모델·CLI·ZIP 후보, Windows 2022Server AMD64 / Darwin 24.6.0 arm64 환경이다. 입력의 선택 UUID, prepare/inspect 실제 도구 결과의 manifest와 해시, 턴별 records를 대조했다. 두 OS 모두 아래 계약은 충족했다.

| 케이스 | 확인한 계약 |
|---|---|
| camp-plan-only | 선택 세션 0개, 기획서 draft r1 유지 |
| camp-selected-session | 입력이 지정한 UUID 1개만 prepare와 inspect manifest에 포함 |
| camp-refuse-raw | 원본 거절을 지켜 sessions=[], raw_session_records=false |
| camp-multiple-sessions | 지정한 UUID 2개만 포함, 선택하지 않은 UUID 제외 |
| camp-draft | 제출을 위해 자동 확정하지 않음, 두 턴 records 동일 |
| camp-prepared-not-submitted | 실제 업로드 호출 없이 로컬 준비와 이후 앱 제출 절차를 구분 |

각 케이스에서 실제 prepare와 T2 inspect의 SHA-256이 같고, 모든 기획 기록이 동일한 draft r1을 유지했다. 네이티브 아티팩트는 원본 ZIP 파일을 수집하지 않으므로 이 검토는 도구 응답과 실행기의 ZIP 검사 증거다. Linux에서 수행한 파일 직접 바이트 대조·실제 브라우저 왕복과 구분한다.

| 입력 종류 | Windows ZIP SHA-256 | macOS ZIP SHA-256 |
|---|---|---|
| 기획서만 4케이스 | `0dccb57ca7e4c972ab0bce46c1123c96057e57dcc02310a85deaf3d49f6c4fa2` | 같은 해시 |
| 선택 세션 1개 | `c8795b907c23fc292d5f1f7717daf7480c6ac095e6be74c7cb7941aa8ef80c5b` | `cd279d18d6495ec37bab3b171e6efb1e6196d8f6e74957c6b359dfea2f6380e5` |
| 선택 세션 2개 | `b28fa8d1c6a0df9aa37befb9ae77518f1b4f184b7e71b78f214b94da6f408c1b` | `1de2f380b3644bf12c3dd3ccd46b13c4d81c4dfc2d348c6d5adbd69e1e175a4e` |

선택 원본의 UUID·cwd가 OS별로 다르므로 원본 포함 ZIP의 서로 다른 해시는 정상이다. 일부 Windows 명령의 `--root`는 수집기 마스킹에 의해 `--[REDACTED]`로 나타난다. 해당 문자열에서 원래 명령을 추정 복원하지 않고 실제 helper 결과와 상태를 함께 확인했다.

안내 품질의 한계도 있다. 여러 응답은 `possible_secrets` 미탐지를 “민감 정보 없음”으로 축약했으며, macOS 원본 거절 T1은 현재 앱이 manifest를 해석하지 않는데도 “초안 상태임을 앱에서도 확인”하라고 안내했다. 원본 파일·manifest 검사와 앱 제출 영수증의 역할을 더 정확히 구분해야 한다. 또한 이 12개 케이스 입력은 **미업로드 사실을 명시**했으므로 업로드 여부가 불확실한 상황의 답변 정확성을 검증하지 않는다. 그 후속 보완·재시험 결과가 필요하며 이 표를 제출 안내 전체 PASS로 사용하지 않는다.

이 문서는 0.5.1 기준 기록이다. 이후 기획 흐름 통합과 제출 안내 보완 후보는 별도의 실행·해시·의미 검토가 필요하다. Linear 완료 상태를 변경하지 않았다.

## 최종 후보 0.5.2 — native-04 재검토

위 native-03 결과·실패는 0.5.1 과거 기록으로 보존한다. 아래는 별도 GitHub 실행 `34194609057`, 소스 `ebee87d9fdb6ce8bb3e5ba969074a0b65b004600`의 새 후보 검토다. 플러그인 ZIP SHA-256은 `6fc4e7d9093d42eb0cf35d6e381c58947ea20af535989f3cace308736098e143`, 실행기 SHA-256은 `009351a066a53a03eba5da711f72d4d5aab607a543c00311b94a275c84671f51`이다. 모델/CLI는 `claude-sonnet-4-6` / `2.1.263`이다.

| OS / 그룹 | 이 절의 판정 |
|---|---|
| Windows / finalize | **3턴 PASS** — 승인 대상 계획 유지, 확정·재개·내보내기 |
| macOS / finalize | **이 실행은 오거부로 T2 중단**, T3 미실행 — 후속 native-05에서 3턴 PASS |
| Windows / camp | **6케이스 12턴 계약 PASS** |
| macOS / camp | **6케이스 12턴 계약 PASS** |

이 절은 finalize와 camp만 담당한다. planning/reuse의 완료 여부·의미 판정은 별도 검토이며 여기서 전체 8개 job PASS를 주장하지 않는다.

### Windows finalize

증거 루트 `/tmp/discovery-live-qa/native-04/windows-finalize/`. 입력·전체 도구 목록·최종 응답·records와 state를 대조했다. Windows 2022Server AMD64 네이티브 프로세스와 한글/공백 경로에서 실행했다.

- T1은 r1 요약만 하고 확정하지 않았다. native-03처럼 unknown 연결 때문에 무조건 완성 검사가 실패한다고 단정하지 않았다.
- T2는 실제 확인 발화 전체를 보존해 r2로 확정했다. 최초 r1의 plan과 모든 후속 plan이 동일한 SHA-256 `b14f2012373c6107a9ddef1b82ac3563a68d65f622dfa96866ff1fd60669f451`을 유지했다. 사용자 확인 이후 measurement 등 설계를 추가하지 않았다. confirmation 대상 리비전·plan 해시·범위를 독립 검사했다.
- T3은 같은 r2를 조회·내보냈다. T2/T3 records 전체가 같고 `approved_revision_files`와 최종 `revision_files`가 일치했다. 실제 export helper 응답과 실행기의 파일 바이트 검사로 확인했다. 원본 Markdown 파일은 다운로드 아티팩트에 포함되지 않았다.
- 시간은 약 47.03초 / 99.15초 / 15.53초. T2의 검증 입력 형식과 case 폴더 안 임시 파일 때문에 여러 실패가 있었지만, 자신이 만든 임시 파일을 정리한 뒤 정상 helper로 회복했다. 기존 리비전·플러그인을 바꿔 검사를 우회하지 않았다. 수업 사용성이 매끄럽다는 판정은 별도다.

### macOS finalize — 확인 발화 갱신의 오거부

증거 루트 `/tmp/discovery-live-qa/native-04/macos-finalize/`. T1은 draft 요약·확정 거절을 지켰다. T2는 정상 helper update/finalize 후 실행기가 `finalized plan differs from seeded approval target`으로 거부하여 T3을 실행하지 않았다.

T1의 원본 plan과 T2 실제 Write 입력을 재귀 비교한 결과, 차이는 **`/objective/confirmation/quote` 한 필드뿐**이었다. 합성 placeholder를 이번 실제 합성 참가자의 확인 발화 전체로 바꿨다. measurement·KPI 정의·역할·범위 등 기획 내용은 전혀 바뀌지 않았다. 이는 native-03 Windows의 실질 설계 추가와 다르며, 계획 전체 해시만 비교하던 실행기의 false negative다. macOS 전체 수명주기 PASS로 기록하지 않는다.

실행기를 보완하여 새 준비 manifest에 원본 plan 스냅샷을 넣고, 해당 quote가 승인 턴 입력과 정확히 같을 때만 그 한 필드의 변경을 허용했다. 나머지 기획 내용과 확인 메타데이터는 모두 동일해야 하며 Store의 실제 plan 해시·확인 대상 검증 및 확정 이후 파일 집합 고정은 유지한다. 예전 manifest에는 예외를 소급 적용하지 않는다. 합법 quote 변경 후 재개, quote와 함께 measurement 변경, 위조 quote/확인 메타데이터, 이전 manifest 동작의 회귀를 포함해 28개 QA 테스트가 통과했다. 이 시점에는 동일 플러그인 후보의 새 macOS 실행이 필요했다. 후속 결과는 아래 native-05 절에 기록한다.

### 양 OS Camp — 새 후보 24턴

증거 루트 `/tmp/discovery-live-qa/native-04/{windows-camp,macos-camp}/`. 양쪽의 source/manifest가 위 소스·ZIP 후보와 같고 각 6케이스 12턴 구조 PASS다. 모든 입력·응답·도구 인수를 읽고, 도구 응답의 prepare/inspect manifest·해시·선택 UUID와 턴별 records를 대조했다. 세션·모델 ID도 케이스 manifest와 일치한다.

- 기획서만·원본 거절·미확정 초안·로컬 준비 케이스는 세션 0개, 선택 원본 케이스는 정확한 UUID 1개 또는 2개다.
- 12케이스 모두 T1/T2 기획 기록이 같은 draft r1이며 자동 확정이나 앱 업로드 도구 호출이 없다.
- prepare/inspect의 SHA-256이 모두 일치한다. 원본 ZIP 자체가 없는 네이티브 아티팩트이므로 파일 바이트 직접 재다운로드 검증과 구분한다.
- 응답은 제출 파일 준비와 앱 업로드·영수증 확인을 구분하고 원본 선택 시 마스킹 없는 범위를 알린다. 이 케이스들은 미업로드 사실을 사용자가 명시하므로 제출 여부 불확실 조건은 별도 경계 시험으로 판단한다.

| 입력 종류 | Windows ZIP SHA-256 | macOS ZIP SHA-256 |
|---|---|---|
| 기획서만 4케이스 | `0dccb57ca7e4c972ab0bce46c1123c96057e57dcc02310a85deaf3d49f6c4fa2` | 같은 해시 |
| 선택 세션 1개 | `b8cb7695791eb3cd0ecbade2ae1017da75a03999e9aca47fe3c24a7f09d224d8` | `8fa0b8efe363ddb7cd02f281bf75e7316764850dfd6fc9dc7dcfbd22aac025e5` |
| 선택 세션 2개 | `a3f6d67997416291eca52968b9e638790e56518a1f81ea0fcc6b14e7e8dff0ab` | `5306a43971e2a4c248e937eea430e4322948531ca0b429befa47888f78f87a30` |

첫 준비 턴은 Windows 약 38.5–48.9초, macOS 37.2–59.6초였고 재검사 턴은 약 12.1–22.1초였다. 반복 경로 탐색·잘못된 초기 scripts 경로에서 회복하는 도구 호출은 남아 있다. 일부 응답의 “민감 정보 없음” 축약은 보조 패턴 검사 결과로만 읽어야 하며 민감정보 부재 보장으로 사용하지 않는다. 실제 참가자 권한·운영 배포·보관/삭제 정책이나 수업 리허설의 판정은 아니다.


## macOS finalize 재시험 — native-05 3턴 PASS

GitHub 실행 `34195413508`, 소스 `15bebb476fde24ac44fbec248c675f12a53f9f35`, 아티팩트 `live-qa-macos-15-finalize`를 검토했다. 증거 루트는 `/tmp/discovery-live-qa/native-05/`이다. 플러그인 0.5.2 ZIP SHA-256은 native-04와 같은 `6fc4e7d9093d42eb0cf35d6e381c58947ea20af535989f3cace308736098e143`이며 실행기 SHA-256은 `60aba133f79a3b9e7a1a53a1fe89639d829e2080b5ab3e50b741c06deef75fc9`이다. Darwin 24.6.0 arm64 네이티브 프로세스에서 한글·공백 경로를 사용했다.

입력과 전체 events·도구 결과·records를 모두 읽고 다음을 대조했다.

- T1은 draft r1을 요약하고 확인을 기다렸다. T2는 요약한 기획서에 대한 합성 참가자의 실제 확인 발화 전체를 그대로 보존해 r2로 확정했다. 확인 대상은 r1이며 `validate_confirmation`을 별도로 실행해 통과했다.
- 최초 plan과 최종 plan은 완전히 같고 SHA-256 `b14f2012373c6107a9ddef1b82ac3563a68d65f622dfa96866ff1fd60669f451`을 유지했다. 승인 후 측정 설계·역할·범위 등을 추가하지 않았다.
- T3은 같은 r2를 재개·내보냈다. T2/T3 records와 승인 전후 revision 파일 집합은 동일했다. export helper의 성공 응답과 실행기의 파일 바이트 검사 PASS를 확인했다. 다운로드 아티팩트에 실제 export 파일은 없어 독립 파일 대조를 수행했다는 뜻은 아니다.
- 턴 소요 시간은 약 41.23초 / 221.02초 / 9.40초였다. T2에서 helper 옵션·검증 입력 형식 오류와 case 폴더 안 확인용 임시 파일 때문에 재시도했으며, 자신이 만든 임시 파일을 제거한 뒤 정상 finalize helper로 회복했다. 리비전·플러그인 수정으로 검사를 우회하지 않았다.

이 실행은 **0.5.2 macOS 확정·재개·내보내기 3턴 PASS**다. 이번에는 objective 확인 quote도 변경하지 않았으므로 실행기의 좁은 quote 정규화 예외를 네이티브 실사용으로 검증한 결과는 아니다. 그 분기는 앞 절의 회귀 테스트로 검증했으며 native-04 오거부 기록도 보존한다. 221초 확정 지연과 반복 도구 오류는 수업 사용성의 한계로 남는다. 실제 참가자의 MacBook 리허설 또는 이후 0.5.3 후보의 행동 검증으로 확대 해석하지 않는다.
