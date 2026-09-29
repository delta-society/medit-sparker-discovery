# 평가 기록과 한 장 PDF

Python 3.9+와 기존 Edge/Chrome으로 동작한다. 추가 패키지·폰트 다운로드·외부 서비스가 필요 없다. 모델이 JSON을 채우며 참가자에게 스키마를 노출하지 않는다. 한글 글꼴은 번들에 포함돼 있다.

아래 `<plugin>`은 실제 플러그인 경로로 치환하고 경로/인수는 안전하게 인용한다. 참가자가 선택한 제품 폴더에서 실행한다. `template` stdout을 별도 작업 JSON에 저장하고 코드/대화 근거로 수정한다. API 키·원문 코드·개인 연락처를 넣지 않는다.

```sh
python3 "<plugin>/scripts/evaluation.py" template
python3 "<plugin>/scripts/evaluation.py" --case my-product save --file "<평가 초안 JSON>"
python3 "<plugin>/scripts/evaluation.py" --case my-product show
```

초안은 `title/purpose/user/done_when/source/human/keep`, `criteria` 6개, `actions` 1~3개다. 각 기준은 `name/judgment/evidence/basis/next/reviewed`. template의 기준 이름/순서를 그대로 쓴다. 판정은 확인됨/부족함/아직 모름, 근거는 코드/실행/사용자 설명/미확인이다. `basis`에 출처 파일·관측·사용자 설명의 핵심을 담고 `next`에 미확인/확인 방법을 남긴다. 단순 코드 존재로 효과를 확인했다고 쓰지 않는다. 미확인 근거는 아직 모름 판정만 허용한다.

한 장의 가독성을 위해 제목 60자, 상단 필드 각150자, 근거160자, 다음 확인100자, 행동·확인방법 각각120자까지 저장한다. 세부 문답은 대화에 남긴다. 한도 초과면 자동 자르지 말고 내용을 요약한다. 레이아웃은 실제 렌더에서도 검사하며 넘치면 PDF 생성을 실패로 반환한다. 아직 모름 항목도 참가자와 검토했다면 reviewed=true가 된다.

전체 초안을 화면에 보여준 뒤 참가자의 최종 확인 문장과 현재 `show`의 digest를 사용한다. 문장을 AI가 만들어내지 않는다.

```sh
python3 "<plugin>/scripts/evaluation.py" --case my-product confirm --digest "<show의 digest>" --statement "<실제 확인 문장>"
python3 "<plugin>/scripts/evaluation.py" --case my-product pdf
```

성공 시 반환된 evaluation.pdf를 첨부하거나 실제 파일 링크로 보여준다. PDF는 확정 리비전에 묶이며 수정/save 시 이전 확인은 새 초안에 승계되지 않는다. 같은 PDF가 이미 있으면 해당 경로를 사용한다. 실패 시 저장된 평가서는 보존한다. 브라우저가 없으면 기존 Edge/Chrome 경로를 확인하고 `SPARKER_PDF_BROWSER`에 절대경로를 지정할 수 있다. 설치를 임의 수행하지 않는다. 한 장을 넘으면 초안을 더 명료하게 요약하고 다시 확인받는다.

기존 `week3.py`는 과거 연결 실습 기록의 호환 보존용이다. 이번 평가에서는 호출하지 않고 새 `.sparker-evaluation`을 쓴다. 연결 실습 완료·외부 발신·계정 연결은 평가 종료 조건이 아니다. 저장/검토 완료를 진위 인증 또는 실제 운영 효과로 보고하지 않는다.
