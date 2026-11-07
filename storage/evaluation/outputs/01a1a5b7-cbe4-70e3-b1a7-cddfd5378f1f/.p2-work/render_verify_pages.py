# -*- coding:utf-8 -*-
"""Render specific PDF pages from the ORIGINAL data/ PDFs for independent verification."""
import sys
import fitz

sys.stdout.reconfigure(encoding="utf-8")
DATA = r"D:\AgentAIProgect\RAG\data"
OUT = r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f\.p2-work\verify"

JOBS = [
    ("电信基础设施维护规程.pdf", [29, 254, 277, 278, 280, 343]),
    ("智慧家庭装维工程与管理职业技能等级标准.pdf", [6, 16, 18, 19]),
    ("中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf", [1, 25, 58, 62]),
]

for name, pages in JOBS:
    doc = fitz.open(DATA + "\\" + name)
    print(f"{name}: total physical pages = {doc.page_count}")
    for p in pages:
        if p > doc.page_count:
            print(f"  page {p}: OUT OF RANGE")
            continue
        page = doc[p - 1]  # 1-based page number -> 0-based index
        zoom = 2.2
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        outpath = OUT + f"\\pg{p:03d}.png"
        pix.save(outpath)
        text_head = " ".join(page.get_text("text").split())[:220]
        print(f"  page {p} rendered -> {outpath}")
        print(f"    text head: {text_head}")
    doc.close()
print("done")
