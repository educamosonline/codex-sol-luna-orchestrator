---
name: sol-luna-orchestrator
description: "Coordinate Sol-led work with bounded Luna workers. Use for Sol/Luna orchestration requests or a delegated Sol coordination scope."
---

# Sol/Luna Orchestrator

## Model routing

Use GPT-6 Sol (`gpt-6-sol`) for the accountable primary coordinator and
GPT-6 Luna (`gpt-6-luna`) for all Luna scout, worker, critic, and tester
delegations. The `sol_reviewer` also uses `gpt-6-sol`. Check that each model
is available in the active runtime before dispatch. If an already loaded custom
agent still pins an older model, update its file and start a new session before
dispatch. A pinned custom-agent model can take precedence over spawn defaults;
do not silently fall back to an older generation. Changing
this skill does not change the model of an already running primary session.

This workflow governs Sol-led runs. Within an Astra-led team, Sol owns only its
assigned domain; root Astra retains overall architecture and final acceptance.
Use the parent coordinator's ledger and capacity allocation rather than creating
a second competing orchestration layer.

Keep the primary Sol accountable for the objective, architecture, routing,
integration, risk decisions, and final answer. Delegate only when a bounded
worker saves meaningful time or primary context.

## Route before spawning

Choose the cheapest safe lane:

1. Use **Direct** when writing a good packet costs as much as the task.
2. Use **Luna single** for a clear objective, narrow scope, and deterministic
   check.
3. Use a **Luna wave** for two to seven independent scopes with disjoint path
   ownership.
4. Escalate to **Sol** for cross-module ambiguity, subtle debugging, or after
   one focused Luna correction fails. This package uses only GPT-6 models.
5. Keep work with **Sol** for architecture, security policy, secrets,
   production risk, irreversible actions, external communication, and final
   acceptance.

Read [routing.md](references/routing.md) when the lane is not obvious. Use
`scripts/workflow.py route --help` for a deterministic recommendation, but let
Sol override it with an explicit reason.

## Prepare the run

Freeze the objective, acceptance criteria, and candidate baseline before
delegation. For work spanning more than one worker or one correction, create a
run directory:

```bash
python <skill-dir>/scripts/workflow.py init .codex/orchestration/<run-id> \
  --goal "<goal>" --acceptance "<observable acceptance>"
```

Write one packet per worker. Keep it self-contained and at most 400 words.
Include objective, `done_when`, owned paths, do-not-touch paths, inputs,
validation, risk, and expected receipt. Read
[contracts.md](references/contracts.md) for the complete schema and commands.

## Delegate bounded work

- Prefer `luna_scout` for read-only mapping and evidence.
- Prefer `luna_worker` for narrow implementation.
- Prefer `luna_critic` for bounded correctness review.
- Prefer `luna_tester` for tests and artifacts without product-code edits.
- Return ambiguous tasks or failed Luna corrections to the primary Sol.
- Use `sol_reviewer` only for a fresh high-risk independent review.

Pass the packet content, not the entire conversation. Check live capacity and
configured limits; start no more than seven children at once, and fewer when
capacity is lower. Do not assign overlapping owned paths. State that workers are
not alone in the repository and must preserve others' changes.

For a wave, start read-heavy work freely but serialize writers unless ownership
is provably disjoint. Wait for all required receipts before integration.

## Validate receipts

Require `PASS`, `FIX`, or `BLOCKED` plus changed files, exact validation
commands and exit codes, evidence references, remaining risks, candidate
digest, and next action. `PASS` without evidence is not a pass.

Validate run state:

```bash
python <skill-dir>/scripts/workflow.py validate .codex/orchestration/<run-id>
python <skill-dir>/scripts/workflow.py summary .codex/orchestration/<run-id>
```

Treat evidence as stale after any relevant candidate change. Keep raw logs in
artifacts; return only concise receipts to the primary context.

## Correct, escalate, and accept

Give a Luna worker at most one focused correction containing the failed check
and exact gap. On a second failure, return to Sol or report `BLOCKED`; do not
loop.

Integrate serially. Re-run affected checks after integration. Sol must compare
the integrated candidate with the original acceptance criteria and issue the
final `PASS`, `FIX`, or `BLOCKED`. A worker receipt is evidence, not acceptance.

For multi-wave PRDs and long-running projects, read
[recipes.md](references/recipes.md). Record elapsed time, primary and total
usage, corrections, escalations, receipt acceptance, and escaped defects when
comparing orchestration policies.

## Preserve safety

Do not put credentials in packets or receipts. Do not let a subagent broaden
permissions or scope. Verify the parent session's permission mode before
spawning because live parent overrides can be reapplied to children.

For installation, run `python scripts/install.py` from the repository root
to preview changes, then use `--apply` and run `python scripts/install.py doctor`.
Replacing different existing files also requires `--replace` and creates a
backup. Existing user authorization can cover these flags; do not ask again
for already authorized installation. Never silently replace a custom agent.
