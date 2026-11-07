const assert = require("node:assert/strict");
const { buildTraceSteps, summarizeTraceMetrics } = require("../../web/traceModel");

const trace = {
  request_id: "req-1",
  is_follow_up: false,
  intent_label: "query_rule",
  intent_confidence: 0.72,
  rewritten_query: "全光组网装维要求",
  retrieval_query: "全光组网装维要求 业务规则 操作规范",
  semantic_expansions: ["业务规则", "操作规范"],
  query_rewrite_rules: ["normalize_whitespace"],
  query_embedding_dimensions: 1024,
  query_embedding_cache_hit: true,
  retrieved_count: 8,
  reranked_count: 3,
  rerank_applied: false,
  rerank_skip_reason: "provider_disabled",
  degradation_reason: null,
  context_latency_ms: 1.2,
  intent_latency_ms: 2.3,
  rewrite_latency_ms: 3.4,
  embedding_latency_ms: 120.1,
  vector_search_latency_ms: 45.6,
  rerank_latency_ms: 0,
  generation_latency_ms: 800.2,
  latency_ms: 980.4,
};

const steps = buildTraceSteps(trace);
assert.equal(steps.length, 7);
assert.deepEqual(
  steps.map((step) => step.key),
  ["context", "intent", "rewrite", "embedding", "retrieval", "rerank", "generation"],
);
assert.equal(steps[0].status, "done");
assert.equal(steps[3].value, "1024 维 / 命中缓存");
assert.equal(steps[5].status, "skipped");
assert.equal(steps[5].value, "provider_disabled");

const metrics = summarizeTraceMetrics(trace);
assert.deepEqual(metrics, [
  { label: "总耗时", value: "980.4 ms" },
  { label: "检索耗时", value: "165.7 ms" },
  { label: "生成耗时", value: "800.2 ms" },
  { label: "召回 / 入选", value: "8 / 3" },
]);

console.log("traceModel tests passed");
