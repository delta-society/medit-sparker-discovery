# 제품 기획 전용 플러그인 검증 — 0.3.0

이 문서는 0.3.0 당시의 검증 이력이다. 활성 경계는 [0.4.0 목표·연동 검증](objective-linkage-verification.md)으로 대체됐다. 아래 “현재”는 당시 기준이다.

당시 기능 경계는 SPEC 「제품 기획 플러그인 책임 경계」를 따른다. 회사/과제의 주어진 목표·제약을 제품 명세로 구체화하며 회사 정합성 판정·KPI·전후 효과 측정은 별도 프로그램 소관이다. 그 프로그램의 구현/연결은 이번 변경에 포함하지 않는다.

## 변경과 호환성

- 활성 SKILL·대화·대표 사례 명세·저장 계약·사용 안내에서 지표 설계/효과 수집 질문과 완료 요구를 제거했다. 원문 선반영, 객관식/주관식 혼합, 제품 계산의 미확인 규칙, 기술적 정상/예외 시험은 유지한다.
- `plan.py template --product`는 제품용 입력을 제공한다. 신규 제품 명세는 KPI/기준선/비교/병목 근거 필드 없이 완성·확정 가능하다. `planning_scope: product`의 Markdown은 제품 필드만 출력한다. 과거 근거·지표·확인 발화가 인계 문서에 자동 복사되지 않는다.
- 과거 모드의 Markdown 렌더러는 그대로 유지한다. 이전 기록을 다시 렌더링하는 무결성 검사와 JSON 해시·리비전 체인·사용자 확인 계약은 보존한다. 과거 기록 수정은 새 리비전에만 적용한다.
- `submission.py --product`는 원문을 보존하면서 제품용 선반영 값과 질문 범위만 제공한다. 회사 ST 산식은 발명하지 않는다. 기존 검토 절차를 승인 관리 앱으로 확대하지 않는다.

## 실행 근거

`python3 -m unittest discover -s plugin/tests -v`: 54 tests PASS. `claude plugin validate ./plugin`: PASS. 제품 모드 완료/확정·기술 시험 누락 거부·레거시 저장 읽기·입력 마커 검사·기록 제외 출력·원문 선반영을 포함한다. 기존 회귀(불변 이력·동시 쓰기·주입/경로 거부·AR/ST 계산·과거 KPI 계산)도 통과했다.

ST 대화 과제는 기존 r000010에서 r000011 초안으로 갱신했다. `validate_plan(complete=True)`와 저장 readback을 통과했고 이전 20개 파일의 SHA256이 전부 그대로다. 입력/획득/시험/구현 단계에서 효과 측정·승인 관리 기능을 제거하고 템플릿과 측정 가이드를 유지했다. 전달 사본: `~/deliverables/st-product-plan.md`. 기획서 확정·실제 ST 계산 제품 구현/시험 통과를 뜻하지 않는다.

배포 파일: `~/deliverables/sparker-discovery-plugin-0.3.0.zip`. 빌드 후 압축 내 전 파일과 소스 바이트 일치를 확인했다. ZIP 직접 로딩은 Claude Code 2.1.205 CLI에서 지원하며 이번 배포물은 Claude Code용이다. 출력 Markdown은 Codex에 전달할 수 있으나 Codex 네이티브 플러그인 설치/실행을 검증한 것은 아니다.

실제 Claude Code 대화는 최종본 통과 미검증이다. 첫 시도는 기본 인증 없음으로 중단됐고, 기존 승인된 OpenRouter 경로로 재실행했다. ZIP의 스킬·원문/제품 template 도우미 호출까지 실제 실행됐으나 남아 있던 baseline 작성 지침 때문에 잘못된 unit을 생성해 저장 검사에서 거부됐다. 이어 API가 HTTP 402(in-flight 요청 포함 가용 크레딧 부족)를 반환했다. baseline 작성 지침의 잔여 문구를 SKILL·예시·데이터 계약·대화에서 제거한 뒤 54개 회귀·패키지 검사와 ST 저장 재조회를 다시 통과했다. 비용/계정 변경은 하지 않았다. 최종 ZIP의 전체 LLM 대화 생성·저장은 통과로 주장하지 않는다.

최종 ZIP SHA256: `f49c37ffc8386887b2b165a976afc969973db05f4095355dea35aa47c226d0ce`. 최종 영수증: `/Users/Shared/DeltaSocietyOS/audit/sparker-product-planning-20260908/verification.json`; 중간 실패: 같은 디렉터리의 `native/` 및 `../sparker-product-planning-retry-20260908/native/`.

## 재현

1. `python3 scripts/build-package.py --output <새 ZIP 경로>`로 패키지를 만든다.
2. 새 실습 폴더에서 `claude --plugin-dir <ZIP 경로>` → `/sparker-discovery:plan 예시 standard-time`으로 시작한다.
3. 이미 있는 엑셀·가이드 목표와 측정 계기는 재사용하고 제품 입력/규칙만 질문하는지 본다. 파일은 아직 없다는 후속 답변에도 구현 틀·자료 확인 이후 계산·정상/예외 시험까지 초안을 저장해야 한다.
4. 저장된 plan에서 `planning_scope=product`, 실제 `plan.md`, 기술 시험, 미확정 상태를 읽는다. KPI 질문·기준선 입력 강요·승인 계정/집계 기능·임의 회사 산식·가짜 시험 통과가 없어야 한다.

사용자는 수정 ZIP으로 새 세션을 시작한다. 기존 과제 폴더는 삭제하지 않는다. 새 기획서 전체에 대한 사람의 확정은 별도이며, 이번 요청은 플러그인 수정과 검증이다.
