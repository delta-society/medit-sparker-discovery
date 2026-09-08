# Week 1 코스 반영 근거

2026-09-08 사용자 제공 코스와 후속 지시로 onboarding/week1에 기능 체험을 포함했다.

- 코스: https://www.ainative.camp/course
- Day 1: https://www.ainative.camp/course/day/1
- 실제 교안 확인: https://github.com/ai-native-camp/camp-2/tree/16c00971bf2224127bd7d6c495ce802a2ddd284e/.claude/skills/day1-onboarding

참고 코스의 Day 1은 첫 대화·Memory·7개 기능·CLI/Git/GitHub, Day 2는 업무 도구 연결, Day 3는 요구 구체화·스킬 제작, Day 4는 회고·축적 흐름이다. 이번에는 Day 1의 기능 체험 구조와 직접 스킬을 만들어보려는 사용자 요청을 Sparker Week 1에 맞게 새로 작성했다. 원 교안 파일·지시문은 번들로 복제하지 않았다. Day 2~4 스킬이나 원 코스 전체 설치는 추가하지 않았다.

| 참가자 흐름 | 이번 구현 |
|---|---|
| 첫 실행·맥락 | onboarding에서 실습 폴더·첫 대화·CLAUDE.md |
| Skill | 실제 프로젝트 스킬 생성 → 참가자 호출 → 결과 보정 |
| MCP | 연결 상태 확인 → 미연결이면 개념/설계, 사용 가능한 연결이면 지정 자료 읽기 |
| Subagent·Teams·Hook·Plugin | 기능 구분과 작은 체험. 실제 Teams/Hook 변경은 선택 |
| 업무로 적용 | 기존 plan의 KPI·입출력·기록·수용 기준 설계 |
| 1주차 인계 | 기존 submit + 참가자 앱 + Slack 두 질문 |

기존 자료의 전역 설정 자동 변경, Hook 100% 성공, 모든 작업의 Git 복구 가능 같은 일반화는 반영하지 않았다. 공식 Claude Code 문서로 Skill 경로·MCP·Teams 설명을 교차 확인했다. 실제 기능 제공 여부에 맞춰 미실행을 구분한다.

원 Day 1의 3~4시간과 Sparker의 기존 45분 실습은 같은 길이가 아니다. Skill·MCP를 우선하고 남은 기능을 인계하는 분기를 제공한다. 이 변경으로 전체 수업 시간 리허설이 완료됐다고 주장하지 않는다.
