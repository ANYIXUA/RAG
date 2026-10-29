from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="生成离线解析固定样例")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "incident_codes.txt").write_text(
        "# 故障码手册\nE203 地址校验失败，请核对省、市、区。\n"
        "E504 下游接口超时，请稍后重试。\n",
        encoding="utf-8",
    )
    (output / "operations.txt").write_text(
        "# 安全操作\n安全警告：断电后再操作。严禁带电拆卸设备。\n",
        encoding="utf-8",
    )
    try:
        _make_mixed_pdf(output / "mixed_manual.pdf")
    except RuntimeError as exc:
        print(f"跳过 PDF 样例: {exc}")
    print(output)
    return 0


def _make_mixed_pdf(path: Path) -> None:
    try:
        import pymupdf as fitz
    except ModuleNotFoundError:
        try:
            import fitz
        except ModuleNotFoundError as exc:
            raise RuntimeError("未安装 PyMuPDF") from exc

    document = fitz.open()
    document.new_page(width=595, height=842)
    document.new_page(width=595, height=842)
    # PyMuPDF 在增删页面后会使旧 Page 句柄失效；全部建页后重新加载。
    page1 = document.load_page(0)
    page2 = document.load_page(1)
    _insert_common_text(page1, 1)
    _insert_common_text(page2, 2)
    page1.insert_text((50, 110), "Safety steps before the table", fontsize=12)
    _draw_table(
        page1,
        x=50,
        y=620,
        rows=[
            ["Code", "Meaning"],
            ["E203", "Address validation failed"],
            ["E504", "Downstream timeout"],
        ],
    )
    _draw_table(
        page2,
        x=50,
        y=45,
        rows=[
            ["E601", "Inventory shortage"],
            ["E702", "Permission denied"],
        ],
    )
    page2.insert_text((50, 230), "Normal paragraph after the continued table.", fontsize=12)
    document.save(path)
    document.close()


def _insert_common_text(page, page_number: int) -> None:
    page.insert_text((50, 30), "OPS OFFLINE PARSING MANUAL", fontsize=10)
    page.insert_text((270, 820), f"Page {page_number}", fontsize=9)


def _draw_table(page, *, x: float, y: float, rows: list[list[str]]) -> None:
    widths = [100.0, 350.0]
    row_height = 35.0
    x_positions = [x, x + widths[0], x + sum(widths)]
    for row_index in range(len(rows) + 1):
        line_y = y + row_index * row_height
        page.draw_line((x_positions[0], line_y), (x_positions[-1], line_y))
    for line_x in x_positions:
        page.draw_line((line_x, y), (line_x, y + len(rows) * row_height))
    for row_index, row in enumerate(rows):
        baseline = y + row_index * row_height + 22
        page.insert_text((x + 6, baseline), row[0], fontsize=9)
        page.insert_text((x + widths[0] + 6, baseline), row[1], fontsize=9)


if __name__ == "__main__":
    raise SystemExit(main())
