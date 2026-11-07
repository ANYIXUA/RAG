import fs from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const resolve = createRequire(import.meta.url).resolve;
const runtime = "C:/Users/10039/.cache/codex-runtimes/codex-primary-runtime/dependencies/node";
const { Workbook, FileBlob, SpreadsheetFile } = await import(pathToFileURL(resolve("@oai/artifact-tool", {paths:[runtime]})).href);
const local = (path) => new URL(path, import.meta.url);
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(fileURLToPath(local("../review.xlsx"))));
const sheet = workbook.worksheets.getItemAt(0);
const mode = process.argv[2];
if (mode === "before") {
  const preview = await workbook.render({sheetName: sheet.name, range: "G4:J9", scale: 0.8});
  await fs.writeFile(local("before.png"), new Uint8Array(await preview.arrayBuffer()));
} else {
  const updates = JSON.parse(await fs.readFile(local("updates.json"), "utf8"));
  for (const [cell, spec] of Object.entries(updates)) {
    const range = sheet.getRange(cell);
    assert.equal(range.values[0][0] || "", spec.original || "", cell);
    range.values = [[spec.value]];
    const row = sheet.getRange(`A${cell.slice(1)}:M${cell.slice(1)}`);
    if (row.format.rowHeight < spec.height) row.format.rowHeight = spec.height;
  }
  workbook.recalculate();
  for (const [cell, spec] of Object.entries(updates)) assert.equal(sheet.getRange(cell).values[0][0], spec.value);
  await workbook.inspect({kind: "region", sheetId: sheet.name, range: "H5:J16", maxChars: 100});
  const staged = await SpreadsheetFile.exportXlsx(workbook);
  await staged.save(fileURLToPath(local("staged.xlsx")));
}
