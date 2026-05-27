const els = {
  form: document.querySelector("#queryForm"),
  apiBase: document.querySelector("#apiBase"),
  topK: document.querySelector("#topK"),
  tenantId: document.querySelector("#tenantId"),
  permissionTags: document.querySelector("#permissionTags"),
  sessionId: document.querySelector("#sessionId"),
  userId: document.querySelector("#userId"),
  question: document.querySelector("#question"),
  queryButton: document.querySelector("#queryButton"),
  healthButton: document.querySelector("#healthButton"),
  readyButton: document.querySelector("#readyButton"),
  clearButton: document.querySelector("#clearButton"),
  copyAnswerButton: document.querySelector("#copyAnswerButton"),
  healthBadge: document.querySelector("#healthBadge"),
  readyBadge: document.querySelector("#readyBadge"),
  latency: document.querySelector("#latency"),
  errorBox: document.querySelector("#errorBox"),
  answerText: document.querySelector("#answerText"),
  sourceCount: document.querySelector("#sourceCount"),
  sources: document.querySelector("#sources"),
  requestId: document.querySelector("#requestId"),
  traceSummary: document.querySelector("#traceSummary"),
  rawJson: document.querySelector("#rawJson"),
};

let lastAnswer = "";

els.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runQuery();
});

els.healthButton.addEventListener("click", () => checkStatus("health"));
els.readyButton.addEventListener("click", () => checkStatus("ready"));
els.clearButton.addEventListener("click", clearResult);
els.copyAnswerButton.addEventListener("click", copyAnswer);

async function runQuery() {
  const payload = {
    question: els.question.value.trim(),
    top_k: Number(els.topK.value || 3),
    tenant_id: emptyToNull(els.tenantId.value),
    permission_tags: splitTags(els.permissionTags.value),
    session_id: emptyToNull(els.sessionId.value),
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
    const data = await requestJson("/query", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    els.latency.textContent = `${Math.round(performance.now() - startedAt)} ms`;
    renderQueryResult(data);
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

function renderQueryResult(data) {
  lastAnswer = data?.answer || "";
  els.answerText.textContent = lastAnswer || "没有返回 answer。";
  els.answerText.classList.toggle("empty", !lastAnswer);
  els.rawJson.textContent = pretty(data);

  const requestId = data?.request_id || data?.trace?.request_id || "";
  els.requestId.textContent = requestId || "无 request_id";

  renderSources(data?.sources || []);
  renderTrace(data?.trace || {});
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
  els.latency.textContent = "0 ms";
  els.answerText.textContent = "等待查询结果";
  els.answerText.classList.add("empty");
  els.sourceCount.textContent = "0";
  els.sources.replaceChildren();
  els.requestId.textContent = "无 request_id";
  els.traceSummary.replaceChildren();
  els.rawJson.textContent = "{}";
  clearError();
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

function numberText(value) {
  return typeof value === "number" ? value.toFixed(4) : "-";
}

function chip(text) {
  const span = document.createElement("span");
  span.textContent = text;
  return span;
}
