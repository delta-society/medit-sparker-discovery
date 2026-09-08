# 실제 Claude Code 대화 QA 실행기

DEL-482는 실행기 준비다. `tests/test_qa_claude.py`의 가상 이벤트 회귀는 실제 모델 QA가 아니다. DEL-483(macOS), DEL-484(Windows), DEL-485(적대적 대화), DEL-490(Camp 대화/브라우저)에 실제 실행과 의미 검토 결과를 따로 기록한다.

## 고정 입력과 증거

`qa/scenarios.json`은 기획 6종(충분한 원문, KPI 모름, 목표 변경/확정 거절, 저장 거절, 중단/재개, 악성 제출문)과 Camp 6종(기획서만, 선택 원본, 원본 거절, 복수 세션, 초안, 준비/제출 구분), 총 26턴이다. 모두 합성 자료이며 실제 참가자 기록은 사용하지 않는다. Camp는 합성 초안과 세션 a/b/unselected를 미리 만든다. 실제 파일명은 UUID이며 준비 단계에서 프롬프트의 선택 경로를 치환한다.

`prepare`는 새 출력 폴더에 명시 목록으로 배포 ZIP을 빌드하고, 시나리오마다 별도 플러그인·입력·작업·Claude 설정·세션 UUID를 만든다. CLI 버전, 모델 ID, ZIP/실행기/시나리오 SHA와 파일 목록을 manifest에 고정한다. 기존 출력 폴더는 덮어쓰지 않는다. 이 단계는 인증·모델 호출 없이 `PREPARED_NOT_RUN`으로 끝난다.

`run`은 매 턴 새 CLI 프로세스를 실행하며 첫 턴의 UUID를 이후 `--resume`에 재사용한다. 다음을 수집한다.

- 입력 발화, JSON 이벤트, 도구 호출, 오류/종료 코드, 경과 시간
- 보고된 비용 추정치와 토큰 사용량, 턴별 저장 리비전 사본과 해시
- 실제 실행 OS/버전/아키텍처, CLI 버전/바이너리 SHA, 격리 환경 확인값

CLI 실패, 잘못된 모델/세션, 플러그인 미로딩, 누락된 결과/비용, 권한 거절, 저장 거절 위반, 초기 Camp 리비전을 포함한 고정 입력·불변 리비전 변경, 무단 확정, 플러그인·canary 변경은 구조 실패다. Camp는 ZIP 구조와 선택 세션 개수·UUID도 검사한다. 질문 적절성, 근거 없는 KPI, 목표 변경 반영, 실제 제출 주장 등은 리뷰어가 입력·응답·도구·리비전 증거를 함께 읽고 판단한다. 자동 결과는 항상 `semantic_status=NOT_REVIEWED`이며 전체 QA 합격을 뜻하지 않는다. Canary 읽기/외부 접속 시도는 도구 로그에서 별도 검토한다.

## 실행 환경과 인증

이 실행기는 보안 샌드박스가 아니다. Bash와 파일 도구가 필요하므로 폐기 가능한 VM/컨테이너 또는 실습 전용 네이티브 계정에서 실행한다. `--execution-boundary`는 운영자의 확인값이며 격리를 자동 구축하거나 입증하지 않는다. 실제 참가자 자료, 홈 디렉터리, 운영 DB, SSH agent, Docker socket, 클라우드/Git 자격을 마운트하지 않는다. 악성 입력 시험은 disposable VM/container만 사용한다. 네트워크는 테스트 환경에서 Anthropic 인증/API 목적지만 허용한다. 프롬프트나 Claude 권한 규칙만으로 네트워크 격리를 대신하지 않는다.

고정 CLI 버전을 설치한 뒤 `claude --version`으로 확인한다. 인증은 해당 환경의 `ANTHROPIC_API_KEY` 또는 `CLAUDE_CODE_OAUTH_TOKEN` 환경변수로만 전달한다. 로그인 파일을 복사하지 않는다. 호스트의 다른 환경변수·hooks·MCP 설정은 전달하지 않으며 각 시나리오의 `CLAUDE_CONFIG_DIR`를 사용한다. 키/토큰을 명령 인수, 채팅, manifest, Git, 로그에 넣지 않는다. 알려진 자격 값과 키 패턴은 수집 로그에서 제거하지만 결과 폴더는 외부 공개 전 사람이 검토한다. 원시 작업 파일·Claude 자체 로컬 세션 저장소까지 마스킹하는 기능은 아니다.

실행 전 계정의 사용 가능 여부와 공급자 쪽 사용량 한도를 확인한다. CLI의 `--max-budget-usd`는 추정 비용을 기준으로 하며 결제 한도 보장 수단이 아니다. 실행기는 매 호출 전에 턴 한도 전액을 예약하고 실패/중단 호출도 차감한다. 기본 전체 예약 한도 $15, 턴당 $0.50, 턴당 300초다. 전체 26턴은 최대 $13 예약이 필요하다. 비용 때문에 실패하면 증거를 보존하고 한도를 명시적으로 조정한 새 run을 만든다. 자동 재시도/모델 fallback은 없다. 비용 합산 시 재개 결과의 공급자별 누계 여부를 확인한다; `reported_cost_usd`는 받은 수치를 그대로 보존한다.

## macOS 네이티브

실습 전용 macOS 계정에서 체크아웃과 고정 CLI/Python 3.9+를 준비한다. 현재 CLI 2.1.263을 기준으로 구현했으며 모델 ID는 실행할 계정에서 사용 가능한 정확한 ID를 명시한다. 아래 ID는 예시이며 가용성을 보장하지 않는다.

```sh
python3 -X utf8 scripts/qa_claude.py prepare --output .qa-runs/mac-01 --model claude-sonnet-4-6 --claude-version 2.1.263 --scenario sufficient-source --scenario stop-resume
python3 -X utf8 scripts/qa_claude.py run .qa-runs/mac-01 --execution-boundary dedicated-native-account --stop-after 1
python3 -X utf8 scripts/qa_claude.py run .qa-runs/mac-01 --execution-boundary dedicated-native-account
```

Apple Silicon/macOS 26에서는 Linux 격리 실행의 우선 후보로 Apple container, 대안으로 OrbStack을 사용할 수 있다. **그 안의 결과는 Linux QA**다. macOS 네이티브 Claude·셸·경로 검증은 위처럼 macOS 프로세스로 별도 실행한다. 컨테이너 런타임의 설치·권한·이미지 준비는 이 스크립트가 변경하지 않는다.

## Windows 네이티브

전용 Windows 테스트 VM/계정에 고정 Claude Code, Git Bash와 Python 3.9+를 준비한다. PowerShell에서 실행하며 실제 Claude Bash 도구의 Git Bash 경로 변환도 도구 로그로 확인한다. 한글·공백 경로를 포함한다.

```powershell
py -3 -X utf8 scripts/qa_claude.py prepare --output '.qa-runs/윈도 QA 01' --model claude-sonnet-4-6 --claude-version 2.1.263 --scenario sufficient-source --scenario stop-resume
py -3 -X utf8 scripts/qa_claude.py run '.qa-runs/윈도 QA 01' --execution-boundary disposable-vm --stop-after 1
py -3 -X utf8 scripts/qa_claude.py run '.qa-runs/윈도 QA 01' --execution-boundary disposable-vm
```

Windows Server CI 결과와 Windows 10/11 참가자 환경 결과를 구분한다. Linux 컨테이너/WSL은 Windows 네이티브 QA가 아니다.

## Linux 격리 실행

고정 Claude CLI/Python이 있는 폐기 가능한 이미지나 VM을 준비한다. 소스는 읽기 전용으로 복사/마운트하고 `/qa`만 쓰기 가능한 새 볼륨으로 둔다. 대상 환경 **내부에서 prepare**해야 합성 세션 cwd와 절대 경로가 일치한다. 이미지 digest 또는 VM 이미지 ID 및 네트워크 제한 방식은 QA 이슈에 기록한다.

```sh
# Prepared disposable environment: no real participant data or host mounts.
python3 -X utf8 /src/scripts/qa_claude.py prepare --output /qa/run-01 --model claude-sonnet-4-6 --claude-version 2.1.263
python3 -X utf8 /src/scripts/qa_claude.py run /qa/run-01 --execution-boundary disposable-container
```

상태 읽기부터 실행 종료까지 `.run-lock` 디렉터리 생성으로 동시 실행을 차단한다. 비정상 종료로 잠금이 남으면 실행 프로세스가 모두 끝났는지 확인한 뒤 증거를 보존한다. 상태 파일의 `inflight`/`failure`가 남으면 같은 턴을 자동 재실행하지 않는다. 새 run으로 재현한다. 정상 턴 사이 중단은 `--stop-after`로 만들고 같은 명령으로 재개한다. 이는 프로세스 종료 후 재개 시험이며 강제 종료 중간 복구 합격을 뜻하지 않는다.

## 판정과 재사용

완료 후 리뷰어가 각 시나리오의 `semantic_review` 항목과 추가 가설을 검토하고 이슈에 PASS/FAIL·증거 경로·한계를 기록한다. CLI 이벤트와 로컬 파일은 서명된 증명이 아니며, 악성 프로세스가 같은 OS 계정의 증거 파일을 조작할 수 있다. 적대적 시험에서는 외부 실행 감독자의 수집 로그/네트워크 감사도 함께 보존한다. mock/가상 CLI로 만든 결과를 실모델 호출 증거로 제출하지 않는다.

Camp 브라우저 업로드와 실제 제출 확인은 실행기에서 하지 않는다. DEL-490에서 고정 패키지와 이 합성 시나리오를 재사용하여 별도 브라우저 증거를 붙인다.

근거: [Claude Code 비대화식 실행](https://code.claude.com/docs/en/headless), [CLI 참조](https://code.claude.com/docs/en/cli-reference), 로컬 `claude 2.1.263 --help` 확인(2026-09-08). 모델/API 성공 여부는 별도 실제 실행으로 검증한다.
