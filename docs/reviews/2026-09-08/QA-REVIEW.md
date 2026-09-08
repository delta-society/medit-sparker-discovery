# DEL-480 / DEL-482 구현·적대적 리뷰·보완·재리뷰

## 결과

2026-09-08, 두 독립 서브에이전트의 1차 적대적 리뷰에서 고유 결함 3개를 확인하고 보완했다. 두 리뷰어의 재리뷰에서 기존 결함 해결을 확인했으며 추가 P1/P2 발견은 없었다. 리뷰어들은 파일을 수정하지 않았고 실제 모델/API·외부 서비스는 호출하지 않았다.

| 발견 | 보완 | 재현·회귀 |
|---|---|---|
| P1: Camp 합성 원본 a.jsonl/b.jsonl이 도우미의 UUID 파일명 계약을 위반 | 실제 UUID 파일명 생성, 프롬프트 경로 치환, 선택 UUID 고정·검사 | 선택 원본 1개/2개로 실제 도우미 ZIP 준비→검사 |
| P2: prepare의 입력 해시가 실행 때 사용되지 않아 원문·초기 Camp 리비전 변경 허용 | 실행 전·각 턴 전후 고정 입력 검사, 초기 리비전을 불변 비교 기준으로 포함 | 실행 전/중 원문 변조, 초기 Camp 리비전 변조 거부 |
| P2: 같은 폴더의 동시 실행에서 예산 예약 손실·중복 호출 가능 | 상태 읽기 전부터 종료까지 원자적 디렉터리 잠금 | 동시 호출 거부, 첫 호출 1회·예약 유지·잠금 해제 독립 재현 |

첫 리뷰어는 실행기 실패·재개·예산·증거 처리를, 두 번째는 통합 패키징·Camp 계약·OS 호환성과 실행기 연결을 검토했다. 한 리뷰어가 발견한 입력 무결성 결함은 다른 리뷰어도 독립 재현했다.

## 1차 보완 후 로컬 검증

- `python3 -m unittest discover -s plugin/tests -q`: 87개 PASS. 저장·포터블 인코딩·Camp·배포 ZIP 해제 실행 포함.
- `python3 -m unittest discover -s tests -v`: 15개 PASS. **가상 CLI 이벤트를 쓰는 실행기 회귀이며 실모델 QA가 아니다.** UTF-8 및 timeout subprocess는 실제 로컬 Python으로 검증했다.
- `python3 -m unittest discover -s examples/germany-ar -p 'test_*.py' -q`: 12개 PASS.
- 합계 114개 PASS. 두 번째 리뷰어가 위 세 묶음을 직접 재실행했다.
- `claude plugin validate ./plugin`: PASS.
- `git diff --check`: PASS.
- 12개 합성 시나리오, 총 26턴 준비 확인. prepare는 모델 호출을 하지 않으며 `PREPARED_NOT_RUN`으로 기록한다.

## 원격 Windows 실패 후 추가 보완·재리뷰

첫 게시 `bafab3a`의 [CI 실행](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34191264674)에서 Linux 3.9/3.13과 macOS 15는 통과했으나 Windows 두 job이 실패했다. 이를 완료로 남기지 않고 DEL-480/482를 다시 열어 보완했다.

- Windows Python 3.13: Camp의 `stable_read`가 `stat`과 `fstat`의 전체 시간값을 교차 비교하여 정상 재작성된 입력/ZIP을 읽기 중 변경으로 오판했다. 각 API의 읽기 전후 값을 비교하고 파일 식별자는 별도 교차 검사하도록 수정했다. 서로 다른 시간 기준의 안정된 파일 허용·실제 handle 변경 거부 회귀 2개를 추가했다. Windows 시간 필드의 이식성 근거: [Python stat 문서](https://docs.python.org/3.13/library/os.html#os.stat_result.st_ctime).
- Windows Python 3.9: 실행기 테스트의 전역 `subprocess.run` 대체가 `platform.win32_ver()` 내부 호출에도 가짜 bytes를 반환했다. Claude 버전 호출만 대체하고 OS 조회는 실제 호출로 위임했다. 실행기 제품 코드의 OS 수집은 유지했다.
- 두 서브에이전트가 변경된 3개 파일을 재검토했다. 추가 P1/P2 발견 없음. 로컬 플러그인 89개 + 실행기 15개 + 기존 AR 12개 = 116개 PASS. 실제 Windows 복구 판정은 수정 커밋의 원격 CI 결과로 기록한다.

## 완료 범위와 한계

DEL-482의 산출물은 실행기·합성 입력·운영 절차·회귀다. 실제 Claude 호출·인증 성공·대화 의미 검토·macOS/Windows 네이티브 실행·Camp 브라우저 업로드는 이 보고서에서 합격으로 주장하지 않는다. QA 실행기는 보안 샌드박스가 아니며 동일 OS 계정 악성 프로세스의 증거 조작 저항성도 인증하지 않는다. 환경 경계와 외부 감독 증거는 후속 실제 QA에서 확보한다.

DEL-480의 소스 게시 범위는 `INTEGRATION.md`와 최종 Git commit/PR이다. 원격 SHA·파일 readback 근거는 Linear에 기록한다. 원래 병행 작업 디렉터리와 미완성 PDF 변경은 보존했다. 고객 배포나 main 병합을 수행하지 않는다.
