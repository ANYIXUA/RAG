(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.TraceModel = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  function buildTraceSteps(trace) {
    const actual = trace || {};
    return [
      {
        key: "context",
        title: "会话上下文",
        status: "done",
        latency: formatMs(actual.context_latency_ms),
        value: actual.is_follow_up ? "识别为追问" : "独立问题",
        detail: listText(actual.context_terms, "无上下文关键术语"),
      },
      {
        key: "intent",
        title: "意图识别",
        status: "done",
        latency: formatMs(actual.intent_latency_ms),
        value: confidenceText(actual.intent_label, actual.intent_confidence),
        detail: actual.intent_reason || "未返回意图说明",
      },
      {
        key: "rewrite",
        title: "查询改写",
        status: "done",
        latency: formatMs(actual.rewrite_latency_ms),
        value: ruleText(actual.query_rewrite_rules),
        detail: expansionText(actual.semantic_expansions, actual.synonym_expansions),
      },
      {
        key: "embedding",
        title: "查询向量化",
        status: "done",
        latency: formatMs(actual.embedding_latency_ms),
        value: embeddingText(actual),
        detail: actual.retrieval_query || "未返回检索查询",
      },
      {
        key: "retrieval",
        title: "混合检索",
        status: actual.retrieved_count > 0 ? "done" : "warn",
        latency: formatMs(actual.vector_search_latency_ms),
        value: `${valueOrDash(actual.retrieved_count)} 条候选`,
        detail: retrievalText(actual),
      },
      {
        key: "rerank",
        title: "重排",
        status: rerankStatus(actual),
        latency: formatMs(actual.rerank_latency_ms),
        value: rerankValue(actual),
        detail: actual.rerank_provider ? `提供方：${actual.rerank_provider}` : "未返回重排提供方",
      },
      {
        key: "generation",
        title: "回答生成",
        status: actual.degradation_reason ? "warn" : "done",
        latency: formatMs(actual.generation_latency_ms),
        value: actual.degradation_reason ? "已降级" : "生成完成",
        detail: actual.degradation_reason || "未触发降级",
      },
    ];
  }

  function summarizeTraceMetrics(trace) {
    const actual = trace || {};
    const retrievalTotal = sumNumbers(
      actual.embedding_latency_ms,
      actual.vector_search_latency_ms,
      actual.rerank_latency_ms,
    );
    return [
      { label: "总耗时", value: formatMs(actual.latency_ms) },
      { label: "检索耗时", value: formatMs(retrievalTotal) },
      { label: "生成耗时", value: formatMs(actual.generation_latency_ms) },
      {
        label: "召回 / 入选",
        value: `${valueOrDash(actual.retrieved_count)} / ${valueOrDash(actual.reranked_count)}`,
      },
    ];
  }

  function formatMs(value) {
    if (value === null || value === undefined || value === "") {
      return "-";
    }
    const number = Number(value);
    if (!Number.isFinite(number)) {
      return "-";
    }
    return `${number.toFixed(1)} ms`;
  }

  function confidenceText(label, confidence) {
    const confidenceValue = Number(confidence);
    if (!label) {
      return "未识别";
    }
    if (!Number.isFinite(confidenceValue)) {
      return label;
    }
    return `${label} / ${(confidenceValue * 100).toFixed(0)}%`;
  }

  function ruleText(rules) {
    return Array.isArray(rules) && rules.length ? `${rules.length} 条规则` : "无规则命中";
  }

  function expansionText(semantic, synonyms) {
    const parts = [];
    if (Array.isArray(semantic) && semantic.length) {
      parts.push(`语义扩展：${semantic.join("、")}`);
    }
    if (Array.isArray(synonyms) && synonyms.length) {
      parts.push(`同义词：${synonyms.join("、")}`);
    }
    return parts.join("；") || "未扩展";
  }

  function embeddingText(trace) {
    const dimensions = valueOrDash(trace.query_embedding_dimensions);
    const cache = trace.query_embedding_cache_hit ? "命中缓存" : "未命中缓存";
    return `${dimensions} 维 / ${cache}`;
  }

  function retrievalText(trace) {
    const mode = trace.retrieval_mode || "-";
    const semantic = numberText(trace.semantic_weight);
    const bm25 = numberText(trace.bm25_weight);
    const threshold = numberText(trace.relative_score_threshold);
    return `模式：${mode}；语义/BM25：${semantic}/${bm25}；相对阈值：${threshold}`;
  }

  function rerankStatus(trace) {
    if (trace.rerank_applied) {
      return "done";
    }
    return trace.rerank_skip_reason ? "skipped" : "warn";
  }

  function rerankValue(trace) {
    if (trace.rerank_applied) {
      return `${valueOrDash(trace.reranked_count)} 条结果`;
    }
    return trace.rerank_skip_reason || "未执行";
  }

  function listText(items, emptyText) {
    return Array.isArray(items) && items.length ? items.join("、") : emptyText;
  }

  function valueOrDash(value) {
    if (value === null || value === undefined || value === "") {
      return "-";
    }
    return String(value);
  }

  function numberText(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(2) : "-";
  }

  function sumNumbers() {
    return Array.from(arguments).reduce((sum, value) => {
      const number = Number(value);
      return Number.isFinite(number) ? sum + number : sum;
    }, 0);
  }

  return {
    buildTraceSteps,
    summarizeTraceMetrics,
    formatMs,
  };
});
