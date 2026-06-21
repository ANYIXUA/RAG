const assert = require("node:assert/strict");
const { createSseParser, parseSseMessage } = require("../../web/streamClient");

assert.deepEqual(parseSseMessage('event: answer_delta\ndata: {"delta":"第一段"}'), {
  event: "answer_delta",
  data: { delta: "第一段" },
});

const events = [];
const parser = createSseParser((item) => events.push(item));
parser.push('event: retrieval\ndata: {"request_id":"req-1"}\n\n');
parser.push('event: answer_delta\ndata: {"delta":"第一');
parser.push('段"}\n\n');
parser.finish();

assert.deepEqual(events, [
  { event: "retrieval", data: { request_id: "req-1" } },
  { event: "answer_delta", data: { delta: "第一段" } },
]);

console.log("streamClient tests passed");
