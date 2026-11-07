# P6-E2E-Run-01 execution plan

Binding specification: user's 500-case real RAG run request. Budget authorized
2026-11-05: total CNY20 for smoke, generation, embedding, retries and judging.

- [x] Verify frozen Silver SHA/count/IDs and original Gold/Holdout/PDF hashes.
- [x] Trace current production `OnlineQueryProcessor.process`; preserve query
  rewrite, intent, hybrid retrieval, context construction and real generation.
- [x] Add an isolated evaluation runner and focused tests before implementation.
  Do not edit the old generation, execution or scoring scripts or business code.
- [x] Use current configured qwen-turbo / text-embedding-v4, production top_k=4,
  candidate_k=20, weights=.7/.3, filters=.05/.35; explicitly select rerank=none
  in the run settings because config/retrieval.json overrides the environment.
  Record this authorized selection and its difference from P5 retrieval-only
  top_k=20 and disabled rewrite/intent. Do not claim identical P5 execution.
- [x] Compare database active Chunk IDs/text to frozen 447 before and after.
  Use real PostgreSQL and Redis. Isolate each attempt's session. Record SDK
  request/response, returned model, tokens, timings, retrieved records and actual
  rendered/truncated LLM messages. Observers must return original values and
  preserve original request arguments, timeouts, prompts and inference options.
- [x] Run smoke: 2 cases/type, 10 total, all must complete actual generation with
  full trace and hybrid mode. Test error accounting separately in unit tests.
- [x] Run all remaining cases, <=3 threads with thread-local processors, batches
  of 25, immutable per-attempt/per-case files, append-audited model calls, at most
  3 attempts/case. Smoke is included exactly once in the 500-case denominator.
- [x] Score actual successful answers with separate judge calls; explicitly
  disclose same qwen-turbo model self-evaluation bias. Keep all actual context,
  validate judge schema, separate judge failures from execution failures.
  Treat unanswerable scores as provisional. p6s-0473 correctness=null and exclude
  it from Silver correctness numerator/denominator regardless of judge opinion.
- [x] Export states/traces/answers/scores, denominator-labelled metrics, eight
  failure categories, 40 blank human review rows, report, reproducible commands
  and hash manifest. Recheck inputs. Stop without Holdout or commit/push.

Cost protocol: public list prices are estimates, not provider invoices. Reserve
conservative UTF-8 byte token bounds before requests. Unknown usage/failures keep
their reservation. Durable requests without responses count against the cap on
resume. SDK retries remain at configured zero; application retries are logged.

Review focus: caught generation exceptions yielding fallback text must never
count as successful real LLM; per-worker mutable state must not cross threads;
no session contamination across retries; partial attempts consume retry budget;
missing judge fields must fail scoring; context truncation must be observable.


Execution ledger (final verified on client date 2026-11-06):
- qwen-turbo: smoke10 failed,30 generation attempts429; one later health request
  also429; exact alias absent from account model inventory. Old directory retained.
- User explicitly selected qwen-flash. A separate variant directory preserves old
  failures and charges all prior reservations against the same CNY20 cap.
- qwen-flash real RAG:500 successes,0 failures/timeouts/retries,500 unique IDs,
  no prior session turns, hybrid mode and no Cross-Encoder throughout.
- Judge:500 terminal scoring states;490 valid,10 failed/uncertain. Original18
  technical failure files retained;8 valid already-paid responses recovered into
  an explicit overlay. No case received more than3 judge requests.
- Minimal evaluation fixes: isolated thread state, exact rendered-context capture,
  durable attempt recovery, judge schema/identity guards, N/A evidence handling,
  bounded formatting only. Production code/data/prompts/settings files unchanged.
- Related pytest40 passed (one third-party deprecation warning). All input/code/
  prompt/config fingerprints and database447Chunk/vector hash rechecked.
- Repeat run and score commands made0 new API requests and changed0 case/attempt/
  score bytes. Full trace,metrics,40 blank human review rows and manifests saved.
- Known list-price estimate including prior known usage: CNY0.94129155; conservative
  total reservations CNY1.48271805/20. Actual provider billing remains unknown.
- No Holdout execution,automatic tuning,human signoff,commit or push.
