# P3-Pilot-02 implementation plan

Goal: repair lexical candidate recall, audit reranking, and report the unchanged 22-query experiment honestly.

Constraints: preserve Gold, PDFs, frozen chunks, human reviews and fixed model/configuration; no commit/push. Existing draft and prior artifacts are saved under baseline/ before editing.

- [x] Reproduce SQL candidate starvation using the HEAD implementation and actual database; record priority/update distributions and ILIKE hit counts.
- [x] Add regressions for candidates beyond early limits, late query tokens and authorization, then verify failure before repair.
- [x] Remove relevance-blind keyword preselection while keeping collection/status and authorization rules; keep existing BM25/fusion formula.
- [x] Run the original evaluator with the saved baseline and fixed implementation, then repeat the fixed run. Verify input hashes, actual DB/corpus equivalence, rankings and configuration.
- [x] Audit real CrossEncoder input pairs, score association/direction, token truncation and degraded-query results without model tuning.
- [x] Run relevant and full unit tests; deliver metrics, per-query ranks, reproducible commands and limitations in report.md.

Review focus: more than 2000 literal matches; discriminating terms after token 12; empty query; unauthorized high-scoring chunks; score-to-chunk association and truncation after rerank. Large-corpus scanning cost is an explicit limitation of this minimal repair.
