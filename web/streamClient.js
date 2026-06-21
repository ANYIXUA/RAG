(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.StreamClient = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  function createSseParser(onEvent) {
    let buffer = "";
    return {
      push(chunk) {
        buffer += chunk;
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() || "";
        parts.filter(Boolean).forEach((part) => onEvent(parseSseMessage(part)));
      },
      finish() {
        const pending = buffer.trim();
        buffer = "";
        if (pending) {
          onEvent(parseSseMessage(pending));
        }
      },
    };
  }

  function parseSseMessage(raw) {
    const lines = String(raw || "").split(/\r?\n/);
    let event = "message";
    const dataLines = [];
    lines.forEach((line) => {
      if (line.startsWith("event:")) {
        event = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice("data:".length).trimStart());
      }
    });
    const dataText = dataLines.join("\n");
    return {
      event,
      data: dataText ? JSON.parse(dataText) : {},
    };
  }

  return {
    createSseParser,
    parseSseMessage,
  };
});
