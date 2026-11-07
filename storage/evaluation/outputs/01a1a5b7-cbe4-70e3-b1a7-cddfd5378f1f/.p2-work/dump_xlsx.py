# -*- coding:utf-8 -*-
"""Dump the current state of review.xlsx for inspection (read-only)."""
import json
import sys
import io
from openpyxl import load_workbook

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
XLSX = BASE + r"\review.xlsx"

wb = load_workbook(XLSX, data_only=False)
print("sheets:", wb.sheetnames)

for name in wb.sheetnames:
    ws = wb[name]
    print(f"--- sheet {name}: dims={ws.dimensions} max_row={ws.max_row} max_col={ws.max_column}")

ws = wb[wb.sheetnames[0]]
rows = []
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=max(13, ws.max_column)):
    vals = []
    for c in row:
        v = c.value
        if v is None:
            v = None
        elif isinstance(v, str):
            v = v
        else:
            v = repr(v)
        vals.append(v)
    rows.append(vals)

for i, r in enumerate(rows, start=1):
    short = []
    for v in r:
        if v is None:
            short.append(None)
        elif isinstance(v, str):
            s = v.replace("\n", "\\n")
            short.append(s if len(s) <= 90 else s[:90] + f"...[len={len(v)}]")
        else:
            short.append(v)
    print(f"R{i}: {short}")

# Save full dump for detailed inspection
full = []
for i, r in enumerate(rows, start=1):
    full.append({"row": i, "cells": {f"{chr(64+j+1)}": v for j, v in enumerate(r) if v is not None}})
with open(BASE + r"\.p2-work\dump_full.json", "w", encoding="utf-8") as f:
    json.dump(full, f, ensure_ascii=False, indent=1)
print("full dump saved")
