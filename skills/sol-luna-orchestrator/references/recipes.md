# Orchestration recipes

## PRD milestone

1. Sol selects one observable milestone, freezes contracts, and creates the
   run.
2. `luna_scout` maps only unknown surfaces.
3. Sol writes two to seven disjoint implementation/test packets.
4. Luna workers execute the wave.
5. A critic and tester inspect the integrated candidate in the next wave.
6. Sol validates current evidence and accepts or routes one correction.

Do not execute an entire PRD as one permanent goal. Close one accepted
milestone before opening the next so context and evidence remain fresh.

## Bug fix

Use a scout and tester in parallel when both can remain read-only with respect
to product code. After reproduction and mapping, give one worker the fix. Run
the tester again against the new candidate, then let Sol accept.

## Repository review

Parallelize read-only lanes: correctness, security, tests, and maintainability.
Require file references and reproduction steps. Sol deduplicates findings and
decides which are real before any writer starts.

## Cost experiment

Choose three matched tasks. Run each with direct Sol, Luna single, and a Luna
wave only when genuinely parallel. Record accepted quality, elapsed time,
primary usage, total usage, and rework. Promote a policy only when measured
savings do not reduce acceptance quality.
