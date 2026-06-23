const els = {
  form: document.querySelector("#queryForm"),
  apiBase: document.querySelector("#apiBase"),
  topK: document.querySelector("#topK"),
  tenantId: document.querySelector("#tenantId"),
  permissionTags: document.querySelector("#permissionTags"),
  sessionId: document.querySelector("#sessionId"),
  userId: document.querySelector("#userId"),
  adminToken: document.querySelector("#adminToken"),
  question: document.querySelector("#question"),
  queryButton: document.querySelector("#queryButton"),
  healthButton: document.querySelector("#healthButton"),
  readyButton: document.querySelector("#readyButton"),
  clearButton: document.querySelector("#clearButton"),
  copyAnswerButton: document.querySelector("#copyAnswerButton"),
  traceFetchButton: document.querySelector("#traceFetchButton"),
  healthBadge: document.querySelector("#healthBadge"),
  readyBadge: document.querySelector("#readyBadge"),
  latency: document.querySelector("#latency"),
  errorBox: document.querySelector("#errorBox"),
  processHint: document.querySelector("#processHint"),
  traceMetrics: document.querySelector("#traceMetrics"),
  processSteps: document.querySelector("#processSteps"),
  queryFlow: document.querySelector("#queryFlow"),
  opsTraceBox: document.querySelector("#opsTraceBox"),
  answerText: document.querySelector("#answerText"),
  sourceCount: document.querySelector("#sourceCount"),
  sources: document.querySelector("#sources"),
  requestId: document.querySelector("#requestId"),
  traceSummary: document.querySelector("#traceSummary"),
  rawJson: document.querySelector("#rawJson"),
};

let lastAnswer = "";
let lastRequestId = "";

initializeSessionId();

els.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runQuery();
});

els.healthButton.addEventListener("click", () => checkStatus("health"));
els.readyButton.addEventListener("click", () => checkStatus("ready"));
els.clearButton.addEventListener("click", clearResult);
els.copyAnswerButton.addEventListener("click", copyAnswer);
els.traceFetchButton.addEventListener("click", fetchOpsTrace);

async function runQuery() {
  const sessionId = ensureCurrentSessionId();
  const payload = {
    question: els.question.value.trim(),
    top_k: Number(els.topK.value || 3),
    tenant_id: emptyToNull(els.tenantId.value),
    permission_tags: splitTags(els.permissionTags.value),
    session_id: sessionId,
    user_id: emptyToNull(els.userId.value),
  };

  if (!payload.question) {
    showError("问题不能为空。");
    return;
  }

  setBusy(true);
  clearError();
  const startedAt = performance.now();

  try {
    prepareStreamingResult();
    try {
      await requestSse("/query/stream", payload, handleQueryStreamEvent);
    } catch (streamError) {
      if (!canFallbackToSync(streamError)) {
        throw streamError;
      }
      const data = await requestJson("/query", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderQueryResult(data);
    }
    els.latency.textContent = `${Math.round(performance.now() - startedAt)} ms`;
  } catch (error) {
    els.latency.textContent = `${Math.round(performance.now() - startedAt)} ms`;
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function checkStatus(kind) {
  const badge = kind === "health" ? els.healthBadge : els.readyBadge;
  setBadge(badge, `${kind} 检查中`, "neutral");
  clearError();

  try {
    const data = await requestJson(`/${kind}`);
    const ok = kind === "health" ? data.status === "ok" : data.status === "ready";
    setBadge(badge, `${kind} ${data.status || "ok"}`, ok ? "ok" : "warn");
    els.rawJson.textContent = pretty(data);
  } catch (error) {
    setBadge(badge, `${kind} 失败`, "error");
    showError(error.message);
  }
}

async function requestJson(path, options = {}) {
  const base = els.apiBase.value.trim().replace(/\/+$/, "");
  if (!base) {
    throw new Error("API 地址不能为空。");
  }
  const { headers = {}, ...fetchOptions } = options;

  const response = await fetch(`${base}${path}`, {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      Accept: "application/json",
      ...headers,
    },
  });

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    throw new Error(formatHttpError(response.status, data));
  }
  return data;
}

async function requestSse(path, payload, onEvent) {
  const base = els.apiBase.value.trim().replace(/\/+$/, "");
  if (!base) {
    throw new Error("API 地址不能为空。");
  }
  if (!window.StreamClient) {
    const error = new Error("当前页面缺少流式解析模块，已回退同步查询。");
    error.status = 404;
    throw error;
  }

  const response = await fetch(`${base}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    let data = text;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    const error = new Error(formatHttpError(response.status, data));
    error.status = response.status;
    throw error;
  }
  if (!response.body) {
    throw new Error("当前浏览器不支持 ReadableStream。");
  }

  let streamError = null;
  const decoder = new TextDecoder();
  const parser = window.StreamClient.createSseParser((message) => {
    if (message.event === "error") {
      streamError = new Error(message.data?.message || "流式查询失败");
      return;
    }
    onEvent(message);
  });
  const reader = response.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    parser.push(decoder.decode(value, { stream: true }));
  }
  const tail = decoder.decode();
  if (tail) {
    parser.push(tail);
  }
  parser.finish();
  if (streamError) {
    throw streamError;
  }
}

function canFallbackToSync(error) {
  return error?.status === 404 || error?.status === 405;
}

function handleQueryStreamEvent(message) {
  if (message.event === "retrieval") {
    renderStreamingRetrieval(message.data || {});
  } else if (message.event === "answer_delta") {
    appendAnswerDelta(message.data?.delta || "");
  } else if (message.event === "complete") {
    renderQueryResult(message.data || {});
  }
}

function renderQueryResult(data) {
  lastAnswer = data?.answer || "";
  els.answerText.textContent = lastAnswer || "没有返回 answer。";
  els.answerText.classList.toggle("empty", !lastAnswer);
  els.rawJson.textContent = pretty(data);

  const requestId = data?.request_id || data?.trace?.request_id || "";
  lastRequestId = requestId;
  els.requestId.textContent = requestId || "无 request_id";
  els.traceFetchButton.disabled = !requestId;
  els.opsTraceBox.classList.add("hidden");
  els.opsTraceBox.replaceChildren();

  renderSources(data?.sources || []);
  renderTrace(data?.trace || {});
  renderProcess(data?.trace || {}, data?.sources || []);
}

function prepareStreamingResult() {
  lastAnswer = "";
  lastRequestId = "";
  els.answerText.textContent = "等待检索结果";
  els.answerText.classList.add("empty");
  els.sourceCount.textContent = "0";
  els.sources.replaceChildren();
  els.requestId.textContent = "无 request_id";
  els.traceFetchButton.disabled = true;
  els.opsTraceBox.classList.add("hidden");
  els.opsTraceBox.replaceChildren();
  els.traceSummary.replaceChildren();
  els.traceMetrics.replaceChildren();
  els.processSteps.replaceChildren();
  els.queryFlow.replaceChildren();
  els.processHint.textContent = "已发送请求，等待检索结果";
  els.rawJson.textContent = pretty({ stream: "waiting" });
}

function renderStreamingRetrieval(data) {
  lastRequestId = data.request_id || "";
  els.requestId.textContent = lastRequestId || "无 request_id";
  els.traceFetchButton.disabled = !lastRequestId;
  els.processHint.textContent = lastRequestId
    ? `request_id: ${lastRequestId}，检索完成，正在生成`
    : "检索完成，正在生成";
  renderSources(data.sources || []);
  els.processSteps.replaceChildren();
  appendStreamStep(
    "检索完成",
    `${data.reranked_count ?? data.retrieved_count ?? 0} 条入选来源`,
    "已进入模型生成阶段",
    "done",
  );
  appendStreamStep("回答生成", "接收中", "正在流式返回 token", "warn");
  els.rawJson.textContent = pretty({ stream_event: "retrieval", data });
}

function appendAnswerDelta(delta) {
  if (!delta) {
    return;
  }
  if (!lastAnswer) {
    els.answerText.textContent = "";
    els.answerText.classList.remove("empty");
  }
  lastAnswer += delta;
  els.answerText.textContent = lastAnswer;
}

function appendStreamStep(title, value, detail, status) {
  const item = document.createElement("div");
  item.className = `process-step ${status}`;
  const marker = document.createElement("span");
  marker.className = "step-marker";
  marker.textContent = String(els.processSteps.children.length + 1);
  const body = document.createElement("div");
  body.className = "step-body";
  const head = document.createElement("div");
  head.className = "step-head";
  const strong = document.createElement("strong");
  strong.textContent = title;
  const latency = document.createElement("span");
  latency.textContent = "实时";
  head.append(strong, latency);
  const valueNode = document.createElement("p");
  valueNode.className = "step-value";
  valueNode.textContent = value;
  const detailNode = document.createElement("p");
  detailNode.className = "step-detail";
  detailNode.textContent = detail;
  body.append(head, valueNode, detailNode);
  item.append(marker, body);
  els.processSteps.append(item);
}

function renderProcess(trace, sources) {
  els.traceMetrics.replaceChildren();
  els.processSteps.replaceChildren();
  els.queryFlow.replaceChildren();
  els.processHint.textContent = trace?.request_id
    ? `request_id: ${trace.request_id}`
    : "本次响应未返回 trace。";

  if (!trace || !trace.request_id || !window.TraceModel) {
    const empty = document.createElement("p");
    empty.className = "source-text";
    empty.textContent = "等待一次查询后展示检索过程。";
    els.processSteps.append(empty);
    return;
  }

  window.TraceModel.summarizeTraceMetrics(trace).forEach((item) => {
    const metric = document.createElement("div");
    metric.className = "metric-card";
    const label = document.createElement("span");
    label.textContent = item.label;
    const value = document.createElement("strong");
    value.textContent = item.value;
    metric.append(label, value);
    els.traceMetrics.append(metric);
  });

  window.TraceModel.buildTraceSteps(trace).forEach((step, index) => {
    const item = document.createElement("div");
    item.className = `process-step ${step.status}`;

    const marker = document.createElement("span");
    marker.className = "step-marker";
    marker.textContent = String(index + 1);

    const body = document.createElement("div");
    body.className = "step-body";

    const head = document.createElement("div");
    head.className = "step-head";
    const title = document.createElement("strong");
    title.textContent = step.title;
    const latency = document.createElement("span");
    latency.textContent = step.latency;
    head.append(title, latency);

    const value = document.createElement("p");
    value.className = "step-value";
    value.textContent = step.value;

    const detail = document.createElement("p");
    detail.className = "step-detail";
    detail.textContent = step.detail;

    body.append(head, value, detail);
    item.append(marker, body);
    els.processSteps.append(item);
  });

  renderQueryFlow(trace, sources);
}

function renderQueryFlow(trace, sources) {
  const rows = [
    ["原始问题", trace.original_query],
    ["归一化", trace.normalized_query],
    ["上下文改写", trace.contextual_query],
    ["标准查询", trace.rewritten_query],
    ["检索查询", trace.retrieval_query],
    ["语义扩展", listText(trace.semantic_expansions)],
    ["权限上下文", permissionText(trace)],
    ["来源页", sourceLocationText(sources)],
  ];

  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    const name = document.createElement("span");
    const content = document.createElement("p");
    name.textContent = label;
    content.textContent = value || "-";
    row.append(name, content);
    els.queryFlow.append(row);
  });
}

function renderSources(sources) {
  els.sourceCount.textContent = String(sources.length);
  els.sources.replaceChildren();

  if (!sources.length) {
    const empty = document.createElement("p");
    empty.className = "source-text";
    empty.textContent = "没有召回来源。";
    els.sources.append(empty);
    return;
  }

  sources.forEach((item, index) => {
    const chunk = item.chunk || {};
    const metadata = chunk.metadata || {};
    const card = document.createElement("div");
    card.className = "source-item";

    const meta = document.createElement("div");
    meta.className = "source-meta";
    meta.append(
      chip(`#${index + 1}`),
      chip(`score ${numberText(item.score)}`),
      chip(metadata.source || "unknown source"),
      chip(metadata.section_title || metadata.title || "未命名章节")
    );

    const text = document.createElement("p");
    text.className = "source-text";
    text.textContent = chunk.text || "";

    card.append(meta, text);
    els.sources.append(card);
  });
}

function renderTrace(trace) {
  els.traceSummary.replaceChildren();
  const rows = [
    ["session", trace.session_id],
    ["intent", trace.intent_label],
    ["retrieved", trace.retrieved_count],
    ["reranked", trace.reranked_count],
    ["latency", trace.latency_ms != null ? `${trace.latency_ms} ms` : null],
    ["retrieval", trace.retrieval_latency_ms != null ? `${trace.retrieval_latency_ms} ms` : null],
    ["generation", trace.generation_latency_ms != null ? `${trace.generation_latency_ms} ms` : null],
    ["cache hit", trace.query_embedding_cache_hit],
    ["degradation", trace.degradation_reason],
  ];

  rows.forEach(([label, value]) => {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value === null || value === undefined || value === "" ? "-" : String(value);
    els.traceSummary.append(dt, dd);
  });
}

function clearResult() {
  lastAnswer = "";
  lastRequestId = "";
  els.latency.textContent = "0 ms";
  els.answerText.textContent = "等待查询结果";
  els.answerText.classList.add("empty");
  els.sourceCount.textContent = "0";
  els.sources.replaceChildren();
  els.requestId.textContent = "无 request_id";
  els.traceSummary.replaceChildren();
  els.traceMetrics.replaceChildren();
  els.processSteps.replaceChildren();
  els.queryFlow.replaceChildren();
  els.opsTraceBox.replaceChildren();
  els.opsTraceBox.classList.add("hidden");
  els.processHint.textContent = "等待查询结果";
  els.traceFetchButton.disabled = true;
  els.rawJson.textContent = "{}";
  clearError();
}

async function fetchOpsTrace() {
  if (!lastRequestId) {
    return;
  }
  els.traceFetchButton.disabled = true;
  els.traceFetchButton.textContent = "拉取中";
  clearError();
  try {
    const data = await requestJson(`/ops/trace/${encodeURIComponent(lastRequestId)}`, {
      headers: adminHeaders(),
    });
    renderOpsTrace(data);
  } catch (error) {
    showError(error.message);
  } finally {
    els.traceFetchButton.disabled = false;
    els.traceFetchButton.textContent = "拉取后台 trace";
  }
}

function renderOpsTrace(data) {
  els.opsTraceBox.replaceChildren();
  els.opsTraceBox.classList.remove("hidden");

  const title = document.createElement("strong");
  title.textContent = data?.found ? "后台 trace 已关联" : "后台 trace 未找到";

  const detail = document.createElement("pre");
  detail.textContent = pretty(data);

  els.opsTraceBox.append(title, detail);
}

async function copyAnswer() {
  if (!lastAnswer) {
    return;
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(lastAnswer);
  } else {
    const textarea = document.createElement("textarea");
    textarea.value = lastAnswer;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.append(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
  els.copyAnswerButton.textContent = "已复制";
  window.setTimeout(() => {
    els.copyAnswerButton.textContent = "复制";
  }, 900);
}

function setBusy(isBusy) {
  els.queryButton.disabled = isBusy;
  els.queryButton.textContent = isBusy ? "查询中" : "发送查询";
}

function setBadge(element, text, tone) {
  element.textContent = text;
  element.className = `badge ${tone}`;
}

function showError(message) {
  els.errorBox.textContent = message;
  els.errorBox.classList.remove("hidden");
}

function clearError() {
  els.errorBox.textContent = "";
  els.errorBox.classList.add("hidden");
}

function formatHttpError(status, data) {
  if (data?.error) {
    return `HTTP ${status}: ${data.error.message || data.error.code}\n${pretty(data.error.detail || data.error)}`;
  }
  return `HTTP ${status}: ${typeof data === "string" ? data : pretty(data)}`;
}

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function emptyToNull(value) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function splitTags(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function adminHeaders() {
  const token = els.adminToken.value.trim();
  return token ? { "X-API-Key": token } : {};
}

function initializeSessionId() {
  if (!window.SessionId || !els.sessionId) {
    return;
  }
  els.sessionId.value = window.SessionId.ensureSessionId({
    currentValue: els.sessionId.value,
    tenantId: els.tenantId.value || "default",
    localStorage: window.localStorage,
  });
}

function ensureCurrentSessionId() {
  if (!window.SessionId || !els.sessionId) {
    return emptyToNull(els.sessionId.value);
  }
  const sessionId = window.SessionId.ensureSessionId({
    currentValue: els.sessionId.value,
    tenantId: els.tenantId.value || "default",
    localStorage: window.localStorage,
  });
  els.sessionId.value = sessionId;
  return sessionId;
}

function listText(items) {
  return Array.isArray(items) && items.length ? items.join("、") : "-";
}

function permissionText(trace) {
  const tenant = trace.tenant_id || "未指定";
  const tags = Array.isArray(trace.permission_tags) && trace.permission_tags.length
    ? trace.permission_tags.join("、")
    : "未指定";
  return `${tenant} / ${tags}`;
}

function sourceLocationText(sources) {
  if (!Array.isArray(sources) || !sources.length) {
    return "-";
  }
  return sources
    .map((item, index) => {
      const metadata = item?.chunk?.metadata || {};
      const title = metadata.section_title || metadata.title || metadata.filename || "未知来源";
      return `#${index + 1} ${title}`;
    })
    .join("；");
}

function numberText(value) {
  return typeof value === "number" ? value.toFixed(4) : "-";
}

function chip(text) {
  const span = document.createElement("span");
  span.textContent = text;
  return span;
}
