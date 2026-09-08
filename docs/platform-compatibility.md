# Windows 네이티브 / macOS 호환성 — 2026-09-08

지원 대상은 참가자의 Windows 네이티브 Claude Code와 macOS Claude Code다. Linux 컨테이너 검증은 두 OS의 실기기 QA를 대체하지 않는다. Windows/macOS 네이티브 helper CI는 원격에서 실행해 통과했다. 실제 Claude 대화 결과는 아래 실행 기록 및 별도 live QA 보고서와 구분한다. 검색 결과는 위험과 설계 근거이지 설치·대화 시험 통과 증거가 아니다.

## 공식 문서와 사례에서 확인한 사항

| 근거 | 확인한 내용 | 반영 |
|---|---|---|
| [Claude Code 설치·Windows 설정](https://code.claude.com/docs/en/setup#set-up-on-windows), [도구 참조](https://code.claude.com/docs/en/tools-reference) | 현재 공식 문서는 Windows 네이티브와 PowerShell 도구를 지원하며 Git for Windows가 있으면 Bash도 사용한다. 시작 터미널과 실제 도구 셸을 구분해야 한다 | 스킬에서 Bash/PowerShell 문법·실행기·경로 인용을 구분. WSL 경로를 Windows Python에 전달하지 않음 |
| [Python Windows UTF-8 모드](https://docs.python.org/3.13/using/windows.html#utf-8-mode), [표준 스트림](https://docs.python.org/3/library/sys.html#sys.stdout) | 파일 기본 인코딩과 파이프 출력은 Windows 콘솔과 다를 수 있다 | CLI stdout/stderr를 UTF-8로 고정하고 import 시에는 변경하지 않음. 문서의 실행 예시에 -X utf8 안내 |
| [공식 skills 저장소 Windows 사례 #1061](https://github.com/anthropics/skills/issues/1061) | 사용자 보고: subprocess 실행기 탐색, cp1252 파일 출력, 파이프 처리 문제 | 이 레포가 사용하는 직접 Python 실행·한글 JSON 출력·명시적 파일 encoding을 점검. 해당 사례 전체가 이 플러그인에 재현된다는 뜻은 아님 |
| [플러그인 공백 경로 사례 #16451](https://github.com/anthropics/claude-code/issues/16451), [백슬래시 확장 사례 #26389](https://github.com/anthropics/claude-code/issues/26389) | 사용자 보고: 플러그인 hook 명령에서 경로 분리/백슬래시 소실 | 이 플러그인은 hook을 추가하지 않으며 실제 경로를 인용하는 지침을 강화. 한글·공백 경로에서 해제한 ZIP 도우미 시험 추가. 현재 버전에도 동일 버그가 남아 있다고 단정하지 않음 |
| [GitHub hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [setup-python](https://github.com/actions/setup-python) | Windows/macOS VM에서 Python 버전별 실행 가능 | 비밀값·Claude 인증 없는 OS별 회귀 테스트 workflow 추가 |

공식 페이지와 과거 검색 캐시에 Git Bash 필수/선택 설명이 혼재한다. 최신 공식 페이지를 우선하되 참가자에게 배포할 Claude Code 버전을 기록하고 해당 버전의 실제 도구를 확인한다. 이 레포에서 확인한 Linux 설치 버전은 2.1.263이며 Windows의 실행 확인을 뜻하지 않는다.

## 구현·테스트 보완

- `plugin/scripts/portable.py`: plan/submission/example/kpi CLI의 stdout/stderr에 UTF-8을 적용. 한국어/기호를 JSON 파이프로 전달해도 로컬 코드 페이지에 의존하지 않음. 호스트가 import한 경우에는 스트림을 변경하지 않는다.
- plan 입력은 UTF-8 BOM도 허용한다. 저장 출력은 기존 UTF-8/해시/리비전 형식 그대로다. UTF-16 입력은 지원하지 않는다.
- `.gitattributes`로 소스·번들 문서의 LF checkout을 지정하고 과거 fixture는 `-text`로 원본 바이트를 보존한다. 아직 기존 파일 전체를 renormalize하지 않았다.
- 테스트 소비자는 subprocess의 UTF-8을 명시적으로 decode한다. CP1252/CP949/ASCII 파이프를 강제한 CLI 검사, 한글·공백·& 경로, BOM 입력, 한글·공백 폴더에 해제한 ZIP 실행을 검사한다.
- 파일 경로의 symlink/junction 거부 정책은 유지한다. Python 3.9~3.11은 `Path.is_junction`이 없어 junction 검사가 제한되므로 새 교육 환경에는 Python 3.12 이상을 권장한다. [Python isjunction 도입](https://docs.python.org/3/library/os.path.html#os.path.isjunction).
- Camp helper와 선택 세션 검증도 포함되어 있다. 원문 보존과 오류 뒤 제출 범위 변경 지침의 실제 대화 검증은 별도 live QA 보고서를 따른다. 병합된 PDF 내보내기는 사용자 선택 사항이며 기존 Camp/기획 대화 QA 결과를 PDF 검증으로 확대하지 않는다. PDF 근거는 [PDF 내보내기](pdf-export.md)를 따른다.

## 자동 검증 구성

`.github/workflows/compatibility.yml`:

- Ubuntu 24.04: Python 3.9 / 3.13.
- Windows Server 2022: Python 3.9 / 3.13, Git Bash 및 PowerShell 명령 smoke test.
- macOS 15: Python 3.13.
- 전체 helper 테스트, 합성 AR 테스트, 패키징·해제 실행 검사.
- push/PR/수동 실행으로 동작. 원격 실행 [34193780227](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34193780227)은 통과했다. 상세 소스 SHA와 OS별 결과는 해당 실행의 matrix를 따른다.

Windows runner는 WSL이 아닌 네이티브 Windows이지만 참가자의 Windows 10/11 PC와 동일하지 않다. Python 3.9는 기존 최소 버전 호환을 위한 시험 대상이며 새 설치 권장 버전이 아니다. CI의 `-X utf8`에 결함이 가려지지 않도록 별도 subprocess 테스트가 UTF-8 mode를 끄고 레거시 코드 페이지를 강제한다.

## 이번 로컬 검증

Linux Python 3.13에서 helper 테스트 86개(병행 Camp 테스트 포함)와 AR 12개, 총 98개 PASS. manifest 검증과 `git diff --check` PASS. 레거시 코드 페이지 강제는 Windows 파이프의 인코딩 실패 조건을 시험한 것이며 Windows OS 실행 결과는 아니다. 위 수치는 최초 로컬 검증 이력이며 현재 원격 결과는 위 CI 링크를 따른다.

PowerShell 5.1의 기본 리다이렉션은 UTF-16LE를 만들 수 있으므로 호스트 파일 도구 또는 명시적 UTF-8 쓰기를 사용하도록 안내했다. [Microsoft 인코딩 문서](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding).

## 남은 실제 QA

네이티브 실제 Claude 대화의 버전·소스·패키지 해시와 시나리오별 결과는 [live QA 검토](reviews/2026-09-08/NATIVE-LIVE-REVIEW.md)를 따른다. helper CI와 실제 대화 검증을 구분하고, 이전 후보의 PASS를 병합된 새 패키지의 전체 대화 PASS로 승계하지 않는다. 신규 시작→원문 선반영→KPI 수정/거절→확정→종료→재개→내보내기, 저장 거절, 경로 인용은 해당 실행에서 확인한 범위만 보고한다.

OneDrive/회사 네트워크 드라이브, 기업 보안 프로그램의 파일 잠금, Windows ARM64, 긴 경로 정책, 실제 PowerShell 5.1과 Git Bash별 LLM 동작은 미검증이다. 발견되면 합성 fixture와 환경 정보를 남겨 재현하며 사용자 원문·인증 자료를 CI 로그로 보내지 않는다.
