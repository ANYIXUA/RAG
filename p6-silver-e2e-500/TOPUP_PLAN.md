# P6 Silver incremental completion plan

The user's detailed task is the binding specification. Implement independently of
the existing generator; do not edit original data, Gold, corpus, or RAG settings.

1. [x] Verify 466 records, type counts, sequential unique IDs, input hashes, and
   reproduce the historical build in memory. Save `silver_baseline_sha256.json`.
2. [x] Add pytest coverage before implementation for evidence, both historical
   deduplication rules, quotas, immutable baseline, interruption, replay,
   output conflicts, and exhaustion.
3. [x] Add `topup_silver.py`, importing the original generator's validators,
   prompts, local client, schemas and inference options. Keep the original
   generator unchanged. Count accepted records only. Use seed 20261106 with a
   distinct deterministic batch offset, fixed original model digest, and a
   cumulative maximum batch limit.
4. [x] Persist batch starts before inference and complete response/decisions
   after inference. Replay all completed batches with deterministic validation;
   incomplete calls consume attempts but no quota. Serialize writers with a
   process lock. Keep immutable per-event files as the recovery authority and
   project them to `silver_topup_raw.jsonl`; archive prior derived reports by
   content hash before updating them. Never replace a conflicting final dataset.
5. [x] Run targeted pytest; generate locally; build only if all final checks
   pass and exactly 500 cases match the quotas. Preserve original 466 rows as
   the exact byte prefix and equal decoded fields. New IDs start at p6s-0467.
6. [ ] Verify idempotent generation/build, baseline hashes and final SHA-256;
   request one independent code review; publish a report with commands and
   risks. Stop without running E2E.

Review focus: lost response after interruption; conflicting existing output;
changed inputs or journal decisions; over-producing model responses; unanswerable
keyword checks being mistaken for human confirmation.

Decisions: stay in the provided working directory because the baseline artifacts
are untracked and must remain authoritative. No branch operations or commits.
Unanswerable cases carry an explicit pending semantic/human verification risk;
no synthetic human approval. Automated completion does not make Silver Gold.

Execution notes:
- Initial baseline verification and original-validator replay passed for all 466.
- New tests observed RED before implementation; Windows hardlink restrictions
  required atomic non-replacing Windows rename, then recovery tests passed.
- Independent reviewer found missing per-request provenance verification. Exact
  request reconstruction now verifies seed, options, corpus, prompt and version;
  six regression cases observed RED then GREEN. Exhausted runs skip model access.
- Agent inspection found four semantically invalid NEW candidates after initial
  automatic publication. Append-only rejection events retain the full candidates
  and reasons. Two superseded publications are preserved in `topup_quarantine`.
  Valid new rows keep all fields/IDs; only explicitly rejected new slots are
  replenished with fresh model candidates. Original 466 are never eligible for
  rejection. Interrupted archiving is recoverable and tested.
- Final generation: 47 attempts, 111 candidates, 34 net accepted, 77 rejected
  including 4 semantic withdrawals. No original prompt, validator, inference
  settings, RAG code, Gold or corpus edits. No commits, push or E2E execution.
