# Limited Haiku acceptance — 0.5.7

The user explicitly accepted a passing Haiku run as the final gate. The frozen **0.5.7 package passes that limited gate**: Linux `reuse-unknown`, 3/3 structural PASS, followed by independent review of all three final responses and both saved revisions. This is not a full model/OS semantic certification and does not close earlier Sonnet findings.

- Model: `claude-haiku-4-5-20251001`; Claude Code 2.1.263.
- Run evidence: `/tmp/discovery-live-qa/runs/linux-057-haiku45`.
- Package SHA-256: `de19675b8687b81378fdedc1a53a335df87ebd20e8457272be2f1cb7cd808d23` (21 files, 192036 bytes).
- T1 presents source-grounded facts and explicitly labeled reuse hypotheses; it does not save a revision or claim one. T1's records snapshot is empty.
- T2 actually saves `case-st-01/r000001`; T3 actually saves `case-st-01/r000002`. Captured state inventories JSON and Markdown for both revisions. The original submission content is retained in both (the file's terminal newline is omitted), with `source.txt` attribution and submitted facts.
- T3 updates the workflow, selected change, code responsibilities, implementation and tests to similar-process ST reference and human review. Deviation analysis/production is removed from that scope and listed in non-goals.
- Both records remain draft. T3 objective is proposed with null confirmation; reuse selection does not finalize the KPI or entire plan. No unsupported assertion that the current source process is manual appears in the reviewed final responses or saved plans.

A minor consistency residue remains: T3 `plan.user_result` still describes the original weekly marked-row review, while the selected change and detailed workflow/code/tests describe the newly selected ST-reference use. This is recorded as P3 and does not reverse the scoped acceptance. KPI unit remains a proposed choice of count or percentage, requiring subsequent user refinement.

Earlier Haiku attempts are failures, not passes: 0.5.5 used wrong reference paths and handcrafted JSON without the required store; 0.5.6 read correct references and used the helper but omitted original submission after mishandling an input file placed inside the revision store. Version 0.5.7 explicitly places scratch input outside the revision store, retains submission/facts in the linked template, and the captured run proves actual source-bearing saves. No failed attempt is included in the 3/3 result.

This report records the user's limited Haiku acceptance criterion. The separate native 0.5.5 Sonnet F2/P2 evidence remains a model-specific limitation; no Sonnet rerun or blanket closure is implied.
