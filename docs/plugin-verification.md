# 플러그인·AR 명세 검증 — 2026-09-07

현재 수정본은 목적 KPI·기존 앱 연결 기획 **0.4.0**이다. 현재 범위와 검증은 [목표·연동 검증](objective-linkage-verification.md)을 따른다. [제품 기획 검증](product-planning-verification.md)은 대체된 0.3.0 이력이다. [원문 선반영 검증](source-first-verification.md)·[혼합 질문 검증](mixed-question-verification.md)·[KPI 검증](kpi-verification.md)은 과거 이력이며, 아래는 0.1.2 당시의 AR/ST 검증 이력이다.

## 생성 품질 후속 수정 — 0.1.2 이력

sung의 “그럼 생성 품질도 건드리면 안돼?”에 따라 SPEC S3의 생성 품질 수정까지 실행했다. `plugin/scripts/example.py`는 신뢰된 읽기 전용 AR/ST 대표 사례 도우미이며 사용자 코드·업무 시스템을 실행하지 않는다. 전제·계산·다음 행동·질문을 함께 출력하고 대표 결과 턴은 이 출력 전체를 보존한다. 회사 기준이 미확인이면 값뿐 아니라 산식도 미확인으로 둔다. 전체 기획서의 다른 절은 계속 작성한다. AR은 단일 통화·인보이스와 입금 대응·다른 조정 없음의 단순 예제, ST는 회사 산식 미확인 예제만 지원한다. 범용 기획 생성의 모든 판단을 코드로 검증한 것은 아니다.

- 단위 회귀: 새 도우미 12개 + 기존 저장 도우미 14개 = `python3 -m unittest discover -s plugin/tests -v` 26 tests PASS. 매니페스트 검사 PASS. 과거 확정 이력·기존 저장 렌더러는 변경하지 않았다.
- **최종 ZIP 실제 Claude Code 대화 5회 PASS:** 아래 모든 응답은 실제 도우미 호출, 최종 답변 전체의 기대 출력 일치, `is_error=false`, 저장하지 말라는 요청 준수까지 확인했다. 명령: `python3 scripts/verify-generation-audit.py /Users/Shared/DeltaSocietyOS/audit/sparker-generation-quality-final` (exit0).

| 실제 시험 | 기대 및 관측 결과 | 응답 ms |
|---|---|---:|
| AR 반영·기준시점 미확인 | 회수 금액 미확정, 확인 행동만 표시 | 33120 |
| AR 이미 반영·시점 확인 | SAP 미결 600 EUR 유지, 재차감 없음 | 38783 |
| AR 미반영·시점 확인 | 600−300=300 EUR, 반영 필요 확인 | 37757 |
| 같은 대화 후속 보정: 이미 반영·시점 확인 | 기존 입력 재사용, 600 EUR 유지로 갱신 | 12725 |
| ST 회사 산식 미확인 | 입력과 총 가공시간만 표시, ST 산식·값 모두 미확정 | 25948 |

입금 대응·동일 통화·다른 조정 없음의 제한을 표 앞에 명시했다. 임의 aging 구간·정상/경고 판정을 만들지 않는다. AR 첫 미확인 시험은 이전 실패 때와 같은 프롬프트를 재사용했다. 프로세스 간 `--resume`은 스킬을 다시 호출해 현재 ZIP의 임시 경로를 새로 받았다.

- 최종 배포 ZIP SHA-256: `baa00ed164afa68ccfcb43d6cc42fcbcee1e0d42f0b04f06891f5af7a1ba7b42`. 원본 응답·프롬프트·도구 이벤트·패키지 해시는 `/Users/Shared/DeltaSocietyOS/audit/sparker-generation-quality-final/`. 비밀값·원시 런타임 로그는 제품 레포에 넣지 않았다.
- 중간 실패도 보존했다. `.../sparker-generation-quality-fix/`: 표는 맞지만 뒤의 질문 설명이 다시 SAP 금액을 잘못 차감. `.../sparker-generation-quality-release/`: AR 4회는 통과했으나 ST 값만 미확정으로 놓고 산식을 임의 제시. 각각 출력 전체 고정·ST 산식 출력 도우미 추가 후 재시험했다. 무변경 재시도로 좋은 응답만 고르지 않았다.
- 완료 범위는 이 대표 예제·후속 보정의 생성 품질이다. 다양한 실제 제출을 대상으로 한 전체 기획서 생성→저장→사람 수정·확정의 최종 패키지 다회 시험, 참가자 노트북·수업 리허설, 실제 데이터·운영 시스템 정확도는 별도 미검증이다. 단일 사례 도우미를 운영 회계 제품이나 범용 자동 검수기로 쓰지 않는다.

## 이전 변경과 완료 범위 (0.1.1)


제작 계약: SPEC S3의 sung 승인. AR 대표 사례의 상세 정본은 `examples/germany-ar/implementation-spec.md`; 처리 규칙·합성 정답·미확인 현업 가정·후속 구현 범위는 그 문서만 갱신한다. 참가자 과제 `case-4162bb7c`는 revision9의 사람 확정본을 바이트 보존하고 reopen 후 revision11 초안으로 갱신했다. 상세화에 이전 확인 발화를 승계하지 않았다.

스킬은 기존 저장 스키마/렌더러를 유지하고 `plugin/references/implementation-example.md`의 대표 입력→출력→사람 행동→데이터 규칙→정상/예외 시험→의미 검사 절차를 추가했다. 자료 미확인 시 실제 업무를 멈추거나 합성 예시를 실제 사실로 처리하지 않는다. 코딩 도구로 작성하는 것과 실행 중 LLM 사용을 구별한다.

## 이전 빌드 실행 근거 (아래 미통과는 후속 수정 전)

- `python3 -m unittest discover -s examples/germany-ar -v`: 12 tests PASS. 명세의 합성 계산만 검증. 상세 시험 목록과 결과는 AR 명세·`examples/germany-ar/executed/`.
- `python3 examples/germany-ar/reconcile.py --output examples/germany-ar/executed`: 정상 exit0, 실제 JSON/Markdown 출력. 실제 SAP/Citibank 조회·적요 추출·Excel·수동 판단 UI는 포함하지 않는다.
- `python3 -m unittest discover -s plugin/tests -v`: 14 tests PASS. 저장·수정·거절·확정·재개·불변 이력·경로/동시쓰기 검사. 스킬의 문장 이해나 현업 타당성의 자동 증명은 아니다.
- `claude plugin validate ./plugin`: PASS. 설치/사용자 노트북 검증과 구분.
- 실제 Claude Code / OpenRouter Sonnet4.6, ZIP 로딩 후 AR 대표 사례 최초 응답: exit0, is_error=false, 197715ms. 새 reference 로딩·대표 입출력 표·질문 하나·초안 JSON/Markdown 저장 확인. `find` 경로 탐색 권한거절1건 뒤 파일 도구로 진행했다. **품질 결함:** 은행 입금의 SAP 미반영 가정을 명시하지 않고 수정 필요를 표시했다. 이 결과는 품질 PASS가 아니며 추가 지침 후 재시험했다. 원본 audit: `/Users/Shared/DeltaSocietyOS/audit/sparker-plan-example-first/germany-ar/turn-1-result.json`, `.sparker-discovery/case-dear/r000001/`.
- 두 번째 원API 시험: exit0/is_error=false/73461ms, 저장 거절을 지켜 과제 폴더 없음. SAP 반영 미확인 시 금액 확정을 보류했으나 이미 확인한 두 용도를 다시 선택하게 묻고 미확인 aging 구간을 1–30일로 채웠다. 품질 미통과. audit `/Users/Shared/DeltaSocietyOS/audit/sparker-plan-example-first-final/ar-unknown-state/turn-1-result.json`.
- 최종 ZIP의 세 번째 원API 시험: exit0/is_error=false/69289ms, 저장 거절 준수. 같은 목적 재질문은 사라졌으나 **SAP에 이미 반영된 경우에도 300 EUR 회수 추적이라고 잘못 설명**했고, 근거 없는 aging 구간·정상/경고 처리를 제안했다. 반영상태뿐 아니라 기준시점의 전제 표시도 충분하지 않았다. 표면 형식 개선과 업무적 정확성을 구별하며 **최종 자동 대화 품질은 미통과**로 기록한다. audit `/Users/Shared/DeltaSocietyOS/audit/sparker-plan-example-first-release/ar-unknown-state/turn-1-result.json`.
- 최종 ZIP SHA-256: `887aa195f4c08374ce891a508f6f2ee4e01907bb08b10a7ea88d96b2af54e97b`. 스킬 지침이 바뀌었지만 이번 결과로 참가자 무검토 배포/명세 자동 확정을 권하지 않는다. 추가 프롬프트 반복으로 PASS를 만들지 않고 미통과 사례를 보존했다. AR 명세·합성 계산 코드의 통과 결과와 이 실패는 별개다.

## 배포와 미검증

배포 파일: `/Users/hermes/deliverables/sparker-discovery-plugin.zip`, 플러그인 0.1.2. 최신 통과 범위는 첫 절을 따른다. ZIP 내용 검사와 SHA-256 영수증은 audit에 보존한다. 사용자에게는 기존 ZIP을 교체하고 Claude Code 세션을 다시 열도록 안내한다. 공통 설치/훅 레포·런타임·운영 서비스·외부 발신·main 병합은 변경하지 않았다.

현재 검증은 합성 계산과 제한된 실제 호스트 대화다. 여러 업무에서 첫 질문부터 보정·확정까지의 최종 패키지 다회 대화, 수업 시간 내 리허설, 실제 데이터 정답 대조·권한·보관·실패복구·처리시간은 미검증이다. 첫 응답 저장은 실제로 수 분이 걸렸으므로 교실 사용성이 검증됐다고 주장하지 않는다. 종전 백그라운드 exit0/timeout도 별도 빌드의 결과이며 이번 시험과 혼합하지 않는다.
