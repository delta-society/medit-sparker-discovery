# main 병합 리뷰 — 0.6.1

사용자 승인: PR 게시 → 병합 전 리뷰 → 보완·CI 확인 → 병합을 빠르게 진행. 기존 사용자 지정 Haiku 핵심 인수는 유지하고 전체 모델 대화를 반복하지 않았다.

main `c224bdc`의 공개 marketplace·온보딩·Week 1·선택형 PDF에 PR #2/#5의 실제 대화 보완을 통합했다. 통합 런타임은 `66e3d33`, 버전 0.6.1이다. PR #5가 main을 직접 대상으로 하며 선행 #2 변경도 포함한다.

- 원문이 포함된 linked template, 입력 JSON의 안전한 위치, 절대 참조 경로, 원문/확정 보존을 유지했다.
- main의 PDF opt-in과 PDF assets, 온보딩·Week 1 및 marketplace 안내를 유지했다.
- Camp 파일 읽기는 main의 경로/열린 파일 각각의 변경 검사와 cross-API 크기·mtime 대조를 유지했다. Windows ctime 차이 허용과 변경 차단 회귀를 함께 보존했다.
- 패키지는 main의 전체 32개 승인 파일 목록과 재현 가능한 ZIP 바이트 형식을 결합했다.
- 두 독립 리뷰어가 runtime·문서 충돌 해결을 검토했고 새 P1/P2를 발견하지 않았다. 이전 모델의 제한과 P3 관찰은 원래 보고서에 남긴다.

로컬 플러그인 회귀 107개 중 102개 PASS, 선택적 브라우저/환경 검사 5개 SKIP. QA 실행기 48개 PASS. 별도 3OS 실제 PDF smoke와 OS 호환성 CI는 병합 직전 GitHub 결과를 확인한다. main 대비 diff check PASS. 이전 vendor 자산은 main과 동일한 바이트를 보존했다.

패키지: `.qa-runs/releases/sparker-discovery-0.6.1.zip`, 32개 파일, 8,711,684 bytes, SHA-256 `5023129900f885692abbeaf9aaec25af171ad4010b9b0ebb2c969d41fb267263`. 이 ZIP에는 선택형 PDF가 포함되며, 이전 0.5.7 QA ZIP과 다르다. 실제 참가자 MacBook 확인·강사 리허설·교육 배포 인수는 별도다.
