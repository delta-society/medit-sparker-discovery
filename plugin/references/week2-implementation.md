# Week2 구현 기록 계약

Python 3.9+ 표준 라이브러리만 사용한다. 네트워크·코드 실행·업로드·PDF 파싱은 하지 않는다. 에이전트가 호스트 도구로 실제 구현/실행하고 그 결과만 입력한다. 아래는 **합성 형식 예시**다. 참가자의 확인 발화를 지어내는 데 사용하지 않는다.

## 명령

`<PLUGIN>`은 로드된 플러그인 절대 경로. Windows는 `py -3`, 그 외 `python3`. 원문을 셸에 삽입하지 말고 파일 도구로 JSON을 쓴다. 각 하위 명령의 `--help`를 지원한다.

```sh
python3 "<PLUGIN>/scripts/implementation.py" --help
python3 "<PLUGIN>/scripts/implementation.py" intake "<기획.md>"
python3 "<PLUGIN>/scripts/implementation.py" intake "<제출.zip>"
python3 "<PLUGIN>/scripts/implementation.py" intake "<제출.zip>" --member "plan.md"
python3 "<PLUGIN>/scripts/implementation.py" --project "<실습 폴더>" new task-a --plan "<기획.md>" --input "<state.json>"
python3 "<PLUGIN>/scripts/implementation.py" --project "<실습 폴더>" show task-a
python3 "<PLUGIN>/scripts/implementation.py" --project "<실습 폴더>" update task-a --expected-revision 1 --input "<state-v2.json>"
python3 "<PLUGIN>/scripts/implementation.py" --project "<실습 폴더>" export task-a --output "<새 구현기록.md>"
python3 "<PLUGIN>/scripts/implementation.py" --project "<실습 폴더>" package task-a --files "<files.json>" --output "<새 week2.zip>"
```

ZIP은 전체 안전 검사 후 후보 목록을 반환한다. PDF는 `needs_host_read`이며 텍스트를 꾸며내지 않는다. 호스트 PDF 읽기에서 실제 페이지를 확인한 경우에만 `new --read-note "실제로 사용한 도구와 읽은 페이지"`를 제공한다. 이 메모는 도우미가 인증하지 않는다. 스캔/OCR 미지원·암호화·읽기 실패 시 생성하지 말고 MD/텍스트를 요청한다. ZIP PDF는 호스트의 안전한 항목 읽기가 없으면 원본 PDF를 별도로 요청한다.

## state JSON

```json
{
  "summary": "합성 예시: 입력 문자열의 앞뒤 공백을 정리하는 기획",
  "feature": "한 문자열 입력에서 정리된 문자열 출력까지",
  "scope_confirmation": "합성 테스트 발화: 이 기능으로 진행",
  "environment": "",
  "structure": "",
  "desired_change": "",
  "change_confirmation": "",
  "stage": "environment",
  "next_action": "사용할 런타임 확인",
  "blockers": [],
  "evidence": []
}
```

`stage`: scope/environment/implement/change/test/submit/paused. 자유문은 각각 최대 8,000자. `show`의 `state`만 새 입력 파일로 사용한다. 갱신은 전체 state이며 기존 evidence 배열을 보존하고 뒤에 추가한다. 기획 원본은 출처 해시로 연결하고 그 내용을 복제하거나 고치지 않는다.

각 evidence는 아래 키가 정확히 필요하다:

```json
{"kind":"normal","command":"실제로 실행한 명령","input":"합성 입력 A","expected":"기대 결과","observed":"실제 관측 결과","exit_code":0,"outcome":"pass","path":"evidence/normal.txt","sha256":"실제 파일 바이트의 64자리 SHA-256"}
```

`kind`: environment/execution/change/normal/exception/second_input. `outcome`: pass/fail/blocked. UI 도구 등 종료 코드가 없으면 null. 기대된 예외의 비영 종료는 통과일 수 있다. 해시는 도구로 실제 계산한다. 증거 경로는 실습 폴더 상대 경로이며 실제 비어 있지 않은 UTF-8 시험/실행 기록 파일을 만든다. 새 시험에는 새 파일명을 쓴다. 각 종류의 마지막 결과가 우선이며 과거 통과로 새 실패를 가리지 않는다. 수정 후 시험을 다시 한다. 도우미는 실행/발화 진위를 인증하지 않으므로 에이전트의 실제 도구 출력과 대조해야 한다.

## 저장·재개·제출 경계

- `.sparker-implementation/<task>/r000001.json`에 신규 리비전만 저장한다. 체인, 스키마, 증거 파일 해시를 검사한다. Week1 `.sparker-discovery`/학습 진행/Camp 파일을 수정하지 않는다. lock은 동시 갱신을 거절하고 expected revision은 오래된 수정 거절이다. `.pending.json`과 `.lock`가 남으면 원인을 확인하고 쓰기 프로세스 종료 확인 후 수동 복구한다. 자동 삭제/과거 기록 초기화는 하지 않는다.
- 사용자 소유의 비적대적 로컬 폴더를 전제한다. 링크/junction(지원 Python) 거부는 기존 plan 경로 계약을 재사용한다. 권한 있는 동시 공격자의 경로 교체를 방어하는 보안 저장소가 아니다. 최신 레코드를 직접 고친 로컬 사용자를 인증하지 않는다.
- MD/PDF 파일 및 ZIP 개별 항목 최대 2 MiB, ZIP 원본/해제 합계 최대 20 MiB, 100항목, 압축률 최대 100. traversal/절대/역슬래시/중복(대소문자 포함)/암호화/링크/특수 파일/중첩 archive(Office ZIP 포함)를 거절한다. 추출하지 않는다.
- `files.json`은 `["app.py", "README.md", "evidence/normal.txt", ...]` 형태의 **개별 상대 파일 allowlist**다. 디렉터리 탐색/통째 포함 없음. 기록된 증거 전부, README.md, 코드 파일이 필요하다. 허용 확장자는 helper의 `EXTENSIONS`에 명시(대부분의 텍스트 코드·설정·MD·CSV). 지원하지 않는 형식은 안전 검토 후 제품 변경이 필요하며 임의로 이름만 바꿔 우회하지 않는다.
- 비밀 경로/토큰 패턴/원본 세션 의심 내용을 거절한다. 탐지는 완전하지 않다. 원본 대화, 비밀, 개인/고객 자료는 수동 검토로도 제외해야 한다. 내부 record JSON·기획 원본은 자동 포함하지 않는다. generated `implementation.md`도 비밀 검사한다. ZIP은 고정 순서/시간의 동일 입력 동일 바이트이며 `manifest.json`에 파일별 SHA-256과 `prepared_locally_not_submitted`를 담는다. 출력은 기존 파일을 덮어쓰지 않는다.
- `show`는 증거가 없거나 달라졌으면 findings로 보여준다. `package`는 환경/실행/변경/정상/예외/두번째 입력의 마지막 결과가 모두 pass이고 구조/변경/확인 설명이 있으며 blocker가 없을 때만 로컬 준비한다. 이 조건은 실제 실행을 대신하지 않고 허위 assertion을 인증하지 않는다. 미완료도 `export`로 정직한 중간 기록을 남길 수 있다.
