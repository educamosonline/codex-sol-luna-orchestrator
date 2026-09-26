# Work packet and receipt contracts

## Work packet

Required fields:

- `schema_version`: `1`
- `packet_id`: stable identifier
- `objective`: one bounded outcome
- `done_when`: observable acceptance checks
- `owner`: agent name and role
- `owned_paths`: exclusive write scope; empty for read-only work
- `do_not_touch`: explicit boundaries
- `inputs`: only task-local sources
- `validation`: exact checks or commands
- `risk`: `low`, `medium`, or `high`
- `return_format`: `receipt-v1`
- `status`: `pending` or `in_progress`
- `created_at`: UTC timestamp

The serialized human-readable content must stay at or below 400 words. Never
include secrets.

Create a packet:

```bash
python <skill-dir>/scripts/workflow.py packet <run-dir> \
  --id api-tests --agent luna_tester --role tester \
  --objective "Verify the API contract" \
  --done-when "All contract tests pass" \
  --owned-path "test-results/api/" \
  --do-not-touch "src/" \
  --validation "python -m unittest tests.test_api"
```

## Receipt

Required fields:

- `schema_version`: `1`
- `packet_id`: matching packet identifier
- `status`: `PASS`, `FIX`, or `BLOCKED`
- `summary`: concise result
- `changed_files`: paths changed within ownership
- `commands`: command and exit code pairs
- `evidence`: kind, path/reference, and optional digest
- `risks`: remaining risks
- `candidate_digest`: Git commit or deterministic candidate hash
- `next_action`: specific handoff
- `created_at`: UTC timestamp

Create a receipt template:

```bash
python <skill-dir>/scripts/workflow.py receipt <run-dir> \
  --packet-id api-tests --status PASS \
  --summary "Contract tests pass" \
  --command "python -m unittest tests.test_api::0" \
  --evidence "test-report:test-results/api/report.xml" \
  --candidate-digest "git:abc123" \
  --next-action "Ready for Sol acceptance"
```

`PASS` requires evidence and successful commands. A changed file outside
`owned_paths` invalidates the receipt.
