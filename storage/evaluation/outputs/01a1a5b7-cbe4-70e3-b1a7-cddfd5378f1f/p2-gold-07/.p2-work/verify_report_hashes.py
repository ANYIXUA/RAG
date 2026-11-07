"""Cross-check every SHA-256 printed in the acceptance report against the files on disk."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

G = Path(r"storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-07")
OUTDIR = G.parent
SEARCH = [G, G / ".p2-work", OUTDIR / "p2-gold-05", OUTDIR]

md = (G / "p2_gold_07_validation.md").read_text(encoding="utf-8")
tick = chr(96)
pattern = "\\| " + tick + "([^" + tick + "\n]+)" + tick + " \\| " + tick + "([0-9a-f]{64})" + tick + " \\|"
rows = re.findall(pattern, md)
print("hashes_listed", len(rows))
bad = 0
for name, digest in rows:
    p = next((d / name for d in SEARCH if (d / name).is_file()), None)
    if p is None:
        print("  MISSING", name)
        bad += 1
        continue
    cur = hashlib.sha256(p.read_bytes()).hexdigest()
    if cur != digest:
        print("  STALE", name, digest[:12], "->", cur[:12])
        bad += 1
print("stale_or_missing", bad)
