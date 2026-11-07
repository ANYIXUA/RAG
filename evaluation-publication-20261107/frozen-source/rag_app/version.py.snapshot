"""项目版本和构建信息。"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict


APP_NAME = "rag-installation-assistant"
APP_VERSION = "0.1.0"


@dataclass(frozen=True)
class BuildInfo:
    """发布时用于追踪代码、镜像和知识库版本。"""

    app_name: str
    app_version: str
    build_commit: str | None
    build_time: str | None
    image_tag: str | None
    knowledge_version: str | None


def get_build_info() -> dict[str, str | None]:
    """从环境变量读取构建信息，未配置时保留为空。"""

    return asdict(
        BuildInfo(
            app_name=APP_NAME,
            app_version=os.getenv("RAG_APP_VERSION", APP_VERSION),
            build_commit=os.getenv("RAG_BUILD_COMMIT") or None,
            build_time=os.getenv("RAG_BUILD_TIME") or None,
            image_tag=os.getenv("RAG_IMAGE_TAG") or None,
            knowledge_version=os.getenv("RAG_KNOWLEDGE_VERSION") or None,
        )
    )
