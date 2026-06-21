"""基于环境变量的运行配置。"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any


_RETRIEVAL_MODES = {"hybrid", "semantic", "keyword", "bm25"}
_EMBEDDING_PROVIDERS = {"openai"}
_LLM_PROVIDERS = {"openai"}
_RERANK_PROVIDERS = {"none", "off", "disabled", "cross-encoder"}
_RERANK_TRIGGERS = {"always", "auto"}
_OPS_STORE_PROVIDERS = {"postgresql", "postgres", "pgsql"}
_VECTOR_STORE_PROVIDERS = {"postgresql", "postgres", "pgsql", "pgvector"}
_CONFIG_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")
_CONFIG_SKIP_FILENAMES = {"evaluation.json"}
_CONFIG_SECTION_KEYS = {
    "api",
    "knowledge",
    "model",
    "retrieval",
    "runtime",
    "settings",
    "storage",
}
_CONFIG_ALIAS_KEYS = {
    "keyword_weight": "bm25_weight",
}
_INT_CONFIG_FIELDS = {
    "chunk_size",
    "chunk_overlap",
    "top_k",
    "embedding_dimension",
    "embedding_batch_size",
    "embedding_max_retries",
    "generation_context_max_chars",
    "openai_max_retries",
    "retrieval_candidate_k",
    "rerank_candidate_k",
    "query_embedding_cache_size",
}
_OPTIONAL_INT_CONFIG_FIELDS = {"openai_max_tokens"}
_OPTIONAL_FLOAT_CONFIG_FIELDS = {
    "embedding_timeout_seconds",
    "openai_timeout_seconds",
}
_FLOAT_CONFIG_FIELDS = {
    "min_similarity_score",
    "relative_score_threshold",
    "semantic_weight",
    "bm25_weight",
    "rerank_min_intent_confidence",
}
_BOOL_CONFIG_FIELDS = {
    "query_embedding_cache_enabled",
    "query_logging_enabled",
    "require_approval_for_crawled",
    "parse_quality_gate_enabled",
    "order_status_tool_enabled",
}
_PATH_CONFIG_FIELDS = {
    "data_dir",
    "storage_dir",
}
_OPTIONAL_PATH_CONFIG_FIELDS = {
    "knowledge_registry_path",
    "knowledge_upload_dir",
    "knowledge_build_dir",
}
_TUPLE_CONFIG_FIELDS = {
    "rerank_intents",
    "api_cors_origins",
    "default_permission_tags",
    "allowed_parse_quality_statuses",
}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _env_optional_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value is None:
        return default
    if value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _env_optional_float(name: str, default: float | None = None) -> float | None:
    value = os.getenv(name)
    if value is None:
        return default
    if value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean, got {value!r}")


def _env_path(name: str, default: str, base_dir: Path) -> Path:
    value = os.getenv(name, default)
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _config_paths(base_dir: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    config_dir_value = os.getenv("RAG_CONFIG_DIR")
    if config_dir_value is None or config_dir_value.strip() == "":
        config_dir = base_dir / "config"
        if config_dir.exists():
            paths.extend(_config_dir_paths(config_dir))
    else:
        config_dir = _resolve_config_path(config_dir_value, base_dir)
        if not config_dir.exists():
            raise ValueError(f"RAG_CONFIG_DIR does not exist: {config_dir}")
        if not config_dir.is_dir():
            raise ValueError(f"RAG_CONFIG_DIR must be a directory: {config_dir}")
        paths.extend(_config_dir_paths(config_dir))

    config_file_value = os.getenv("RAG_CONFIG_FILE")
    if config_file_value:
        for raw_path in re.split(r"[;,]", config_file_value):
            raw_path = raw_path.strip()
            if not raw_path:
                continue
            config_file = _resolve_config_path(raw_path, base_dir)
            if not config_file.exists():
                raise ValueError(f"RAG_CONFIG_FILE does not exist: {config_file}")
            if not config_file.is_file():
                raise ValueError(f"RAG_CONFIG_FILE must be a file: {config_file}")
            paths.append(config_file)

    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_paths.append(resolved)
    return tuple(unique_paths)


def _config_dir_paths(config_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(config_dir.glob("*.json"), key=lambda item: item.name)
        if path.name not in _CONFIG_SKIP_FILENAMES
        and not path.name.endswith(".example.json")
    ]


def _resolve_config_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path


def _load_config_overrides(
    base_dir: Path,
    allowed_fields: set[str],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    overrides: dict[str, Any] = {}
    sources: list[str] = []
    for path in _config_paths(base_dir):
        payload = _load_config_file(path)
        flattened = _flatten_config(payload)
        for raw_key, raw_value in flattened.items():
            key = _CONFIG_ALIAS_KEYS.get(raw_key, raw_key)
            if key in {"base_dir", "config_sources", "config_fingerprint"}:
                raise ValueError(f"{path}: {raw_key!r} cannot be configured in file")
            if key not in allowed_fields:
                raise ValueError(f"{path}: unsupported config key {raw_key!r}")
            overrides[key] = _coerce_config_value(
                name=key,
                value=raw_value,
                base_dir=base_dir,
                source=path,
            )
        sources.append(str(path))
    return overrides, tuple(sources)


def _load_config_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON config: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: config root must be an object")
    return payload


def _flatten_config(payload: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in payload.items():
        normalized_key = str(key).strip()
        if normalized_key in _CONFIG_SECTION_KEYS and isinstance(value, dict):
            for child_key, child_value in _flatten_config(value).items():
                flattened[child_key] = child_value
        else:
            flattened[normalized_key] = value
    return flattened


def _coerce_config_value(
    *,
    name: str,
    value: Any,
    base_dir: Path,
    source: Path,
) -> Any:
    value = _expand_config_value(value, source)
    if name in _INT_CONFIG_FIELDS:
        return _coerce_int(name, value)
    if name in _OPTIONAL_INT_CONFIG_FIELDS:
        if value is None or value == "":
            return None
        return _coerce_int(name, value)
    if name in _OPTIONAL_FLOAT_CONFIG_FIELDS:
        if value is None or value == "":
            return None
        return _coerce_float(name, value)
    if name in _FLOAT_CONFIG_FIELDS:
        return _coerce_float(name, value)
    if name in _BOOL_CONFIG_FIELDS:
        return _coerce_bool(name, value)
    if name in _PATH_CONFIG_FIELDS:
        return _coerce_path(value, base_dir)
    if name in _OPTIONAL_PATH_CONFIG_FIELDS:
        if value is None or value == "":
            return None
        return _coerce_path(value, base_dir)
    if name in _TUPLE_CONFIG_FIELDS:
        return _coerce_tuple(name, value)
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _expand_config_value(value: Any, source: Path) -> Any:
    if isinstance(value, str):
        def replace_var(match: re.Match[str]) -> str:
            env_name = match.group(1)
            default = match.group(2)
            env_value = os.getenv(env_name)
            if env_value is not None:
                return env_value
            if default is not None:
                return default
            raise ValueError(f"{source}: environment variable {env_name} is required")

        return _CONFIG_ENV_PATTERN.sub(replace_var, value)
    if isinstance(value, list):
        return [_expand_config_value(item, source) for item in value]
    if isinstance(value, dict):
        return {
            key: _expand_config_value(item, source)
            for key, item in value.items()
        }
    return value


def _coerce_int(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _coerce_float(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, got {value!r}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _coerce_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"{name} must be a boolean, got {value!r}")


def _coerce_path(value: Any, base_dir: Path) -> Path:
    path = Path(str(value))
    if not path.is_absolute():
        path = base_dir / path
    return path


def _coerce_tuple(name: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError(f"{name} must be a list or comma-separated string")


@dataclass(frozen=True)
class Settings:
    """RAG 流程的运行参数。"""

    base_dir: Path
    data_dir: Path
    storage_dir: Path
    collection_name: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    embedding_provider: str
    embedding_dimension: int
    llm_provider: str
    openai_api_key: str | None
    openai_chat_model: str
    openai_embedding_model: str
    openai_base_url: str | None = None
    openai_max_tokens: int | None = 800
    openai_timeout_seconds: float | None = 8.0
    openai_max_retries: int = 0
    generation_context_max_chars: int = 3200
    embedding_batch_size: int = 10
    embedding_timeout_seconds: float | None = 3.0
    embedding_max_retries: int = 0
    min_similarity_score: float = 0.05
    relative_score_threshold: float = 0.35
    retrieval_mode: str = "hybrid"
    retrieval_candidate_k: int = 20
    semantic_weight: float = 0.7
    bm25_weight: float = 0.3
    keyword_weight: float = 0.3
    rerank_provider: str = "none"
    rerank_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    rerank_candidate_k: int = 20
    rerank_trigger: str = "always"
    rerank_intents: tuple[str, ...] = (
        "recommend_solution",
        "explain_error",
        "query_rule",
        "similar_case",
        "need_human",
    )
    rerank_min_intent_confidence: float = 0.75
    query_embedding_cache_enabled: bool = True
    query_embedding_cache_size: int = 128
    query_logging_enabled: bool = True
    api_admin_token: str | None = None
    api_cors_origins: tuple[str, ...] = ("*",)
    ops_store_provider: str = "postgresql"
    ops_postgres_dsn: str | None = None
    vector_store_provider: str = "postgresql"
    knowledge_registry_path: Path | None = None
    knowledge_default_status: str = "approved"
    require_approval_for_crawled: bool = True
    knowledge_upload_dir: Path | None = None
    knowledge_build_dir: Path | None = None
    default_tenant_id: str = "default"
    default_permission_tags: tuple[str, ...] = ("public",)
    parse_quality_gate_enabled: bool = True
    allowed_parse_quality_statuses: tuple[str, ...] = (
        "parsed_success",
        "parsed_with_warning",
    )
    order_status_tool_enabled: bool = True
    order_status_postgres_dsn: str | None = None
    config_sources: tuple[str, ...] = ()
    config_fingerprint: str = ""

    def __post_init__(self) -> None:
        """集中校验配置，尽量在启动阶段暴露错误。"""

        object.__setattr__(self, "base_dir", self.base_dir.resolve())
        object.__setattr__(self, "data_dir", self.data_dir.resolve())
        object.__setattr__(self, "storage_dir", self.storage_dir.resolve())

        collection_name = self.collection_name.strip()
        if not collection_name:
            raise ValueError("RAG_COLLECTION_NAME cannot be empty")
        if any(part in collection_name for part in ("/", "\\", "..")):
            raise ValueError(
                "RAG_COLLECTION_NAME cannot contain path separators or '..'"
            )
        object.__setattr__(self, "collection_name", collection_name)

        _require_positive_int("RAG_CHUNK_SIZE", self.chunk_size)
        _require_non_negative_int("RAG_CHUNK_OVERLAP", self.chunk_overlap)
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        _require_positive_int("RAG_TOP_K", self.top_k)
        _require_positive_int("RAG_EMBEDDING_DIMENSION", self.embedding_dimension)
        _require_positive_int("RAG_EMBEDDING_BATCH_SIZE", self.embedding_batch_size)
        if self.embedding_timeout_seconds is not None and self.embedding_timeout_seconds <= 0:
            raise ValueError("RAG_EMBEDDING_TIMEOUT_SECONDS must be greater than 0")
        _require_non_negative_int(
            "RAG_EMBEDDING_MAX_RETRIES",
            self.embedding_max_retries,
        )
        _require_positive_int("RAG_RETRIEVAL_CANDIDATE_K", self.retrieval_candidate_k)
        _require_positive_int("RAG_RERANK_CANDIDATE_K", self.rerank_candidate_k)

        if self.min_similarity_score < -1.0 or self.min_similarity_score > 1.0:
            raise ValueError("RAG_MIN_SIMILARITY_SCORE must be between -1 and 1")
        if not 0.0 <= self.relative_score_threshold <= 1.0:
            raise ValueError("RAG_RELATIVE_SCORE_THRESHOLD must be between 0 and 1")

        if self.semantic_weight < 0:
            raise ValueError("RAG_SEMANTIC_WEIGHT cannot be negative")
        if self.bm25_weight < 0:
            raise ValueError("RAG_BM25_WEIGHT cannot be negative")
        if self.semantic_weight + self.bm25_weight <= 0:
            raise ValueError("RAG_SEMANTIC_WEIGHT and RAG_BM25_WEIGHT cannot both be 0")
        object.__setattr__(self, "keyword_weight", self.bm25_weight)

        retrieval_mode = self.retrieval_mode.strip().lower()
        if retrieval_mode not in _RETRIEVAL_MODES:
            raise ValueError(
                "RAG_RETRIEVAL_MODE must be one of: "
                + ", ".join(sorted(_RETRIEVAL_MODES))
            )
        object.__setattr__(self, "retrieval_mode", retrieval_mode)

        embedding_provider = self.embedding_provider.strip().lower()
        if embedding_provider not in _EMBEDDING_PROVIDERS:
            raise ValueError(
                "RAG_EMBEDDING_PROVIDER must be one of: "
                + ", ".join(sorted(_EMBEDDING_PROVIDERS))
            )
        object.__setattr__(self, "embedding_provider", embedding_provider)
        if embedding_provider == "openai" and not (
            self.openai_api_key and self.openai_api_key.strip()
        ):
            raise ValueError("OPENAI_API_KEY cannot be empty when RAG_EMBEDDING_PROVIDER=openai")

        llm_provider = self.llm_provider.strip().lower()
        if llm_provider not in _LLM_PROVIDERS:
            raise ValueError(
                "RAG_LLM_PROVIDER must be one of: "
                + ", ".join(sorted(_LLM_PROVIDERS))
            )
        object.__setattr__(self, "llm_provider", llm_provider)
        if llm_provider == "openai" and not (
            self.openai_api_key and self.openai_api_key.strip()
        ):
            raise ValueError("OPENAI_API_KEY cannot be empty when RAG_LLM_PROVIDER=openai")

        rerank_provider = self.rerank_provider.strip().lower()
        if rerank_provider not in _RERANK_PROVIDERS:
            raise ValueError(
                "RAG_RERANK_PROVIDER must be one of: "
                + ", ".join(sorted(_RERANK_PROVIDERS))
            )
        object.__setattr__(self, "rerank_provider", rerank_provider)

        if not self.openai_chat_model.strip():
            raise ValueError("OPENAI_CHAT_MODEL cannot be empty")
        if not self.openai_embedding_model.strip():
            raise ValueError("OPENAI_EMBEDDING_MODEL cannot be empty")
        if self.openai_max_tokens is not None:
            _require_positive_int("OPENAI_MAX_TOKENS", self.openai_max_tokens)
        if self.openai_timeout_seconds is not None and self.openai_timeout_seconds <= 0:
            raise ValueError("OPENAI_TIMEOUT_SECONDS must be greater than 0")
        _require_non_negative_int("OPENAI_MAX_RETRIES", self.openai_max_retries)
        _require_positive_int(
            "RAG_GENERATION_CONTEXT_MAX_CHARS",
            self.generation_context_max_chars,
        )
        if self.rerank_provider == "cross-encoder" and not self.rerank_model.strip():
            raise ValueError("RAG_RERANK_MODEL cannot be empty when rerank is enabled")
        rerank_trigger = self.rerank_trigger.strip().lower()
        if rerank_trigger not in _RERANK_TRIGGERS:
            raise ValueError(
                "RAG_RERANK_TRIGGER must be one of: "
                + ", ".join(sorted(_RERANK_TRIGGERS))
            )
        object.__setattr__(self, "rerank_trigger", rerank_trigger)
        if not 0.0 <= self.rerank_min_intent_confidence <= 1.0:
            raise ValueError("RAG_RERANK_MIN_INTENT_CONFIDENCE must be between 0 and 1")
        rerank_intents = tuple(
            intent.strip()
            for intent in self.rerank_intents
            if intent and intent.strip()
        )
        object.__setattr__(self, "rerank_intents", rerank_intents)
        _require_positive_int(
            "RAG_QUERY_EMBEDDING_CACHE_SIZE",
            self.query_embedding_cache_size,
        )

        ops_store_provider = self.ops_store_provider.strip().lower()
        if ops_store_provider not in _OPS_STORE_PROVIDERS:
            raise ValueError(
                "RAG_OPS_STORE_PROVIDER must be one of: "
                + ", ".join(sorted(_OPS_STORE_PROVIDERS))
            )
        if ops_store_provider in {"postgres", "pgsql"}:
            ops_store_provider = "postgresql"
        object.__setattr__(self, "ops_store_provider", ops_store_provider)
        if self.ops_store_provider == "postgresql" and not (
            self.ops_postgres_dsn and self.ops_postgres_dsn.strip()
        ):
            raise ValueError(
                "RAG_OPS_POSTGRES_DSN cannot be empty when RAG_OPS_STORE_PROVIDER=postgresql"
            )
        if self.ops_postgres_dsn is not None:
            object.__setattr__(
                self,
                "ops_postgres_dsn",
                self.ops_postgres_dsn.strip() or None,
            )

        order_status_dsn = self.order_status_postgres_dsn or self.ops_postgres_dsn
        if order_status_dsn is not None:
            order_status_dsn = order_status_dsn.strip() or None
        if self.order_status_tool_enabled and not order_status_dsn:
            raise ValueError(
                "RAG_ORDER_STATUS_POSTGRES_DSN cannot be empty when RAG_ORDER_STATUS_TOOL_ENABLED=true"
            )
        object.__setattr__(self, "order_status_postgres_dsn", order_status_dsn)

        vector_store_provider = self.vector_store_provider.strip().lower()
        if vector_store_provider not in _VECTOR_STORE_PROVIDERS:
            raise ValueError(
                "RAG_VECTOR_STORE_PROVIDER must be one of: "
                + ", ".join(sorted(_VECTOR_STORE_PROVIDERS))
            )
        if vector_store_provider in {"postgres", "pgsql", "pgvector"}:
            vector_store_provider = "postgresql"
        object.__setattr__(self, "vector_store_provider", vector_store_provider)
        if self.vector_store_provider == "postgresql" and not (
            self.ops_postgres_dsn and self.ops_postgres_dsn.strip()
        ):
            raise ValueError(
                "RAG_OPS_POSTGRES_DSN cannot be empty when RAG_VECTOR_STORE_PROVIDER=postgresql"
            )

        if self.api_admin_token is not None:
            admin_token = self.api_admin_token.strip()
            object.__setattr__(self, "api_admin_token", admin_token or None)

        if self.openai_base_url is not None:
            openai_base_url = self.openai_base_url.strip()
            object.__setattr__(
                self,
                "openai_base_url",
                openai_base_url or None,
            )

        if self.knowledge_registry_path is None:
            object.__setattr__(
                self,
                "knowledge_registry_path",
                self.data_dir / "knowledge_registry.json",
            )
        else:
            object.__setattr__(
                self,
                "knowledge_registry_path",
                self.knowledge_registry_path.resolve(),
            )
        knowledge_default_status = self.knowledge_default_status.strip().lower()
        if not knowledge_default_status:
            raise ValueError("RAG_KNOWLEDGE_DEFAULT_STATUS cannot be empty")
        object.__setattr__(
            self,
            "knowledge_default_status",
            knowledge_default_status,
        )

        cors_origins = tuple(
            origin.strip()
            for origin in self.api_cors_origins
            if origin and origin.strip()
        )
        object.__setattr__(self, "api_cors_origins", cors_origins or ("*",))

        if self.knowledge_upload_dir is None:
            object.__setattr__(
                self,
                "knowledge_upload_dir",
                self.storage_dir / "uploads",
            )
        else:
            object.__setattr__(
                self,
                "knowledge_upload_dir",
                self.knowledge_upload_dir.resolve(),
            )
        if self.knowledge_build_dir is None:
            object.__setattr__(
                self,
                "knowledge_build_dir",
                self.storage_dir / "knowledge_builds",
            )
        else:
            object.__setattr__(
                self,
                "knowledge_build_dir",
                self.knowledge_build_dir.resolve(),
            )

        default_tenant_id = self.default_tenant_id.strip() or "default"
        object.__setattr__(self, "default_tenant_id", default_tenant_id)
        default_permission_tags = tuple(
            tag.strip()
            for tag in self.default_permission_tags
            if tag and tag.strip()
        )
        object.__setattr__(
            self,
            "default_permission_tags",
            default_permission_tags or ("public",),
        )
        allowed_parse_quality_statuses = tuple(
            status.strip()
            for status in self.allowed_parse_quality_statuses
            if status and status.strip()
        )
        if not allowed_parse_quality_statuses:
            raise ValueError("RAG_ALLOWED_PARSE_QUALITY_STATUSES cannot be empty")
        object.__setattr__(
            self,
            "allowed_parse_quality_statuses",
            allowed_parse_quality_statuses,
        )
        config_sources = tuple(
            str(Path(source).resolve())
            for source in self.config_sources
            if str(source).strip()
        )
        object.__setattr__(self, "config_sources", config_sources)
        object.__setattr__(self, "config_fingerprint", _settings_fingerprint(self))

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "Settings":
        resolved_base = (base_dir or Path.cwd()).resolve()
        bm25_weight = _env_float(
            "RAG_BM25_WEIGHT",
            _env_float("RAG_KEYWORD_WEIGHT", 0.3),
        )
        kwargs: dict[str, Any] = {
            "base_dir": resolved_base,
            "data_dir": _env_path("RAG_DATA_DIR", "data", resolved_base),
            "storage_dir": _env_path("RAG_STORAGE_DIR", "storage", resolved_base),
            "collection_name": os.getenv("RAG_COLLECTION_NAME", "default"),
            "chunk_size": _env_int("RAG_CHUNK_SIZE", 800),
            "chunk_overlap": _env_int("RAG_CHUNK_OVERLAP", 120),
            "top_k": _env_int("RAG_TOP_K", 4),
            "min_similarity_score": _env_float("RAG_MIN_SIMILARITY_SCORE", 0.05),
            "relative_score_threshold": _env_float(
                "RAG_RELATIVE_SCORE_THRESHOLD",
                0.35,
            ),
            "retrieval_mode": os.getenv("RAG_RETRIEVAL_MODE", "hybrid"),
            "retrieval_candidate_k": _env_int("RAG_RETRIEVAL_CANDIDATE_K", 20),
            "semantic_weight": _env_float("RAG_SEMANTIC_WEIGHT", 0.7),
            "bm25_weight": bm25_weight,
            "keyword_weight": bm25_weight,
            "rerank_provider": os.getenv("RAG_RERANK_PROVIDER", "none"),
            "rerank_model": os.getenv(
                "RAG_RERANK_MODEL",
                "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
            ),
            "rerank_candidate_k": _env_int("RAG_RERANK_CANDIDATE_K", 20),
            "rerank_trigger": os.getenv("RAG_RERANK_TRIGGER", "always"),
            "rerank_intents": _env_list(
                "RAG_RERANK_INTENTS",
                (
                    "recommend_solution",
                    "explain_error",
                    "query_rule",
                    "similar_case",
                    "need_human",
                ),
            ),
            "rerank_min_intent_confidence": _env_float(
                "RAG_RERANK_MIN_INTENT_CONFIDENCE",
                0.75,
            ),
            "query_embedding_cache_enabled": _env_bool(
                "RAG_QUERY_EMBEDDING_CACHE_ENABLED",
                True,
            ),
            "query_embedding_cache_size": _env_int(
                "RAG_QUERY_EMBEDDING_CACHE_SIZE",
                128,
            ),
            "query_logging_enabled": _env_bool("RAG_QUERY_LOGGING_ENABLED", True),
            "api_admin_token": os.getenv("RAG_API_ADMIN_TOKEN") or None,
            "api_cors_origins": _env_list("RAG_API_CORS_ORIGINS", ("*",)),
            "ops_store_provider": os.getenv("RAG_OPS_STORE_PROVIDER", "postgresql"),
            "ops_postgres_dsn": (
                os.getenv("RAG_OPS_POSTGRES_DSN")
                or os.getenv("RAG_OPS_DB_DSN")
                or os.getenv("DATABASE_URL")
                or None
            ),
            "vector_store_provider": os.getenv(
                "RAG_VECTOR_STORE_PROVIDER",
                "postgresql",
            ),
            "knowledge_registry_path": _env_path(
                "RAG_KNOWLEDGE_REGISTRY_PATH",
                "",
                resolved_base,
            )
            if os.getenv("RAG_KNOWLEDGE_REGISTRY_PATH")
            else None,
            "knowledge_default_status": os.getenv(
                "RAG_KNOWLEDGE_DEFAULT_STATUS",
                "approved",
            ),
            "require_approval_for_crawled": _env_bool(
                "RAG_REQUIRE_APPROVAL_FOR_CRAWLED",
                True,
            ),
            "knowledge_upload_dir": _env_path(
                "RAG_KNOWLEDGE_UPLOAD_DIR",
                "",
                resolved_base,
            )
            if os.getenv("RAG_KNOWLEDGE_UPLOAD_DIR")
            else None,
            "knowledge_build_dir": _env_path(
                "RAG_KNOWLEDGE_BUILD_DIR",
                "",
                resolved_base,
            )
            if os.getenv("RAG_KNOWLEDGE_BUILD_DIR")
            else None,
            "default_tenant_id": os.getenv("RAG_DEFAULT_TENANT_ID", "default"),
            "default_permission_tags": _env_list(
                "RAG_DEFAULT_PERMISSION_TAGS",
                ("public",),
            ),
            "parse_quality_gate_enabled": _env_bool(
                "RAG_PARSE_QUALITY_GATE_ENABLED",
                True,
            ),
            "allowed_parse_quality_statuses": _env_list(
                "RAG_ALLOWED_PARSE_QUALITY_STATUSES",
                ("parsed_success", "parsed_with_warning"),
            ),
            "order_status_tool_enabled": _env_bool(
                "RAG_ORDER_STATUS_TOOL_ENABLED",
                True,
            ),
            "order_status_postgres_dsn": (
                os.getenv("RAG_ORDER_STATUS_POSTGRES_DSN")
                or os.getenv("RAG_OPS_POSTGRES_DSN")
                or os.getenv("RAG_OPS_DB_DSN")
                or os.getenv("DATABASE_URL")
                or None
            ),
            "embedding_provider": os.getenv("RAG_EMBEDDING_PROVIDER", "openai"),
            "embedding_dimension": _env_int("RAG_EMBEDDING_DIMENSION", 1024),
            "embedding_batch_size": _env_int("RAG_EMBEDDING_BATCH_SIZE", 10),
            "embedding_timeout_seconds": _env_optional_float(
                "RAG_EMBEDDING_TIMEOUT_SECONDS",
                3.0,
            ),
            "embedding_max_retries": _env_int("RAG_EMBEDDING_MAX_RETRIES", 0),
            "llm_provider": os.getenv("RAG_LLM_PROVIDER", "openai"),
            "openai_api_key": (
                os.getenv("OPENAI_API_KEY")
                or os.getenv("DASHSCOPE_API_KEY")
                or None
            ),
            "openai_base_url": (
                os.getenv("OPENAI_BASE_URL")
                or os.getenv("RAG_OPENAI_BASE_URL")
                or os.getenv("DASHSCOPE_BASE_URL")
                or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            "openai_chat_model": os.getenv("OPENAI_CHAT_MODEL", "qwen-plus"),
            "openai_embedding_model": os.getenv(
                "OPENAI_EMBEDDING_MODEL",
                "text-embedding-v4",
            ),
            "openai_max_tokens": _env_optional_int("OPENAI_MAX_TOKENS", 800),
            "openai_timeout_seconds": _env_optional_float(
                "OPENAI_TIMEOUT_SECONDS",
                8.0,
            ),
            "openai_max_retries": _env_int("OPENAI_MAX_RETRIES", 0),
            "generation_context_max_chars": _env_int(
                "RAG_GENERATION_CONTEXT_MAX_CHARS",
                3200,
            ),
        }
        allowed_fields = {field.name for field in fields(cls) if field.init}
        overrides, sources = _load_config_overrides(resolved_base, allowed_fields)
        kwargs.update(overrides)
        kwargs["config_sources"] = sources
        return cls(**kwargs)

    @property
    def vector_store_location(self) -> str:
        return f"{_redact_dsn(self.ops_postgres_dsn or '')}/{self.collection_name}"

    @property
    def manifest_path(self) -> Path:
        return self.storage_dir / f"{self.collection_name}_manifest.json"

    @property
    def manifest_backup_path(self) -> Path:
        return self.storage_dir / f"{self.collection_name}_manifest.previous.json"

    @property
    def refresh_report_path(self) -> Path:
        return self.storage_dir / f"{self.collection_name}_refresh_report.json"

def _require_positive_int(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")


def _require_non_negative_int(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")


def _redact_dsn(dsn: str) -> str:
    return re.sub(r":([^:@/]+)@", ":***@", dsn)


def _settings_fingerprint(settings: Settings) -> str:
    payload: dict[str, Any] = {}
    for field in fields(settings):
        if field.name == "config_fingerprint":
            continue
        payload[field.name] = _json_safe_value(getattr(settings, field.name))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _json_safe_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value
