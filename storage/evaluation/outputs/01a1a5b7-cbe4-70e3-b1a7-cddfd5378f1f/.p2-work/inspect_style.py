# -*- coding:utf-8 -*-
"""Inspect formatting details of review.xlsx (read-only)."""
import sys
from openpyxl import load_workbook

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
wb = load_workbook(BASE + r"\review.xlsx")
ws = wb["候选审核"]

print("== column dimensions ==")
for key, dim in ws.column_dimensions.items():
    print(key, "width=", dim.width, "custom=", dim.customWidth, "hidden=", dim.hidden)

print("== row heights 4-20 ==")
for r in range(4, 21):
    d = ws.row_dimensions.get(r)
    h = d.height if d else None
    print("row", r, "height=", h)

print("== cell styles sample ==")
for addr in ["H4", "H5", "H16", "I5", "J5", "A5", "B5", "F5", "G5", "D5", "K5", "L5", "M5"]:
    c = ws[addr]
    fill = c.fill
    fg = fill.fgColor.rgb if fill.fgColor and fill.fgColor.type == "rgb" else (fill.fgColor.theme if fill.fgColor else None)
    print(addr,
          "| fill_type=", fill.fill_type, "fg=", fg,
          "| wrap=", c.alignment.wrap_text, "halign=", c.alignment.horizontal, "valign=", c.alignment.vertical,
          "| font=", c.font.name, c.font.size, "bold=", c.font.bold,
          "| border L/R/T/B=", c.border.left.style, c.border.right.style, c.border.top.style, c.border.bottom.style)

print("== merged cells ==")
print(ws.merged_cells.ranges)
print("== freeze panes ==", ws.freeze_panes)
print("== sheet dims ==", ws.dimensions)
