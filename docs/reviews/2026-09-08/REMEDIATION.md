# 0.4.2 보완 결과 — 2026-09-08

대상: `8d1f705` 기반 작업 브랜치 `codex/insight-relay`. [원래 리뷰](REPORT.md)의 F1/F2/F3 수정과 로컬 검증을 완료했다. 커밋·push·운영 배포는 하지 않았다.

## 변경

| 항목 | 수정 | 검증 |
|---|---|---|
| F1 CRLF/CR 저장 후 접근 불가 | Markdown을 UTF-8 바이트로 비교. 원문·렌더러·레코드 스키마는 변경하지 않음 | LF/CRLF/CR의 legacy/linked 생성·수정·확정·재개·내보내기, 이전 파일 바이트 보존 |
| F2 ZIP 비공개 파일 혼입 | 18개 배포 파일을 명시적으로 지정. 임의 파일·실습 기록·테스트는 읽거나 포함하지 않음. 필수 파일 누락 및 배포 경로의 symlink/junction 거부 | 가짜 환경 파일·실습 JSON·추가 references/scripts/examples 파일·기존 ZIP 배제, 필수 파일 누락·링크 거부, 해제 후 도우미 실행 |
| F3 레코드 크기 초과 | 메타데이터·확정 발화까지 포함한 직렬화 결과에 2,000,000바이트 한도 적용 | 한글/ASCII 입력, 저장 한도 직전·동일·초과, update/finalize 거절 이후 원래 리비전 조회·정상 재시도 |

공통으로 staging 파일을 `load`와 동일한 리비전 검증 함수로 다시 읽은 뒤에만 rename으로 공개한다. 합성 Markdown 손상 주입 시 새 리비전이 공개되지 않고 이전 기록을 정상 조회·수정할 수 있다. 기존 lock·expected revision·해시 체인·사람 확인 범위는 유지한다.

F1은 기존 렌더링 계약의 호환성을 위해 줄바꿈 정규화나 스키마 버전 변경 대신 정확한 바이트 비교를 선택했다. 리뷰 재현 당시 0.4.1이 실제 기록한 CRLF 실패 리비전을 현재 코드로 읽고, 전후 모든 파일 SHA-256이 같음을 별도로 확인했다. 문서 표현 자체를 정규화하는 변경은 포함하지 않았다.

패키지 manifest는 0.4.2로 올렸다. 배포 파일 추가 시 `scripts/build-package.py`의 명시 목록도 검토·변경해야 한다. 기존 비공개 파일이 지정된 배포 파일 자체를 덮어쓴 경우까지 의미적으로 판별하는 기능은 아니다.

## 검증 결과

- `python3 -m unittest discover -s plugin/tests -q`: **70개 PASS**. 기존 62개와 신규 저장 5개·패키징 3개 테스트. 각 테스트 안의 줄바꿈·언어·크기·경로별 하위 시나리오 포함.
- `python3 -m unittest discover -s examples/germany-ar -p 'test_*.py' -q`: **12개 PASS**.
- `claude plugin validate ./plugin`: **PASS**.
- `git diff --check`: **PASS**.
- 최종 ZIP을 별도 임시 폴더에 해제해 Python CLI로 linked 기획서 생성→CRLF/CR 포함 수정→합성 확인으로 확정→resume→export→reopen→resume 수행: **PASS**. 실제 사용자 확인이나 LLM 대화 시험은 아니다.
- 리뷰 때 생성된 0.4.1 CRLF 기록을 재작성 없이 읽기: **PASS**.

빌드 명령:

```sh
python3 scripts/build-package.py --output /tmp/sparker-discovery-0.4.2.zip
```

검증한 ZIP: 18개 파일, 59,819바이트.
SHA-256: `37d50c498910f949f6fa89cacc04f772aacded0f5362cd25dbeac08fb3070af8`.
ZIP timestamp 때문에 재빌드 SHA는 달라질 수 있다. 이 값은 위 검증 시 생성한 파일의 영수증이다.

회귀 테스트는 `plugin/tests/test_storage_regressions.py`와 `plugin/tests/test_package.py`에 있다. `reproduce.py`는 수정 전 `8d1f705`에서 결함 존재를 확인한 역사적 재현 스크립트이며 현재 버전의 통과 검사로 사용하지 않는다.

## 남은 경계

- 이미 2MB를 초과해 저장된 옛 레코드는 자동 복구하지 않는다. 원본 보존을 전제로 별도 복구가 필요하다. 수정은 새로 잘못된 리비전이 생기는 것을 막는다.
- 실제 Claude Code 모델 전체 대화·프롬프트 주입 저항성·사용자 기기 설치·Windows/macOS 실기기·전원 장애 내구성은 미검증이다.
- 리뷰의 비참조 확보 작업 출력 정책과 최초 원문 지연 입력은 설계상 주의점으로 유지했다. 기획 완료 기준·비공개 정보 출력 경계는 바꾸지 않았다.
- Python helper 검증이 사용자 신원·실제 확인 발화·기획 의미의 타당성을 인증하지 않는다는 계약은 그대로다.
