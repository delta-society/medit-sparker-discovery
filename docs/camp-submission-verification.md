# Camp 제출 기능 검증 — 2026-09-08

## 구현과 결과

`sparker-discovery` 0.5.0: `submit` 스킬, `camp_submit.py`, 배포 명시 목록, 참가자 안내, SPEC S15. 기존 0.4.2 저장/패키징 보완과 동시 진행 중인 플랫폼 호환성 작업을 보존했다. 기존 작업 전체를 이번 제출 기능의 신규 변경이라고 세지 않는다.

| 검증 | 확인 결과 |
|---|---|
| `python3 -m unittest discover -s plugin/tests -q` | 실행 시점 87개 PASS. 새 Camp 테스트 15개와 기존/병행 도우미 테스트 포함 |
| `python3 -m unittest discover -s examples/germany-ar -p 'test_*.py' -q` | 12개 PASS |
| `claude plugin validate ./plugin` | PASS |
| `skill-creator/scripts/quick_validate.py plugin/skills/submit` | PASS |
| `git diff --check` | PASS |
| 배포 ZIP 해제 후 CLI | 패키지 테스트에서 새 submit 도우미 prepare→inspect 및 기존 기획서 생성/재개 실행 PASS |
| 실제 참가자 앱의 격리 HTTP 왕복 | 아래 19개 확인 PASS |

## Camp 도우미 회귀

`plugin/tests/test_camp_submit.py`는 사용자 HOME/원본을 사용하지 않는 합성 테스트다.

- 기획서 단독 제출에서 환경 파일·미선택 대화·내부 JSON·로컬 경로 메타데이터 제외.
- 여러 세션 원본 바이트/CRLF 보존, 미선택 세션 제외.
- 순서가 다른 동일 선택도 동일 ZIP/해시, 기존 동일 파일 재사용, 변경 내용 덮어쓰기 거부.
- 오래된 리비전 거부, 기존 기획 기록 보존.
- 명시적 원본 선택, 중복 세션·다른 프로젝트·불명확/혼합 sessionId/cwd 거부.
- 잘린 JSONL·중복 JSON 키·UTF-8 오류·객체가 아닌 행 거부. 원본을 자동 잘라내지 않음.
- 압축/원본 크기 한도에서 실패하고 원본과 기존 출력 보존.
- 민감 키 후보는 유형/개수만 보고하고 실제 값은 결과에 출력하지 않음. 원본에는 그대로 있으므로 검토 필요.
- 입력·출력·상위 디렉터리 링크 거부. 읽는 동안 파일 변경 감지.
- ZIP 변조·목록 외 파일·중복·경로 탈출·잘못된 세션 기록 수 거부.
- 후보 목록은 선택 폴더의 최상위 파일만 조회하고 내용/하위 디렉터리는 읽지 않음.
- Linux/Windows 형식의 원본 cwd를 ZIP 검사에서 인식. 실기기 실행 인증은 아님.

## 실제 참가자 앱의 격리 HTTP 왕복

원격 소스: `delta-society/medit-sparker-leaderboard` main `439d2ba491cef5f2a4c01947a03a1577491672d9`. 별도 임시 체크아웃에 의존성을 설치하고 Next 서버를 loopback에서 실행했다. 새 임시 DB·합성 참가자 2명·임시 인증값·합성 기획서/세션 2개를 사용했다. 기존 운영 DB/계정·실제 참가자 원본·운영 앱에는 접속하거나 업로드하지 않았다.

검증 스크립트: `scripts/verify-camp-roundtrip.py`. 웹 API 모의 구현이 아니라 체크아웃의 실제 Next API 라우트에 HTTP로 요청했다. Next 개발 서버 검증이며 프로덕션 빌드/브라우저 UI 시험은 아니다.

1. 미로그인 업로드 401.
2. 합성 참가자 A 로컬 생성.
3. A의 실제 활성화·세션 인증.
4. 합성 참가자 B 로컬 생성.
5. B의 실제 활성화·세션 인증.
6. 잘못된 Origin 업로드 403.
7. 참가자 신원을 요청 본문으로 위조한 업로드 400.
8. 도우미가 만든 실제 ZIP 제출 201·제출 ID 반환.
9. 참가자 다운로드가 준비한 ZIP 바이트와 일치.
10. 다운로드가 attachment로 처리됨.
11. 내려받은 ZIP의 Camp manifest·해시 검사 통과.
12. 미인증 파일 조회 401.
13. 다른 참가자의 파일 조회 404.
14. 인증된 운영자 파일 조회 200·원본 바이트 일치.
15. 재업로드는 다른 제출 ID로 기록됨(멱등 API가 아님).
16. 이전 제출 파일도 내려받을 수 있음.
17. 대시보드에 제출 이력 2건·활성 제출 1건.
18. 과제 업로드가 토큰 사용량을 증가시키지 않음.
19. 5 MiB 초과 파일 거부.

해당 실행의 합성 제출 파일: 2,529 bytes, SHA-256 `7da2a130a2ae89be05fcc6dfa3253cf2e5ff746ed54c357fc899269bfa06cfc3`. UUID/임시 작업 경로가 달라지는 재실행의 파일 해시는 달라진다. 시험 서버와 임시 DB는 종료·정리했다.

재현(네트워크 설치는 별도 준비, 반드시 격리 체크아웃):

```sh
python3 scripts/verify-camp-roundtrip.py --app-root <위 SHA의 참가자 앱 임시 체크아웃>
```

## 배포 파일과 미검증

빌드: `python3 scripts/build-package.py --output /tmp/sparker-discovery-0.5.0.zip`.

검증 시 생성한 플러그인 ZIP: 21개 배포 파일, 71,407 bytes. SHA-256 `274b476fdaa1020f1fc9cfabbbcc3eb22f14fe42aa1f744aca669a2bcc0faf42`. 이는 합성 과제 제출 ZIP과 다른 파일이다. 빌드 시각/공유 작업 변경에 따라 재빌드 해시는 달라질 수 있다.

- 실제 Claude Code 모델과의 전체 제출 대화·사용자 기기 설치·Windows/macOS 실기기 시험은 수행하지 않았다.
- 원본의 모든 개인정보/시크릿 탐지·자동 마스킹은 제공하지 않는다.
- 제출은 참가자 앱에서 사람이 수행한다. 자동 제출 API·전용 원본 저장소·자동 분석·manifest 색인·회차 자동 선택은 구현하지 않았다.
- 현재 파일 업로드 경로의 5 MiB 한도·재업로드 시 새 이력은 유지한다.
- 캠프 운영자의 원본 허용 범위·열람/보관 정책과 운영 배포는 이번 내부 구현/합성 검증으로 확정하거나 완료하지 않는다.
- 커밋·main 반영·운영 서비스 배포·실제 참가자 자료 제출은 하지 않았다.
