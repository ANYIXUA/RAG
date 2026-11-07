"""知识库热更新、版本切换和上传任务管理。"""

from __future__ import annotations

import re
import shutil
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from rag_app.core.config import Settings
from rag_app.ingestion.loaders import SUPPORTED_EXTENSIONS
from rag_app.indexing.offline import OfflineKnowledgeBuilder


UPLOAD_STATUS_UPLOADED = "uploaded"
JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCEEDED = "succeeded"
JOB_STATUS_FAILED = "failed"
VERSION_STATUS_BUILT = "built"
VERSION_STATUS_ACTIVE = "active"
VERSION_STATUS_INACTIVE = "inactive"


@dataclass(frozen=True)
class UploadedKnowledgeDocument:
    """用户热上传的原始知识文件记录。"""

    upload_id: str
    created_at: str
    filename: str
    stored_path: str
    content_type: str | None
    size_bytes: int
    status: str = UPLOAD_STATUS_UPLOADED
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class KnowledgeBuildJob:
    """一次离线知识库构建任务。"""

    job_id: str
    created_at: str
    version: str
    base_collection: str
    collection_name: str
    status: str
    source_dir: str | None = None
    upload_ids: list[str] | None = None
    activate_when_ready: bool = True
    description: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    report: dict[str, Any] | None = None


@dataclass(frozen=True)
class KnowledgeVersion:
    """一个可被在线服务读取的知识库版本。"""

    version: str
    base_collection: str
    collection_name: str
    status: str
    created_at: str
    source_dir: str
    job_id: str | None = None
    activated_at: str | None = None
    previous_version: str | None = None
    description: str | None = None
    documents: int = 0
    chunks: int = 0
    records: int = 0
    manifest_path: str | None = None
    vector_store_path: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ActiveKnowledgeContext:
    """在线查询实际使用的知识库上下文。"""

    settings: Settings
    active_version: KnowledgeVersion | None
    base_collection: str
    collection_name: str

    @property
    def cache_key(self) -> str:
        version = self.active_version.version if self.active_version else "base"
        return f"{self.base_collection}:{self.collection_name}:{version}"


class KnowledgeLifecycleStore(Protocol):
    """知识生命周期元数据存储接口。"""

    def save_upload(
        self,
        upload: UploadedKnowledgeDocument,
    ) -> UploadedKnowledgeDocument:
        ...

    def get_upload(self, upload_id: str) -> UploadedKnowledgeDocument | None:
        ...

    def list_uploads(self, limit: int = 50) -> list[UploadedKnowledgeDocument]:
        ...

    def save_job(self, job: KnowledgeBuildJob) -> KnowledgeBuildJob:
        ...

    def get_job(self, job_id: str) -> KnowledgeBuildJob | None:
        ...

    def list_jobs(self, limit: int = 50) -> list[KnowledgeBuildJob]:
        ...

    def save_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        ...

    def get_version(self, version: str) -> KnowledgeVersion | None:
        ...

    def list_versions(self, limit: int = 50) -> list[KnowledgeVersion]:
        ...

    def get_active_version(self, base_collection: str) -> KnowledgeVersion | None:
        ...

    def activate_version(
        self,
        base_collection: str,
        version: str,
    ) -> KnowledgeVersion:
        ...


class PostgresKnowledgeLifecycleStore:
    """用 PostgreSQL 保存知识版本元数据，适合多实例服务共享状态。"""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._ensure_schema()

    def save_upload(
        self,
        upload: UploadedKnowledgeDocument,
    ) -> UploadedKnowledgeDocument:
        psycopg, _, jsonb = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO knowledge_uploads (
                        upload_id, created_at, filename, stored_path, content_type,
                        size_bytes, status, metadata_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (upload_id) DO UPDATE SET
                        created_at = EXCLUDED.created_at,
                        filename = EXCLUDED.filename,
                        stored_path = EXCLUDED.stored_path,
                        content_type = EXCLUDED.content_type,
                        size_bytes = EXCLUDED.size_bytes,
                        status = EXCLUDED.status,
                        metadata_json = EXCLUDED.metadata_json
                    """,
                    (
                        upload.upload_id,
                        upload.created_at,
                        upload.filename,
                        upload.stored_path,
                        upload.content_type,
                        upload.size_bytes,
                        upload.status,
                        jsonb(upload.metadata or {}),
                    ),
                )
        return upload

    def get_upload(self, upload_id: str) -> UploadedKnowledgeDocument | None:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge_uploads WHERE upload_id = %s",
                    (upload_id,),
                )
                row = cursor.fetchone()
        return _upload_from_postgres(row) if row else None

    def list_uploads(self, limit: int = 50) -> list[UploadedKnowledgeDocument]:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge_uploads ORDER BY created_at DESC LIMIT %s",
                    (max(limit, 0),),
                )
                rows = cursor.fetchall()
        return [_upload_from_postgres(row) for row in rows]

    def save_job(self, job: KnowledgeBuildJob) -> KnowledgeBuildJob:
        psycopg, _, jsonb = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO knowledge_build_jobs (
                        job_id, created_at, version, base_collection, collection_name,
                        status, source_dir, upload_ids_json, activate_when_ready,
                        description, started_at, finished_at, error, report_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (job_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        source_dir = EXCLUDED.source_dir,
                        upload_ids_json = EXCLUDED.upload_ids_json,
                        activate_when_ready = EXCLUDED.activate_when_ready,
                        description = EXCLUDED.description,
                        started_at = EXCLUDED.started_at,
                        finished_at = EXCLUDED.finished_at,
                        error = EXCLUDED.error,
                        report_json = EXCLUDED.report_json
                    """,
                    (
                        job.job_id,
                        job.created_at,
                        job.version,
                        job.base_collection,
                        job.collection_name,
                        job.status,
                        job.source_dir,
                        jsonb(job.upload_ids or []),
                        job.activate_when_ready,
                        job.description,
                        job.started_at,
                        job.finished_at,
                        job.error,
                        jsonb(job.report or {}),
                    ),
                )
        return job

    def get_job(self, job_id: str) -> KnowledgeBuildJob | None:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge_build_jobs WHERE job_id = %s",
                    (job_id,),
                )
                row = cursor.fetchone()
        return _job_from_postgres(row) if row else None

    def list_jobs(self, limit: int = 50) -> list[KnowledgeBuildJob]:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge_build_jobs ORDER BY created_at DESC LIMIT %s",
                    (max(limit, 0),),
                )
                rows = cursor.fetchall()
        return [_job_from_postgres(row) for row in rows]

    def save_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        psycopg, _, jsonb = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO knowledge_versions (
                        version, base_collection, collection_name, status, created_at,
                        source_dir, job_id, activated_at, previous_version, description,
                        documents, chunks, records, manifest_path, vector_store_path,
                        metadata_json
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (version) DO UPDATE SET
                        status = EXCLUDED.status,
                        activated_at = EXCLUDED.activated_at,
                        previous_version = EXCLUDED.previous_version,
                        description = EXCLUDED.description,
                        documents = EXCLUDED.documents,
                        chunks = EXCLUDED.chunks,
                        records = EXCLUDED.records,
                        manifest_path = EXCLUDED.manifest_path,
                        vector_store_path = EXCLUDED.vector_store_path,
                        metadata_json = EXCLUDED.metadata_json
                    """,
                    (
                        version.version,
                        version.base_collection,
                        version.collection_name,
                        version.status,
                        version.created_at,
                        version.source_dir,
                        version.job_id,
                        version.activated_at,
                        version.previous_version,
                        version.description,
                        version.documents,
                        version.chunks,
                        version.records,
                        version.manifest_path,
                        version.vector_store_path,
                        jsonb(version.metadata or {}),
                    ),
                )
        return version

    def get_version(self, version: str) -> KnowledgeVersion | None:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge_versions WHERE version = %s",
                    (version,),
                )
                row = cursor.fetchone()
        return _version_from_postgres(row) if row else None

    def list_versions(self, limit: int = 50) -> list[KnowledgeVersion]:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge_versions ORDER BY created_at DESC LIMIT %s",
                    (max(limit, 0),),
                )
                rows = cursor.fetchall()
        return [_version_from_postgres(row) for row in rows]

    def get_active_version(self, base_collection: str) -> KnowledgeVersion | None:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT v.*
                    FROM knowledge_active_versions a
                    JOIN knowledge_versions v ON v.version = a.version
                    WHERE a.base_collection = %s
                    """,
                    (base_collection,),
                )
                row = cursor.fetchone()
        return _version_from_postgres(row) if row else None

    def activate_version(
        self,
        base_collection: str,
        version: str,
    ) -> KnowledgeVersion:
        psycopg, dict_row, _ = _import_psycopg()
        now = utc_now()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                # PostgreSQL 版本切换放在同一个事务里，保证 active 指针和版本状态一致。
                cursor.execute(
                    "SELECT version FROM knowledge_active_versions WHERE base_collection = %s",
                    (base_collection,),
                )
                active_row = cursor.fetchone()
                previous_version = active_row["version"] if active_row else None
                cursor.execute(
                    """
                    UPDATE knowledge_versions
                    SET status = %s
                    WHERE base_collection = %s AND status = %s AND version <> %s
                    """,
                    (
                        VERSION_STATUS_INACTIVE,
                        base_collection,
                        VERSION_STATUS_ACTIVE,
                        version,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE knowledge_versions
                    SET status = %s,
                        activated_at = %s,
                        previous_version = COALESCE(previous_version, %s)
                    WHERE version = %s
                    RETURNING *
                    """,
                    (
                        VERSION_STATUS_ACTIVE,
                        now,
                        previous_version,
                        version,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError(f"知识版本不存在：{version}")
                cursor.execute(
                    """
                    INSERT INTO knowledge_active_versions (
                        base_collection, version, updated_at
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT (base_collection) DO UPDATE SET
                        version = EXCLUDED.version,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (base_collection, version, now),
                )
        return _version_from_postgres(row)

    def _ensure_schema(self) -> None:
        psycopg, _, _ = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_uploads (
                        upload_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        stored_path TEXT NOT NULL,
                        content_type TEXT,
                        size_bytes INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        metadata_json JSONB NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_build_jobs (
                        job_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        version TEXT NOT NULL,
                        base_collection TEXT NOT NULL,
                        collection_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        source_dir TEXT,
                        upload_ids_json JSONB NOT NULL,
                        activate_when_ready BOOLEAN NOT NULL,
                        description TEXT,
                        started_at TEXT,
                        finished_at TEXT,
                        error TEXT,
                        report_json JSONB NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_versions (
                        version TEXT PRIMARY KEY,
                        base_collection TEXT NOT NULL,
                        collection_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        source_dir TEXT NOT NULL,
                        job_id TEXT,
                        activated_at TEXT,
                        previous_version TEXT,
                        description TEXT,
                        documents INTEGER NOT NULL,
                        chunks INTEGER NOT NULL,
                        records INTEGER NOT NULL,
                        manifest_path TEXT,
                        vector_store_path TEXT,
                        metadata_json JSONB NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_active_versions (
                        base_collection TEXT PRIMARY KEY,
                        version TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_knowledge_versions_base ON knowledge_versions(base_collection)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_knowledge_jobs_status ON knowledge_build_jobs(status)"
                )


def create_knowledge_lifecycle_store(settings: Settings) -> KnowledgeLifecycleStore:
    """根据当前存储配置创建知识生命周期元数据存储。"""

    if settings.ops_store_provider == "postgresql":
        assert settings.ops_postgres_dsn is not None
        return PostgresKnowledgeLifecycleStore(settings.ops_postgres_dsn)
    raise ValueError(f"Unsupported knowledge lifecycle store: {settings.ops_store_provider}")


def save_uploaded_text(
    settings: Settings,
    filename: str,
    content: str,
    *,
    content_type: str | None = "text/markdown",
    metadata: dict[str, Any] | None = None,
) -> UploadedKnowledgeDocument:
    """保存一次文本热上传，并记录到生命周期存储。"""

    safe_name = _safe_filename(filename)
    if Path(safe_name).suffix == "":
        safe_name = f"{safe_name}.md"
    if Path(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"暂不支持的知识文件类型：{Path(safe_name).suffix}")

    upload_id = uuid4().hex
    upload_dir = settings.knowledge_upload_dir
    assert upload_dir is not None
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{upload_id}_{safe_name}"
    actual_content = _with_upload_front_matter(content, metadata or {}, upload_id)
    stored_path.write_text(actual_content, encoding="utf-8")

    upload = UploadedKnowledgeDocument(
        upload_id=upload_id,
        created_at=utc_now(),
        filename=safe_name,
        stored_path=str(stored_path),
        content_type=content_type,
        size_bytes=len(actual_content.encode("utf-8")),
        metadata=metadata or {},
    )
    return create_knowledge_lifecycle_store(settings).save_upload(upload)


def create_knowledge_build_job(
    settings: Settings,
    *,
    source_dir: Path | None = None,
    upload_ids: list[str] | None = None,
    activate_when_ready: bool = True,
    description: str | None = None,
) -> KnowledgeBuildJob:
    """创建一个待执行的知识库构建任务。"""

    version = _new_version_id()
    collection_name = collection_name_for_version(settings.collection_name, version)
    job = KnowledgeBuildJob(
        job_id=uuid4().hex,
        created_at=utc_now(),
        version=version,
        base_collection=settings.collection_name,
        collection_name=collection_name,
        status=JOB_STATUS_QUEUED,
        source_dir=str(source_dir) if source_dir else None,
        upload_ids=upload_ids or [],
        activate_when_ready=activate_when_ready,
        description=description,
    )
    return create_knowledge_lifecycle_store(settings).save_job(job)


def run_knowledge_build_job(
    settings: Settings,
    job_id: str,
) -> KnowledgeBuildJob:
    """执行离线构建任务，成功后可原子切换为 active 版本。"""

    store = create_knowledge_lifecycle_store(settings)
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"知识构建任务不存在：{job_id}")
    running = replace(
        job,
        status=JOB_STATUS_RUNNING,
        started_at=utc_now(),
        error=None,
    )
    store.save_job(running)

    try:
        # 构建源目录可能来自显式 source_dir，也可能是“当前 data + 热上传文件”的合成目录。
        build_source_dir = _prepare_build_source_dir(settings, store, running)
        # 新版本写入独立 collection，不覆盖当前线上 active collection。
        version_settings = settings_for_collection(settings, running.collection_name)
        report = OfflineKnowledgeBuilder(version_settings).refresh(
            source_dir=build_source_dir,
            reset=True,
            force=True,
        )
        version = KnowledgeVersion(
            version=running.version,
            base_collection=running.base_collection,
            collection_name=running.collection_name,
            status=VERSION_STATUS_BUILT,
            created_at=utc_now(),
            source_dir=str(build_source_dir),
            job_id=running.job_id,
            description=running.description,
            documents=report.documents_seen,
            chunks=report.chunks_embedded,
            records=report.stored_records,
            manifest_path=report.manifest_path,
            vector_store_path=report.vector_store_path,
            metadata={
                "documents_changed": report.documents_changed,
                "documents_skipped": report.documents_skipped,
                "documents_failed": report.documents_failed,
                "documents_skipped_by_policy": report.documents_skipped_by_policy,
            },
        )
        store.save_version(version)
        if running.activate_when_ready:
            # 构建成功后才切 active 指针，失败任务不会影响当前线上版本。
            version = store.activate_version(running.base_collection, version.version)
        succeeded = replace(
            running,
            status=JOB_STATUS_SUCCEEDED,
            source_dir=str(build_source_dir),
            finished_at=utc_now(),
            report=asdict(report),
        )
        store.save_job(succeeded)
        return succeeded
    except Exception as exc:
        failed = replace(
            running,
            status=JOB_STATUS_FAILED,
            finished_at=utc_now(),
            error=str(exc),
        )
        store.save_job(failed)
        return failed


def get_active_knowledge_context(settings: Settings) -> ActiveKnowledgeContext:
    """返回在线查询应该读取的知识库版本。"""

    # 如果没有激活过版本，就回退到 base collection；否则读取 active 指针指向的 collection。
    active_version = create_knowledge_lifecycle_store(settings).get_active_version(
        settings.collection_name
    )
    if active_version is None:
        return ActiveKnowledgeContext(
            settings=settings,
            active_version=None,
            base_collection=settings.collection_name,
            collection_name=settings.collection_name,
        )
    active_settings = settings_for_collection(settings, active_version.collection_name)
    return ActiveKnowledgeContext(
        settings=active_settings,
        active_version=active_version,
        base_collection=settings.collection_name,
        collection_name=active_version.collection_name,
    )


def settings_for_collection(settings: Settings, collection_name: str) -> Settings:
    """派生一个只用于指定知识库 collection 的配置。"""

    return replace(
        settings,
        collection_name=collection_name,
    )


def collection_name_for_version(base_collection: str, version: str) -> str:
    """生成符合 PostgreSQL 标识习惯的版本化 collection 名称。"""

    raw = f"{base_collection}_{version}"
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized or normalized[0].isdigit():
        normalized = f"kb_{normalized}"
    return normalized[:120]


def utc_now() -> str:
    """返回 UTC ISO 时间。"""

    return datetime.now(timezone.utc).isoformat()


def _new_version_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"kb_{stamp}_{uuid4().hex[:8]}"


def _prepare_build_source_dir(
    settings: Settings,
    store: KnowledgeLifecycleStore,
    job: KnowledgeBuildJob,
) -> Path:
    explicit_source = Path(job.source_dir) if job.source_dir else None
    if explicit_source is not None:
        return explicit_source

    # 自动构建时创建隔离目录，复制当前知识目录和上传文件，保证一次 job 的输入可追溯。
    build_root = settings.knowledge_build_dir
    assert build_root is not None
    build_dir = (build_root / job.version).resolve()
    _reset_build_dir(build_root, build_dir)
    _copy_supported_tree(settings.data_dir, build_dir)

    upload_ids = set(job.upload_ids or [])
    uploads = (
        [upload for upload in store.list_uploads(limit=10000) if upload.upload_id in upload_ids]
        if upload_ids
        else store.list_uploads(limit=10000)
    )
    upload_target = build_dir / "uploads"
    upload_target.mkdir(parents=True, exist_ok=True)
    for upload in uploads:
        if upload.status != UPLOAD_STATUS_UPLOADED:
            continue
        source = Path(upload.stored_path)
        if not source.exists():
            continue
        shutil.copy2(source, upload_target / upload.filename)
    return build_dir


def _reset_build_dir(build_root: Path, build_dir: Path) -> None:
    build_root = build_root.resolve()
    build_dir = build_dir.resolve()
    try:
        build_dir.relative_to(build_root)
    except ValueError as exc:
        raise ValueError("构建目录必须位于 RAG_KNOWLEDGE_BUILD_DIR 内") from exc
    # 递归删除前先校验 build_dir 位于 build_root 下，避免误删外部目录。
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)


def _copy_supported_tree(source_dir: Path, target_dir: Path) -> None:
    if not source_dir.exists():
        return
    for source in source_dir.rglob("*"):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        target = target_dir / source.relative_to(source_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _safe_filename(filename: str) -> str:
    name = Path(filename.strip()).name
    if not name:
        raise ValueError("filename 不能为空")
    return re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]", "_", name)


def _with_upload_front_matter(
    content: str,
    metadata: dict[str, Any],
    upload_id: str,
) -> str:
    if content.replace("\r\n", "\n").startswith("---\n"):
        return content
    front_matter = {
        "knowledge_status": "approved",
        "source_type": "manual_upload",
        "upload_id": upload_id,
        **{
            key: value
            for key, value in metadata.items()
            if value not in (None, "", [], {})
        },
    }
    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {_front_matter_value(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n" + content


def _front_matter_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ",".join(str(item) for item in value if str(item).strip())
    return str(value)


def _upload_from_postgres(row: dict[str, Any]) -> UploadedKnowledgeDocument:
    return UploadedKnowledgeDocument(
        upload_id=row["upload_id"],
        created_at=row["created_at"],
        filename=row["filename"],
        stored_path=row["stored_path"],
        content_type=row["content_type"],
        size_bytes=row["size_bytes"],
        status=row["status"],
        metadata=dict(row.get("metadata_json") or {}),
    )


def _job_from_postgres(row: dict[str, Any]) -> KnowledgeBuildJob:
    return KnowledgeBuildJob(
        job_id=row["job_id"],
        created_at=row["created_at"],
        version=row["version"],
        base_collection=row["base_collection"],
        collection_name=row["collection_name"],
        status=row["status"],
        source_dir=row["source_dir"],
        upload_ids=list(row.get("upload_ids_json") or []),
        activate_when_ready=bool(row["activate_when_ready"]),
        description=row["description"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        error=row["error"],
        report=dict(row.get("report_json") or {}),
    )


def _version_from_postgres(row: dict[str, Any]) -> KnowledgeVersion:
    return KnowledgeVersion(
        version=row["version"],
        base_collection=row["base_collection"],
        collection_name=row["collection_name"],
        status=row["status"],
        created_at=row["created_at"],
        source_dir=row["source_dir"],
        job_id=row["job_id"],
        activated_at=row["activated_at"],
        previous_version=row["previous_version"],
        description=row["description"],
        documents=row["documents"],
        chunks=row["chunks"],
        records=row["records"],
        manifest_path=row["manifest_path"],
        vector_store_path=row["vector_store_path"],
        metadata=dict(row.get("metadata_json") or {}),
    )


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL 知识版本存储需要安装 psycopg：pip install -e \".[pgsql]\""
        ) from exc
    return psycopg, dict_row, Jsonb
