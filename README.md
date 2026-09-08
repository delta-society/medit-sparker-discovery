# 상부구조 — 돈 벌 문제점 발굴

AI Sparker 1기 상부구조 트랙 — 참가자 산출물에서 메디트가 돈 벌 문제점을 발굴하고 KPI·기획서로 전환.

- 헌법: [`CONSTITUTION.md`](./CONSTITUTION.md) — 정체가 바뀌는 문장
- 스펙: [`SPEC.md`](./SPEC.md) — 산출물이 바뀌는 문장

**완료 정의**: 4회차 발표 PDF와 교육용 플러그인을 만들고 1회차20분·후속 회차 약30분 발표와 회당40분 이상 실습의 실행 근거를 남긴다.

첫 제작물: [1회차 어젠다·실습 설계](curriculum/week1-agenda.md). 구현·리허설은 SPEC 작업 항목으로 추적한다.

**Linear 추적**: DEL / `상부구조 — 돈 벌 문제점 발굴` (이니셔티브 `Medit AI Sparker 1기`) · target 2026-10-07
**Lead**: @sung

---

상위 Project 캐논: `delta-society/delta-society-os` `projects/mbk-medit/`

## 플러그인 설치 · GitHub marketplace

```text
/plugin marketplace add delta-society/medit-sparker-discovery
/plugin install sparker-discovery@sparker
```

Claude Code를 다시 시작한 뒤 `/sparker-discovery:plan`을 실행합니다. Python 3.9 이상과 PDF용 Chrome 또는 Edge가 필요합니다. 공개 저장소에서 설치하므로 별도 저장소 권한 요청은 필요하지 않습니다.

설치·업데이트: [사용 안내](docs/plugin-guide.md). 플러그인과 예시·한글 글꼴·PDF 자산은 `plugin/` 안에 함께 배포됩니다.
