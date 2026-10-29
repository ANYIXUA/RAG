from __future__ import annotations

import json
import sys

from .quality import validate_expected_pairs


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    actual = "E203 下游接口超时\nE504 地址校验失败"
    result = validate_expected_pairs(
        actual_text=actual,
        expected_pairs={
            "E203": "地址校验失败",
            "E504": "下游接口超时",
        },
    )
    print(
        json.dumps(
            {
                "actual": actual,
                "accepted": result.accepted,
                "status": result.status,
                "mismatched_keys": result.mismatched_keys,
                "disposition": "review_quarantine",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    # 此固定 badcase 被正确拦截时，Demo 命令成功。
    return 0 if not result.accepted and result.status == "needs_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
