import os
from pathlib import Path

from langchain_core.runnables import RunnableConfig

_WORKSPACE_MARKER = "tmp/piper/"


def workspace_root(config: RunnableConfig | None) -> Path:
    cfg = (config or {}).get("configurable") or {}
    return Path(cfg.get("repo_path") or os.getcwd())


def resolve_workspace_path(src: str, config: RunnableConfig | None) -> Path:
    path = Path(src)
    if path.is_absolute():
        return path

    root = workspace_root(config)
    normalized = src.replace("\\", "/")

    # Strip repo_path prefix if LLM passes the full workspace-relative path
    root_str = str(root).replace("\\", "/").rstrip("/") + "/"
    if normalized.startswith(root_str):
        normalized = normalized[len(root_str):]
    elif _WORKSPACE_MARKER in normalized:
        idx = normalized.find(_WORKSPACE_MARKER)
        rest = normalized[idx + len(_WORKSPACE_MARKER):]
        parts = rest.split("/", 2)
        if len(parts) >= 3 and parts[2]:
            normalized = parts[2]

    return root / normalized


def display_path(path: str) -> str:
    if not path:
        return path
    normalized = path.replace("\\", "/")
    idx = normalized.find(_WORKSPACE_MARKER)
    if idx != -1:
        rest = normalized[idx + len(_WORKSPACE_MARKER) :]
        segments = rest.split("/", 2)
        if len(segments) >= 3 and segments[2]:
            return segments[2]
    parts = normalized.split("/")
    return parts[-1] if len(parts) <= 2 else "/".join(parts[-2:])
