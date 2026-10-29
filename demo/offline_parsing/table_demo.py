from __future__ import annotations

import argparse
import json

from .table_continuation import (
    extract_table_candidates,
    merge_table_candidates,
    table_to_chunk,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="固定跨页续表启发式 Demo")
    parser.add_argument("pdf")
    args = parser.parse_args()
    tables = merge_table_candidates(extract_table_candidates(args.pdf))
    payload = []
    for table in tables:
        chunk = table_to_chunk(table, source=args.pdf)
        payload.append({
            "block_id": table.table_id,
            "block_type": "table",
            "page_number": table.source_pages[0],
            "bbox": table.bbox_by_page[table.source_pages[0]],
            "section_path": [],
            "table_id": table.table_id,
            "header": table.header,
            "source_pages": table.source_pages,
            "bbox_by_page": table.bbox_by_page,
            "rows": [
                {
                    "values": row.values,
                    "source_page": row.source_page,
                    "table_bbox": row.table_bbox,
                }
                for row in table.rows
            ],
            "chunk": {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "metadata": chunk.metadata,
            },
        })
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
