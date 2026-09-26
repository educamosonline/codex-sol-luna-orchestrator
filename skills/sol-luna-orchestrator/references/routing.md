# Routing reference

Use the first lane whose constraints are satisfied.

| Signal | Direct | Luna | Sol escalation |
| --- | --- | --- | --- |
| Objective | tiny | explicit | ambiguous, strategic or open-ended |
| Scope | one trivial change | narrow and owned | cross-module, architecture or program |
| Verification | immediate | deterministic | investigation, judgment or external proof |
| Risk | low | low to medium | high or irreversible |
| Context | already in parent | compact packet | broader decision context |

## Parallel gate

Run Luna in parallel only when all are true:

- there are two to seven useful independent scopes;
- owned paths do not overlap by file or directory prefix;
- no worker needs another worker's uncommitted output;
- each scope has its own acceptance check;
- integration order is known.

Otherwise use one worker or serialized waves.

Pass the observed free capacity to `workflow.py route --available-workers N`.
The helper does not discover runtime slots; its default ceiling is seven.
A capacity of zero routes work directly; one slot prevents a parallel wave.

## Reasoning effort

- Luna medium: scouting, mechanical tests, data processing.
- Luna high: criticism, edge cases, focused diagnosis.
- Luna Max: demanding but still bounded implementation.
- Sol high: ambiguity or cross-module escalation.
- Sol high/Max: architecture and acceptance proportional to risk.

Higher effort and more subagents consume more tokens. Do not use Max or a wave
as a ritual.

## Escalation triggers

Escalate when ownership is unclear, inputs are missing, a task needs product or
security judgment, a worker tries to broaden scope, evidence cannot be tied to
the candidate, or one focused correction fails.
