from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PairQualityResult:
    accepted: bool
    status: str
    mismatched_keys: list[str]
    missing_keys: list[str]


def validate_expected_pairs(
    *,
    actual_text: str,
    expected_pairs: dict[str, str],
) -> PairQualityResult:
    """按“字段和值必须在同一行”验收，防止只数关键词造成假通过。"""

    lines = [re.sub(r"\s+", " ", line).strip() for line in actual_text.splitlines()]
    missing: list[str] = []
    mismatched: list[str] = []
    for key, expected_value in expected_pairs.items():
        key_lines = [line for line in lines if key in line]
        if not key_lines:
            missing.append(key)
        elif not any(expected_value in line for line in key_lines):
            mismatched.append(key)
    accepted = not missing and not mismatched
    return PairQualityResult(
        accepted=accepted,
        status="parsed_success" if accepted else "needs_review",
        mismatched_keys=mismatched,
        missing_keys=missing,
    )
