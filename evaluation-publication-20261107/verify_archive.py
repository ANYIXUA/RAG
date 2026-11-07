"""Verify the published evaluation bytes without running any model or service."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((Path(__file__).parent / "sha256_manifest.json").read_text(encoding="utf-8"))
    failures = []
    for name, expected in manifest["files"].items():
        path = root / name
        if not path.is_file():
            failures.append({"path": name, "error": "missing"})
            continue
        if path.stat().st_size != expected["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            failures.append({"path": name, "error": "content mismatch"})
    print(json.dumps({"checked_files": len(manifest["files"]), "failures": failures}, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
