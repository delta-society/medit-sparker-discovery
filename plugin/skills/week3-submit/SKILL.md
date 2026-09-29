---
name: week3-submit
description: 최초 계정 연결 후 참가자가 검토한 최신 3주차 평가 PDF를 터미널에서 바로 제출합니다.
---

# 3주차 평가서 제출

<participant_input>
$ARGUMENTS
</participant_input>

1. 현재 week3 흐름에서 알고 있는 `.sparker-evaluation/<case>/` 기록과 방금 생성한 PDF를 그대로 재사용한다. 이름·계정·주차·파일 경로를 다시 묻지 않는다. 주차는 3 고정이며 계정은 저장된 보고서 전용 연결을 사용한다. 최초 연결·필요한 재연결 때만 기존 웹 로그인으로 확인한다. 여러 기록 중 활성 대상이 정말 불명확할 때만 대상 하나를 확인한다. 원본 코드/ZIP, 대화 원문, 인증정보는 전송하지 않는다.
2. `evaluation.py --root "<known-root>" --case "<known-case>" show`로 최신 confirmed 상태를 확인한다. 변경된 draft면 전체 평가서 검토 단계로 돌아간다. PDF는 해당 revision의 `pdf-rNNNNNN/evaluation.pdf`만 허용한다. 0.11.0의 구 PDF에 SHA receipt가 없으면 같은 confirmed 기록으로 `evaluation.py ... pdf --refresh`를 실행해 새 PDF를 생성하고 경로를 보여준다. 새 내용을 확정한 것으로 가장하거나 기존 PDF에 SHA만 붙이지 않는다. PDF가 아예 없으면 `pdf`를 실행한다. 원래 보고서 전체 검토가 유효하면 계정/여섯 질문/내용 확인을 반복하지 않는다.
3. **보고서 생성/검토 확인은 외부 전송 동의가 아니다.** 사용자가 '제출해줘' 또는 이 제출 명령을 요청했을 때만 다음 helper를 실행한다. 이미 제출을 요청했다면 별도 채팅 동의를 반복하지 않는다. 최초 연결 때만 helper가 기본 브라우저를 열고 기존 로그인(필요 시 GitHub 로그인)을 재사용한다. 표시 계정과 30일 제출 전용 권한을 확인하고 **터미널 연결에 동의하고 제출**을 누른다. 이후 다른 PDF·리비전·case 제출은 브라우저를 열지 않는다. 비밀번호·쿠키·토큰을 요청하거나 읽지 않는다. Camp 수집 동의/토큰은 사용하지도 변경하지도 않는다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/submission_bridge.py" --root "<known-root>" --case "<known-case>" --submit
```

Windows에서는 설치된 `python` 또는 `py -3`를 사용한다. 실제 흐름에서 `--no-browser`, `--local-test`, `--origin`을 붙이지 않는다. 수동 링크 전달만으로 끝내지 않는다. `--submit`은 사용자의 요청을 반영할 때만 지정한다.

4. helper는 최초 prepare→웹 연결 동의→제출 전용 credential 교환, 이후 credential-authenticated prepare→PDF 전송→별도 status receipt 확인까지 처리한다. `status=submitted`와 서버 receipt가 있어야 접수 완료라고 말한다. 로컬 PDF/intent 저장, 브라우저 승인, upload 응답만으로 성공을 선언하지 않는다. 제출 번호와 주차, 기존 학습 화면 URL을 안내한다. 서버는 사람의 검토 여부를 검증한다고 말하지 않는다.
5. exit 2/pending은 실패 확정도 성공도 아니다. 같은 명령을 재실행해 같은 case·revision·SHA intent를 status부터 재조회한다. 제출 중에는 PDF를 재출력하지 않는다. 프로젝트 밖 private `~/.config/sparker-report/` 파일을 읽어 대화·로그·공유 파일에 넣지 않는다. capability/approval URL은 출력하지 않는다. prepare_unknown은 계약상 idempotency key가 없어 자동 재생성 금지: 10분 서버 만료 후 같은 명령 재실행으로 회복한다. 서버가 expired를 확인하면 명령이 한 번 새 intent를 만든다. 저장된 연결이 만료·해제되어 prepare가 인증 거절되면 재연결로 전환한다. 미확정 upload는 이 경로로 버리지 않는다. 연결 해제는 `submission_bridge.py --logout`으로 서버 revoke 후 로컬 credential을 제거한다. 유효기간 30일 또는 해제/disabled면 fail-closed하며 운영진 확인 또는 재연결이 필요하다. 상태 파일 삭제로 무조건 재시도하거나 HTTP 오류를 접수 완료로 바꾸지 않는다.

기본 목적지는 `https://leaderboard-production-eac2.up.railway.app` 고정이다. 다른 서버·Camp API·클라우드 임시 업로드로 우회하지 않는다. 원본 participant 코드/대화 대신 검토한 1장 PDF만 전송한다. source 요약에는 비민감 참조만 남긴다.
