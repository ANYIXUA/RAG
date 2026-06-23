(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.SessionId = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  const STORAGE_KEY = "rag_session_id";

  function createSessionId(options = {}) {
    const now = options.now || new Date();
    const tenantId = sessionPart(options.tenantId || "default");
    const source = sessionPart(options.source || "web");
    const randomHex = (options.randomHex || makeRandomHex()).slice(0, 8).toLowerCase();
    return `sess_${formatTimestamp(now)}_${tenantId}_${source}_${randomHex}`;
  }

  function ensureSessionId(options = {}) {
    const currentValue = String(options.currentValue || "").trim();
    if (currentValue) {
      return currentValue;
    }
    const storage = options.localStorage;
    const stored = readStoredSessionId(storage);
    if (stored) {
      return stored;
    }
    const generated = createSessionId(options);
    writeStoredSessionId(storage, generated);
    return generated;
  }

  function formatTimestamp(value) {
    const date = value instanceof Date ? value : new Date(value);
    const year = date.getUTCFullYear();
    const month = pad2(date.getUTCMonth() + 1);
    const day = pad2(date.getUTCDate());
    const hour = pad2(date.getUTCHours());
    const minute = pad2(date.getUTCMinutes());
    const second = pad2(date.getUTCSeconds());
    return `${year}${month}${day}${hour}${minute}${second}`;
  }

  function readStoredSessionId(storage) {
    try {
      return String(storage?.getItem(STORAGE_KEY) || "").trim();
    } catch {
      return "";
    }
  }

  function writeStoredSessionId(storage, sessionId) {
    try {
      storage?.setItem(STORAGE_KEY, sessionId);
    } catch {
      return;
    }
  }

  function sessionPart(value) {
    return (
      String(value || "default")
        .trim()
        .replace(/[^a-zA-Z0-9_-]+/g, "-")
        .replace(/^[-_]+|[-_]+$/g, "")
        .toLowerCase()
        .slice(0, 32) || "default"
    );
  }

  function makeRandomHex() {
    if (typeof crypto !== "undefined" && crypto.getRandomValues) {
      const bytes = new Uint8Array(4);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("");
    }
    return Math.floor(Math.random() * 0xffffffff)
      .toString(16)
      .padStart(8, "0");
  }

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  return {
    createSessionId,
    ensureSessionId,
    formatTimestamp,
  };
});
