# -*- coding: utf-8 -*-
"""g03 建稿：以 review_p2_gold_02_draft.xlsx 为底，生成 review_p2_gold_03_draft.xlsx。
仅改 行11(B07)/行16(B12) 的 H/J 共 4 格；行高只增不减；其余逐格不动。"""
import copy
import math
import shutil
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment

sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f")
SRC = OUT_DIR / "review_p2_gold_02_draft.xlsx"
DST = OUT_DIR / "review_p2_gold_03_draft.xlsx"

H11 = (
    "修订：题面必须限定二维码所属产品（附录 A 有 A.1 光网关、A.2 光路由终端 两类二维码）。"
    "来源 Chunk 核验（g03）：17×17mm 尺寸行在第 62 页 Chunk 38ea5e749604f43f5f040901"
    "（该 Chunk 起于“3. 二维码要求”清单第（3）项，是跨页续文，正文与页面均无“光路由终端”字样，"
    "g03 已重核语料快照全文与第 62 页渲染原件）；"
    "“A.2 光路由终端二维码标识要求”标题在第 61 页 Chunk c120df3a569ae215d69183ac"
    "（该 Chunk 另含清单第（1）（2）项：颜色/黏贴位置）。"
    "回答本问需“标题+尺寸行”两页证据；第 61 页属章节背景，检索相关性弱于第 62 页，"
    "不得因章节背景便自动同等相关（详见 J 列与 p2_gold_03_revision_proposal.md）。"
)

J11 = (
    "1. 原问题存在的问题：题面“二维码的尺寸大小要求”未限定所属产品。附录 A 有两类二维码："
    "A.1 光网关零配置（第 60 页，本规范未给尺寸要求）与 A.2 光路由终端（第 61–62 页）；"
    "“（3）尺寸大小：不小于17×17mm（公差：±1mm)，正方形”仅属 A.2。\n"
    "2. 来源 Chunk 核验（g03 新增，核对语料快照全文+渲染原件）："
    "第 62 页 Chunk 38ea5e749604f43f5f040901 为“3. 二维码要求”清单的跨页续文（首行第（3）项尺寸），"
    "正文与页面均不含“光路由终端”；“A.2 光路由终端二维码标识要求”标题"
    "（另含清单第（1）颜色、（2）黏贴位置）在第 61 页 Chunk c120df3a569ae215d69183ac。"
    "回答本问需“标题+尺寸行”两处证据；第 61 页属章节背景用途，检索相关性弱于第 62 页，"
    "不得因有章节背景便自动同等相关。\n"
    "3. 引用用途区分建议与 Schema 限制：evidence_chunk_ids 建议 = "
    "[c120df3a569ae215d69183ac, 38ea5e749604f43f5f040901]（两页共同证明提问对象与答案成立）；"
    "retrieval_relevant_chunk_ids 建议：第 62 页（答案原文所在）为必要命中，第 61 页为可选背景证据。"
    "现行审核表与候选 Schema 均无区分两用途的字段——本次不改 Schema，"
    "仅记录限制；Gold 构建时应补该字段，或以 text_contains 粒度落评测 target"
    "（详见 p2_gold_03_revision_proposal.md 第 4 节）。\n"
    "4. 推荐修改后的 question：在《中国移动智慧家庭全光组网产品技术规范》附录 A.2 中，"
    "光路由终端二维码的尺寸大小要求是什么？\n"
    "5. 推荐修改后的 proposed_answer：不小于17×17mm（公差：±1mm)，正方形"
    "（语料快照原文逐字，收口括号为半角属解析层样式；尺寸与公差不新增事实）。"
)

H16 = (
    "修订：① 题面直接写出两个知识类别名（答案词“网优”就在题面中），不等检索即可猜中答案——答案泄露；"
    "② 题面问“知识类别”，答案却是技能条目“能对无线局域网覆盖进行优化”——答非所问；"
    "③ 比较对象未指明等级/章节，且“无线局域网相关基础知识”初级与中级均出现——歧义；"
    "④ 原问题含解析空格“基础知 识”。"
    "g03 无泄露重写完成：新题面不含两个类别短语（含解析空格变体，自动断言通过）；"
    "等级对应经第 16/18 页渲染原件重核一致；中级知识要求实含 3.2.1/3.2.2/3.2.3 三项，"
    "推荐答案对中级只列 3.2.3 为“净新增项”简说（是否采用该口径由人工签核定夺）；"
    "两 Chunk 双引用保持不变；查重无高度重复；评测器 any-hit 口径限制已只记录不重构"
    "（详见 J 列与 p2_gold_03_revision_proposal.md）。"
)

J16 = (
    "1. 原问题存在的问题：① 题面问两个“知识类别”哪个更侧重网络优化设计，"
    "答案“能对无线局域网覆盖进行优化”却是技能要求条目（中级 3.2.3），答非所问；"
    "② 题面直接写出“无线局域网网优及软件基础知识”等类别名，不等检索即可凭“网优”猜中答案（答案泄露）；"
    "③ 比较对象未指明等级/章节，“无线局域网相关基础知识”初级与中级均出现，歧义；"
    "④ 原问题含解析空格“基础知 识”。\n"
    "2. 无泄露重写核验（g03）：新题面不含“无线局域网相关基础知识”/"
    "“无线局域网网优及软件基础知识”（含解析空格变体，自动断言通过）。"
    "等级对应（原件渲染第 16/18 页重核）：初级 3.2 基础网络质量检测·知识 3.2.2 无线局域网相关基础知识"
    "（同页 3.2.3 技能“能对无线局域网信号进行检测”）；"
    "中级 3.2 基础网络优化·知识 3.2.1 通信网基础及网优相关知识、3.2.2 无线局域网相关基础知识、"
    "3.2.3 无线局域网网优及软件基础知识（3.2.3 与同号技能“能对无线局域网覆盖进行优化”编号对应）。"
    "口径说明：中级实际要求含 3.2.2，推荐答案对中级只列 3.2.3 为“净新增项”简说，"
    "该口径由人工签核定夺。\n"
    "3. 证据与查重：两处 Chunk 均为必要证据——第 16 页 Chunk 承载初级归属，"
    "第 18 页 Chunk 承载中级归属与 3.2.3 判定；supporting_chunk_ids 保持 "
    "{48ecc091e26caaa3ccbd3be5, c10a8b3b89210595f9880fc6} 不变。"
    "查重（57 条候选池，CJK 双字组最近邻）：最近邻 J=0.1447，无高度重复。"
    "残留风险如实记录：两个证据 Chunk 文本各含一个答案词，仅凭阅读证据仍可得答案"
    "（该题型固有“阅读即答案”特征，检索评测量纲不变。）\n"
    "4. 评测口径记录（只记录、不改动代码）：rag_app/operations/evaluation.py 以 _first_match_rank "
    "对 expected 目标列表判分——命中任一目标即为 hit，hit_at_k/mrr 依首个命中名次计，"
    "无“全部相关 Chunk 均召回”指标；若 Gold 用双 Chunk 出题，hit_at_k=1 不得解读为双证据完整召回。\n"
    "5. 推荐修改后的 question：根据《智慧家庭装维工程与管理职业技能等级标准》，"
    "初级基础网络质量检测与中级基础网络优化，对无线局域网知识的要求分别是什么？\n"
    "6. 推荐修改后的 proposed_answer：初级要求无线局域网相关基础知识；"
    "中级要求无线局域网网优及软件基础知识。"
)

CHANGES = {11: {"H": H11, "J": J11}, 16: {"H": H16, "J": J16}}


def disp_units(s: str) -> int:
    """显示宽度估算：ASCII=1，其他（CJK 等）=2。"""
    return sum(1 if ord(ch) < 0x2E80 else 2 for ch in s)


def col_units(ws, col_letter: str) -> float:
    d = ws.column_dimensions.get(col_letter)
    return float(d.width) if (d is not None and d.width) else 8.43


def needed_height(ws, text: str, col_letter: str) -> float:
    width = max(col_units(ws, col_letter) - 0.6, 4.0)
    lines = 0
    for seg in str(text).split("\n"):
        if not seg:
            lines += 1
            continue
        lines += max(1, math.ceil(disp_units(seg) / width))
    return lines * 14.4 + 6.0


shutil.copyfile(SRC, DST)
wb = openpyxl.load_workbook(DST)
ws = wb.active
old_heights = {r: ws.row_dimensions[r].height for r in CHANGES}
old_cells = {r: {"H": ws.cell(row=r, column=8).value, "J": ws.cell(row=r, column=10).value}
             for r in CHANGES}

for r, ch in CHANGES.items():
    for col, text in ch.items():
        cell = ws.cell(row=r, column=8 if col == "H" else 10)
        cell.value = text
        al = copy.copy(cell.alignment)
        al.wrapText = True
        if al.vertical is None:
            al.vertical = "center"
        cell.alignment = al
    jh = needed_height(ws, ch["J"], "J")
    hh = needed_height(ws, ch["H"], "H")
    want = max(jh, hh)
    cur = ws.row_dimensions[r].height
    if cur is None or cur < want:
        ws.row_dimensions[r].height = round(want, 1)

print(f"saved: {DST}")
print("H/j texts length: H11", len(H11), "J11", len(J11), "H16", len(H16), "J16", len(J16))
for r in CHANGES:
    print(f"row {r}: height {old_heights[r]} -> {ws.row_dimensions[r].height}")
    for col in ("H", "J"):
        old = old_cells[r][col]
        if old == ws.cell(row=r, column=8 if col == 'H' else 10).value:
            print(f"  ⚠ row {r} {col} unchanged!")
wb.save(DST)
print("re-saved final.")
