# Native 0.5.5 reuse semantic review

Reviewed 2026-09-08. GitHub Actions run [34197747230](https://github.com/delta-society/medit-sparker-discovery/actions/runs/34197747230), artifacts `live-qa-macos-15-reuse` and `live-qa-windows-2022-reuse`. Both manifests identify `claude-sonnet-4-6`, Claude Code 2.1.263 and package SHA-256 `49578b41bd10617837a76c0ca7edfd5355bf0b918cabe0b8ae7c269614883037`. This is native captured evidence, distinct from Linux evidence and any later model retry.

Both operating systems completed 4 cases / 9 turns with structural PASS (18 turns total). Human review covered every final response and published revision, with particular inspection of scope, workflow, selected change, code responsibilities, implementation steps, tests, objective and linkage. Structural PASS does not imply semantic PASS.

## Open F2 / P2: unsupported current-manual assumption persists on both operating systems

The reuse-unknown source establishes a weekly Excel process, work-code linkage, missing/outlier marking and review. It does not establish manual execution. Nevertheless the following outputs assert it as the current process:

| OS | Evidence location within artifact | Exact text |
|---|---|---|
| macOS | `reuse-unknown/evidence/turn-2-records.json`, latest revision `plan.selected_change.reason` | `현재 수작업인 연결·표시 단계를 자동화해 생산기술 담당자의 반복 작업을 줄이고…` |
| macOS | `reuse-unknown/evidence/turn-3-events.json`, result final, existing weekly process table row | `현행 수작업 유지 — 제품 범위 밖, 입력 데이터 소스 역할` |
| macOS | `reuse-unknown/evidence/turn-3-records.json`, latest revision `plan.workflow[0].step` | `1. 기존 ST 기록 누적 (현행 수작업 — 제품 범위 밖)`; basis `f01, f02, f03` |
| Windows | `reuse-unknown/evidence/turn-2-events.json`, result final question | `현재 수작업에서 어떤 편차를 이상치로 판단하고 있나요?` |
| Windows | `reuse-unknown/evidence/turn-2-records.json`, latest revision `plan.selected_change.reason` | `현재 수작업 연결·표시 과정을 코드로 보조하여 생산기술 담당자의 반복 처리를 줄인다.` |
| Windows | `reuse-unknown/evidence/turn-3-records.json`, latest revision `plan.acquisition_tasks[1].method` | `현재 수작업 참조 방식 문서 또는 구두 확인` |

This remains F2/P2 under the earlier review criterion: the assistant supplies an unsupported current-state premise that can bias the proposed solution and subsequent questions. It is present in persisted records as well as visible output. Draft status alone does not distinguish the asserted current state from a hypothesis. These two native reuse groups cannot be reported as fully semantic-clean. A proposed future manual measurement step, or a draft linkage trigger alone, is not the basis for this finding.

## Behaviors that passed the bounded review

- **Scope exclusion:** both reuse-unknown T3 revisions remove new deviation calculation and missing/outlier generation from the selected product, code responsibilities, implementation and tests. The remaining product consumes existing ST evidence to display similar conditions/ST/basis for human review. Normal and no-match tests cover this consumer behavior. No excluded producer remains executable within the selected scope.
- **Confirmation boundary:** every reviewed revision remains draft. Selected reuse purpose does not finalize the KPI or complete plan; proposed objectives keep null confirmation. Current and target numeric KPI values are not invented.
- **Confirmed time objective:** both time cases retain the user-provided minutes-per-work-item reduction objective. T2 proposes timing-record events in existing Excel and leaves location/details unconfirmed. The weekly work-unit denominator is still a proposed definition, not evidence that the user confirmed it.
- **One-off:** both cases preserve the single Word-document scope and reject recurring accumulation/new systems/external sending. T2 reuses r1 without unnecessary mutation and remains draft.
- **Weekly report:** both final revisions restrict reuse to missing-metric/correction-reason history in the existing report, without ST estimation or a separate dashboard. KPI proposals concern history availability/completeness and remain unconfirmed. These are indirect outcome proxies, a calibration limitation rather than a fabricated confirmed target.

No package changes or additional live runs were made for this review. The F2 finding remains open; this document does not supersede it with a blanket PASS.
