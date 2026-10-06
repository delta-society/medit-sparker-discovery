# W4 도우미 계약 · AI용

참가자는 대화만 한다. 아래 JSON/명령은 AI가 만든다. `--statement`에는 실제 참가자 확인 문장을 쓰며 `--expected`는 방금 보여준 `show` 결과의 `digest`다. 도우미는 텍스트의 의미를 자동 분류하거나 사람 확인의 진위를 인증하지 않는다. 인용 위치·해시·순서·선택 파일 범위·최종 코드 정합을 검증한다. 스킬 대화가 사람 판단을 보존한다.

## 1. 기존 자료로 초안

`python3 <plugin>/scripts/week4.py init --root <case> --input <spec.json>`

```json
{
  "title":"내 제품", "product":"my-product",
  "code_root":"/absolute/product", "files":["app.py","README.md","requirements.txt"],
  "dependency_note":"requirements.txt와 README 실행 안내 포함",
  "sources":{"plan":"/absolute/planning.md","interview":"/absolute/interview.txt"},
  "principles":[{"id":"P1","text":"사람이 확인한 뒤 전달", "evidence":{"source":"plan","line_start":3,"line_end":3,"quote":"사용자가 확인하고 전달한다."}}]
}
```

파일은 재현에 필요한 **명시 allowlist**다. 원본 소스·의존성 명세/lockfile·실행 README를 읽고 준비한다. 기본 폴더 전체 압축 금지. 빌드 캐시·venv·node_modules·.git·.env·개인 인증정보·실제 업무 데이터·전사·음성·시험 로그는 넣지 않는다. 의존성 없는 제품은 README와 dependency_note에 명시한다. 자동 비밀 패턴 검사는 보조 수단이며 참가자와 파일 목록/본문을 검토한다. 인식 못 하는 비밀·업무 데이터까지 자동 제거한다고 주장하지 않는다.

`principles --root <case> --expected <digest> --statement "실제 원칙 확인"`

없거나 충돌한 원칙은 먼저 질문한다. 확인된 원칙을 새 요구 때문에 바꾸지 않는다. 원칙 재검토는 별도 명시 확인이며, 바뀐 원칙으로는 이전 case 보존 후 새 case에서 시작한다.

## 2. 전사 추출 → 대원칙 대조

`review --root <case> --input <feedback.json>` (최상위 배열)

```json
[{"id":"F1","product":"my-product",
"evidence":{"source":"interview","line_start":12,"line_end":13,"timestamp":"00:12","quote":"확인 버튼을 더 명확하게 해주세요."},
"speaker":"리뷰어 A","speaker_certainty":"confirmed",
"need":"검토 전후 상태 구분","request":"버튼 설명 보완",
"fit":"fit","principles":["P1"],"reason":"사람의 검토를 유지하고 더 분명하게 함",
"expected":"검토 필요 상태 표시","keep":"자동 전달하지 않음","paths":["app.py"]}]
```

타임스탬프가 없으면 필드 생략하고 행 위치로 연결한다. 문단 단위 전사도 실제 파일의 행 범위와 원문을 기록한다. 화자 `confirmed|uncertain|unknown`, 분류 `fit|conflict|insufficient`. 역할/제품 불명·인식 오류·누락은 필요한 질문으로 확인한다. `request`는 상대 제안, `need`는 AI 해석이며 동일시하지 않는다. 이 단계는 코드 수정이 아니다. 확인 후 `review`를 다시 저장할 수 있다.

## 3. 참가자의 선택

`select --root <case> --expected <digest> --statement "실제 수정 범위 선택" --input <choices.json>`

```json
{"F1":{"decision":"apply","reason":"사람 검토를 돕는 범위만 수정"},"F2":{"decision":"defer","reason":"원칙과 충돌해 이번에는 반영하지 않음"}}
```

“왜 이걸 지금 고칠 만한가?”에 기존 근거로 답 초안을 짧게 제시한다. 사용자 편익과 수정·유지 부담을 함께 보고, 참가자가 고친 답을 choices의 기존 reason에 반영한다. 이미 답이 있으면 다시 묻지 않으며 ROI 수치나 결정 건수를 요구하지 않는다.

후보 모두의 반영/보류를 기록한다. `fit`이고 화자가 확인된 항목만 `apply` 가능하다. 선택 전 코드가 달라졌으면 차이를 확인하고 초안을 다시 잡는다. 선택 후 **AI가 실제 코드 편집 도구로 고치고 실제 시험**한다. 도우미는 전사 명령·임의 shell을 실행하지 않는다.

## 4. 구현·시험 → 같은 짝 재확인 → 최종 수정·시험

수정 전 결과와 같은 입력을 보존한다. `week4.manifest(week4.files(code_root, files))`의 `plan.digest(...)`가 코드 digest다. 실제 실행 로그는 case 밖/안 개인 작업 영역에 저장하며 패키지엔 넣지 않는다.

`final --root <case> --input <result.json>`

```json
{"files":["app.py","README.md","requirements.txt"],
"summary":"검토 상태 안내 보완","before":"표시 없음","after":"검토 필요 표시",
"remaining":"실제 업무 적용 미검증",
"tests":[{"command":"python3 -m unittest","exit_code":0,"code_digest":"<최종 코드 digest>","log":"/absolute/final-test.log","sha256":"<로그 sha256>"}],
"peer":{"status":"checked","reviewer":"리뷰어 A","same_peer":true,"code_digest":"<실제 동료가 본 코드 digest>","source":"/absolute/recheck.txt","evidence":{"source":"peer","line_start":1,"line_end":1,"quote":"표시가 분명해졌습니다."},"remaining":"남은 불편 또는 미확인"}}
```

재확인 못 하면 `peer={"status":"not_checked","remaining":"재확인 미실시 이유/남은 확인"}`. 본래 인터뷰를 수정 후 확인으로 쓰지 않는다. 수정 후 다시 `final` 기록하면 보고서 확인은 해제된다. 동료가 본 digest와 최종 digest가 다르면 PDF에 **이전 코드 확인 / 최종 재수정본 동료 미확인**이 표시된다. 시험 실패는 exit_code와 남은 문제에 정직하게 쓴다.

## 5. 한 장 보고서·코드 묶음

“다음에도 쓰고 고칠 수 있게 남았나?”를 기존 코드·의존성·실행 안내·원칙과 시험 근거로 확인한다. 최소 실행 안내 보완은 선택된 파일 범위에서 하고, 확인 내용은 기존 summary에, 미확인은 remaining에 짧게 반영한다. 참가자가 같은 대화에서 문구를 고치면 final을 다시 저장하고 새 초안을 보여준다. 별도 스택 항목·설문·범용화는 추가하지 않는다.

`show`로 전체 초안을 보여준 뒤:

```
confirm --root <case> --expected <digest> --statement "실제 최종 코드/보고서 확인"
bundle --root <case>
```

Chrome/Edge를 쓰는 기존 오프라인 PDF renderer 재사용. 한 페이지 높이/폭을 넘으면 축소·잘라내기 대신 중요한 내용을 보존해 요약하고 `final → confirm`을 다시 한다. 최종 ZIP은 `code/<명시 소스>`, `report.pdf`, `manifest.json`만 포함. manifest의 week=4, 소스별 SHA256, 코드 집합 digest, PDF SHA, record digest로 정합을 연결한다. 변경 후 옛 PDF/ZIP을 제출할 수 없다.

현재 `submit`은 loopback `--local-test` 전용. 운영 미배포이므로 사용자의 제출 요청만으로 production 권한을 확대하지 않는다. 기존 브리지의 중복 방지/접수 재조회/재연결을 재사용한다. 서버 W3 장기 연결은 DB migration의 week=3 기본값을 유지하고 W4는 새 명시 동의로 별도 발급한다.

## 재현 시험

- `python3 -m unittest discover -s plugin/tests -p 'test_week4.py' -v`
- `python3 scripts/week4-smoke.py --output <새 절대 폴더>`: 합성 제품 실제 수정·전후 실행·Chrome PDF·ZIP 정합. 사람 답은 **합성 시험**으로 표시.
- 서버 `tests/week4-terminal-integration.py`로 격리 로그인→W4 첫 동의→실제 ZIP 전송→주차별 저장/다운로드 SHA→재실행 중복 방지를 시험한다.

이 검사는 실제 모델의 자연어 스킬 호출·개별 참가자 이해·운영 OAuth·실참가자 접수·Windows 실기기 검증을 대체하지 않는다.
