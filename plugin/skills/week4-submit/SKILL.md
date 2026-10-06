---
name: week4-submit
description: 참가자가 확인한 최신 4주차 최종 코드+한 장 PDF 묶음의 정합을 검사하고 기존 로그인·터미널 제출 경로로 연결합니다. 공통 배포본에서 로컬 묶음 생성까지 지원하며 운영 4주차 접수는 아직 차단됩니다.
---

# 4주차 최종 코드 + 보고서 제출

현재 대화의 제품 폴더·case·4주차를 그대로 쓴다. `week4.py show --root <case>`로 최신 `confirmed`를 확인하고 `bundle`로 만든 최신 `bundle-rNNNNNN/final-code-and-report.zip`만 사용한다. arbitrary ZIP/PDF나 옛 리비전을 보내지 않는다. 최종 확인과 외부 제출 동의를 구분한다.

**플러그인은 공통 배포됐지만 운영 웹앱의 4주차 ZIP 접수 확장은 미배포다.** 생성한 최종 ZIP은 로컬에 보존하고 운영 업로드는 차단한다. 운영 서버는 아직 3주차 PDF 전용이다. 운영 3주차로 우회하거나 기존 3주차/collector/Camp 자격을 4주차로 재사용하지 않는다. 최종 ZIP 경로와 운영 연결 미배포를 정직하게 안내한다. 기존 웹 수동 업로드를 실제 접수 없이 접수 완료라고 하지 않는다.

승인된 격리 개발 시험에서만:

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/week4.py" submit --root "<case>" --origin "http://127.0.0.1:<port>" --local-test --submit
```

기존 제출 브리지와 동일한 로그인/명부/과제 저장 경로를 사용한다. W4 첫 연결은 기존 계정 로그인으로 **4주차 코드+PDF 권한**에 별도 명시 동의한다(3주차 권한을 조용히 확대하지 않는다). 그 뒤 유효한 W4 연결로는 터미널 제출·접수 재조회만 한다. `submitted`와 동일 SHA/주차가 든 서버 receipt만 접수 성공이다. pending/unknown은 같은 명령으로 재조회하며 임의 상태 파일 삭제·재접수로 바꾸지 않는다.

W4 연결 해제는 `submission_bridge.py --logout --scope 4 --origin <local-origin> --local-test`를 사용한다. 자격 파일·승인 URL은 stdout/보고서/패키지에 넣지 않는다. 운영 배포 승인·검증 전 local-test 제한을 제거하지 않는다.
