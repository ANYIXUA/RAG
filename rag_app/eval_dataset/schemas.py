"""Explicit export scope; deliberately no permissive production ACL defaults."""

from __future__ import annotations

from dataclasses import dataclass


def required_label(value: object, field: str) -> str:
    if (
        not isinstance(value, str) or not value.strip() or value != value.strip()
        or any(ord(char) < 32 for char in value) or "*" in value
    ):
        raise ValueError(f"{field} must be an explicit nonempty string without wildcards/control characters")
    return value


def permission_labels(value: object, field: str = "permission_tags") -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{field} must be a nonempty list of explicit tags")
    return tuple(sorted({required_label(item, field) for item in value}))


@dataclass(frozen=True)
class CorpusScope:
    collection_name: str
    tenant_id: str
    permission_tags: tuple[str, ...]

    def __post_init__(self) -> None:
        required_label(self.collection_name, "collection_name")
        required_label(self.tenant_id, "tenant_id")
        object.__setattr__(self, "permission_tags", permission_labels(self.permission_tags))

    def to_dict(self) -> dict:
        return {
            "collection_name": self.collection_name,
            "tenant_id": self.tenant_id,
            "permission_tags": list(self.permission_tags),
        }

    @classmethod
    def from_dict(cls, payload: object) -> "CorpusScope":
        if not isinstance(payload, dict) or set(payload) != {
            "collection_name", "tenant_id", "permission_tags"
        }:
            raise ValueError("Invalid corpus scope")
        return cls(**payload)
