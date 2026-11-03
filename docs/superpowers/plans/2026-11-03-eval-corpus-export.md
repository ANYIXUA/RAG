# Evaluation corpus export — approved stage 1

Scope: implement Active Chunk read-only export and Corpus Snapshot only, in
`D:/AgentAIProgect/RAG`. The user's latest scope overrides the broader phase-0
proposal. No commits, pushes, benchmark, Ollama, review/compiler, production
retrieval, permission gateway, or Docker Compose changes in this stage.

Architecture: a standalone exporter consumes existing Settings and an explicit
single collection/tenant/tag scope. A new psycopg connection defaults to read-only,
uses a repeatable-read read-only transaction, checks the server's actual mode,
then checks ACL headers before selecting authorized bodies. No business Store is
constructed. JSONL content and scope have deterministic hashes; manifest time is
excluded from snapshot identity. The verifier revalidates hashes, scope and rows.

Decisions:
- Work in the current repository as explicitly requested; preserve the two
  pre-existing untracked paths. Do not create another checkout or use old images.
- Reuse installed psycopg and standard-library dataclasses; no dependency install.
- Exporter accepts only explicit well-formed tenant/tag metadata. Malformed ACLs
  in the requested tenant stop export; no legacy default-permission inference.
  Existing production permission behavior remains unchanged.
- Validate both document and chunk ACLs; inconsistent associations stop export.
- Metadata export is an explicit structural-field allowlist, excluding raw paths,
  unknown metadata, credentials and runtime connection settings.
- The explicit collection is the exact collection exported; do not resolve or
  change the global active-version pointer. Both rows must have active status.
- New output directory only; manifest is published last. Partial output without a
  valid manifest is never a usable snapshot.
- Local CLI requires the existing environment configuration; it does not silently
  import .env or switch to another worktree's configuration.

Tasks:
- [x] Write and observe failing scope/export/snapshot/CLI tests.
- [x] Implement schema, read-only exporter, manifest verifier and CLI.
- [x] Verify permission isolation, failure handling, reproducibility and no overwrite.
- [x] Run local focused tests and available full regressions.
- [x] Run a real read-only export using current checkout code if local DB access is
      available; record code provenance and distinguish it from mocked tests.
- [x] Document commands, actual results, limitations; stop for user acceptance.

Progress and rulings will be appended here. No implementation has been committed.

## Execution ledger — 2026-11-03

- RED: `venv/Scripts/python.exe -B -m unittest tests.test_eval_corpus` initially
  failed because `rag_app.eval_dataset` did not exist. Tests were written first.
- Fixed implementation defects exposed by tests: provenance root was one parent
  too high; rollback/close exceptions could override sanitized errors. Explicit
  regression tests verify current checkout provenance and sanitized cleanup.
- Ruling: pytest is not installed, so use the already available unittest runner;
  test cases are pytest-compatible. No packages installed/upgraded.
- Ruling: use local code and current repository configuration, with existing .env
  credentials loaded only in the validation subprocess. The existing DSN's host
  `postgres` is container-only; use inspected existing port mapping
  `127.0.0.1:15432` via a temporary process-local host/port override. No config or
  Compose mutation and no execution of old rag-api code.
- Initial sandbox full regression stalled inside existing FastAPI TestClient.
  Interrupted only that test session, then verified `tests.test_api` outside the
  sandbox restriction: 13 tests, 7 passed/6 explicitly skipped. Full discovery
  outside that restriction completed normally without dependency changes.
- Fresh read-only reviewer: no Critical, two Important (Unicode JSONL splitting;
  malformed nested structural metadata) and one Minor (manifest provenance schema).
  All were reproduced with failing regression tests, then fixed in one pass.
  Ruling: address the manifest schema issue now because required provenance is
  part of this stage's artifact contract. Also test/reject JSON boolean/float
  substitutions which Python numeric equality would otherwise accept.
- Reviewer declined items ruled on: operator assertions/stricter export ACLs are
  the approved contract; missing/other tenant metadata is excluded, never inferred;
  hostile filesystem races/signature authenticity are outside this local tool's
  contract (exclusive creation and integrity hashes are still enforced); production
  permission changes and writable API integration remain excluded as requested.
- Final focused run:
  `venv/Scripts/python.exe -B -m unittest tests.test_eval_corpus tests.test_evaluation tests.test_rerank tests.test_vector_store tests.test_online_processing tests.test_config tests.test_deployment_config`
  -> **86 tests OK**, including **28 new unit tests**.
- Final full run: `venv/Scripts/python.exe -B -m unittest discover`
  -> **209 tests, 201 passed, 8 skipped**. Six skips are existing writable-DB API
  integration tests without DSN; two are the opt-in readonly tests without their
  explicit scope. Existing Starlette deprecation warning remains; no upgrades.
- Final real integration subprocess runs
  `unittest.defaultTestLoader.loadTestsFromName('tests.test_eval_corpus_postgres')`
  with explicit `default/default/public` scope and the temporary existing DSN
  route described above -> **2 tests OK, 0 skips**, using current checkout code.
  Tests use only transaction commands/SHOW/SELECT, with CTE-only fixture data.
- Final actual CLI `main(['export-eval-chunks', '--collection', 'default',
  '--tenant-id', 'default', '--permission-tags', 'public', '--output-dir',
  '<current repo>/storage/evaluation/corpus/stage1-20261103-79e33ff2', '--json'])`
  -> **447 chunks, 3 documents**, verifier passed, before/after fingerprints of
  Chunk/document/knowledge-version/active-pointer tables identical.
- Artifact: `storage/evaluation/corpus/stage1-20261103-79e33ff2/corpus.manifest.json`.
  Snapshot ID: `sha256:d9f1fa7851b10fba00665e0478b88f136dc50879afef489ca15fee51ff704051`.
  Producer corpus.py SHA-256:
  `2f92a38a4863c92f5bc4ac6e52d3b0054c2b13384a16563e59f1795104fc0df7`.
- No Ollama/generation/review/compiler/benchmark work performed. No commits/pushes.
  Stop here for user acceptance; do not continue to the next stage automatically.
