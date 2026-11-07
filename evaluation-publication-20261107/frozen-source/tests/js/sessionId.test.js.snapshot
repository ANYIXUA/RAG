const assert = require("node:assert/strict");
const { createSessionId, ensureSessionId } = require("../../web/sessionId");

const fixedDate = new Date("2026-06-23T23:12:45Z");
assert.equal(
  createSessionId({
    now: fixedDate,
    tenantId: "default",
    source: "web",
    randomHex: "ab12cd34",
  }),
  "sess_20260623231245_default_web_ab12cd34",
);

const storage = new Map();
const localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
};

const generated = ensureSessionId({
  currentValue: "",
  tenantId: "default",
  localStorage,
  now: fixedDate,
  randomHex: "ab12cd34",
});
assert.equal(generated, "sess_20260623231245_default_web_ab12cd34");
assert.equal(localStorage.getItem("rag_session_id"), generated);
assert.equal(
  ensureSessionId({ currentValue: "", tenantId: "default", localStorage }),
  generated,
);
assert.equal(
  ensureSessionId({ currentValue: "manual-session", tenantId: "default", localStorage }),
  "manual-session",
);

console.log("sessionId tests passed");
