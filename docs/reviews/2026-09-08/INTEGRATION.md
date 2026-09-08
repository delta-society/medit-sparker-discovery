# DEL-480 / DEL-482 통합 후보 — 2026-09-08

## 범위

기준 main `8d1f705f6b754f22d0380db09b0490d91a5fc90a`에서 별도 `codex/del-480-482-qa` 작업 디렉터리를 만들고, 아래 33개 미커밋 파일의 내용을 고정했다. 원래 작업 디렉터리를 수정하거나 기존 변경을 정리하지 않았다.

- DEL-475/476: 적대적 리뷰 재현·저장 CRLF/크기/공개 전 검증과 회귀
- DEL-477/478/479: 정확한 배포 목록·UTF-8/경로 보완·OS별 CI 작성
- DEL-487/488: Camp 제출 기능·합성 세션 검증·실제 앱 격리 HTTP 왕복 재현 스크립트와 기록
- DEL-482 신규: 실제 Claude QA 실행기, 12개 합성 시나리오(26턴), 실행 절차, 실행기 회귀 및 CI 연결

병행 DEL-474의 PDF 구현은 이 스냅샷에 없으며 포함하지 않는다. Camp 정책 확정(DEL-489), 실제 Claude QA(DEL-483/484/485/490), 리허설과 교육 배포(DEL-441/486)는 완료 범위가 아니다. 내부 소스 브랜치 게시와 검토 가능한 PR이 DEL-480의 게시 산출물이며 main 병합이나 고객 배포를 뜻하지 않는다.

## 가져온 파일의 기준 해시

아래는 **작업 시작 때 복사한 내용**의 SHA-256이다. 이후 적대적 리뷰 보완은 최종 Git diff와 리뷰 기록으로 구분한다. 최종 게시 내용의 정본은 PR commit SHA다.

| 파일 | 시작 SHA-256 |
|---|---|
| `.gitattributes` | `0bb9568fcbb11db1d305f521ff02e034c12a19b69d7e10cc7b1b8d48363712a9` |
| `.github/workflows/compatibility.yml` | `11450f433dbbde81a562dd539ad48f4033cb48e71f599bd61092fca975b8e8ae` |
| `.gitignore` | `04e61fe84234e8f607fff4863925d13ff8d319fcdfc8e35ac50f7e06ae554127` |
| `SPEC.md` | `311a69ed8df8ad328fcd73dc6838813c96f3c7d2b6500f3e58383b9ba0bdc0e6` |
| `docs/camp-submission-verification.md` | `bc600245fc34ca7e3f27b0048e1aa9c3ad25c007fd450774855d9c4d33104e3d` |
| `docs/camp-submission.md` | `e7f175d824c5bdf7b40448328e957792661c10c4e64b039a962d58d6d51558c7` |
| `docs/platform-compatibility.md` | `37d830b27a0f2996a81b131af57d92da326a46c7e51393331f0bb27769a176e0` |
| `docs/plugin-guide.md` | `f98f3c32f5cbbe2745f9ab941cf32981fcca9ae1e985cf804ee834b17944abdb` |
| `docs/reviews/2026-09-08/REMEDIATION.md` | `b15266cc93473028dd5f472f320736de7ab0c957d26624c8e3e9cf61b97c8a84` |
| `docs/reviews/2026-09-08/REPORT.md` | `4016550aeb51df27c93b5a963dbe196d0bbd45e1bfcd363703b52ba0fc13f30d` |
| `docs/reviews/2026-09-08/reproduce.py` | `9aa3d0431ce722a816039aa89efc2776d8df4cfdd5c6e23eb280df8911db9faf` |
| `docs/session-handoff.md` | `9c0539387c1721151c0f1037ec1c6c9546b41f2167913add69181b2142073499` |
| `plugin/.claude-plugin/plugin.json` | `e56384387891acf4b2a492389edcabda4e9e54a7f3d81da4e50ab58ea9156d84` |
| `plugin/references/data-contract.md` | `28ce41cefda1f487f5d8da06005d970a8167279884a47537037bb73fc8828e60` |
| `plugin/scripts/camp_submit.py` | `54b238002c06c4076e50a8fca20b9b77f4bb8ac32394b9b37b0f685ae7aa1cf6` |
| `plugin/scripts/example.py` | `f0c31c17c68b014fcf65108061b91cac046bddfb2df9072801c136b7825c3f59` |
| `plugin/scripts/kpi.py` | `7585862a9d176c286e6367e6e617f32101383987e006396dd45a6b18f0d71788` |
| `plugin/scripts/plan.py` | `1167f1894382fb13efba6693444ca5317aaaf0a17e3c3200b51537cee369218d` |
| `plugin/scripts/portable.py` | `86cf958cfa7dff13d5698205f21dadd76ef726d51a0b7a8fc3f819b69acc00e2` |
| `plugin/scripts/submission.py` | `5291b63b471cc87ee8bdf926d43f4c62a9774399e49097d874e4d049f9f41e8c` |
| `plugin/skills/plan/SKILL.md` | `cd3a365aff697d06f31335f0d7f3ec4e5e89af1b539dd539d48664bff9afd07f` |
| `plugin/skills/submit/SKILL.md` | `c68009d8692c73e0d7c5842103057f653320ce4a8f09ede054b0860c15b93bf0` |
| `plugin/tests/test_camp_submit.py` | `e47b5ee04ba4636459582f479307750c50a2f398f82b746e90887453738b83e1` |
| `plugin/tests/test_kpi.py` | `d7216206b487da751bb2adf4ce6037bc79a9a6e348cbb5a5f1455a3daa8e7516` |
| `plugin/tests/test_linkage.py` | `2e35654143159dd94cb29ec7a6b00574aa3c84941fd4c11fbd21f7e2ee7c0c87` |
| `plugin/tests/test_package.py` | `86069eebf48e99cf2a59aee6ea8cbb16fcc1f341e0371b79a1824a8e8185b2fc` |
| `plugin/tests/test_plan.py` | `dafa81890e7d6eb8cb76b9938d4e3c0cb3f4525ae6feb2eeef5fd8ff5f1e2623` |
| `plugin/tests/test_platform.py` | `3ff59b0ff5e71476d06dad7dcd3eeea9794d2943906037f260ef5b418b5bf392` |
| `plugin/tests/test_product.py` | `d39a7e8c4b2c97b1cfbaa13b250f2e15b38e217aefa2889ac5bbb84db7d05124` |
| `plugin/tests/test_storage_regressions.py` | `a1376fe2e454e68be20d3e36f21f4c85246d9fb63cce768fba248add018383a7` |
| `plugin/tests/test_submission.py` | `7905a106887f51c15c96aca397da54d3e05210ebb5d8497ff1805b042e90772d` |
| `scripts/build-package.py` | `470ef396dd57c1065ede0af8de6b69881d9cb224ff16171197771a67c24814c5` |
| `scripts/verify-camp-roundtrip.py` | `39a090cecfd0fdc4af5e16e8cdad1b35472f134ef042a082c6cd591f2094c8b2` |

## 검증 구분

로컬 helper/합성 회귀, ZIP 해제 후 실행, manifest 검증을 수행한다. 기존 검증 문서의 테스트 개수/ZIP 해시는 각 문서 시점의 기록이며 이 통합 후보의 결과로 재해석하지 않는다. 최종 실행 수치와 2기 리뷰·보완·재리뷰 결과는 `QA-REVIEW.md`에 기록한다.

CI는 소스 게시 시 실행될 수 있으나, 통합/실행기 준비와 실제 OS별 결과 수용은 구분한다. 원격 SHA 및 파일 readback 이후 Linear에 실제 파일 링크를 붙인다. 실모델 호출이 없는 회귀 테스트를 실제 대화 QA 통과로 기록하지 않는다.
