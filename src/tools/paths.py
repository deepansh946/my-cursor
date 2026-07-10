import os
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langchain_core.tools.base import ToolException

_WORKSPACE_MARKER = "tmp/piper/"


def workspace_root(config: RunnableConfig | None) -> Path:
    cfg = (config or {}).get("configurable") or {}
    return Path(cfg.get("repo_path") or os.getcwd())


def resolve_workspace_path(src: str, config: RunnableConfig | None) -> Path:
    root = workspace_root(config).resolve()
    path = Path(src)
    normalized = src.replace("\\", "/")

    if path.is_absolute():
        # Strip absolute prefix if it points inside the workspace; else reject
        root_str = str(root).replace("\\", "/").rstrip("/") + "/"
        if normalized.startswith(root_str):
            normalized = normalized[len(root_str) :]
        else:
            raise ToolException("Access denied: path outside workspace")
    else:
        root_str = str(root).replace("\\", "/").rstrip("/") + "/"
        if normalized.startswith(root_str):
            normalized = normalized[len(root_str) :]
        elif _WORKSPACE_MARKER in normalized:
            idx = normalized.find(_WORKSPACE_MARKER)
            rest = normalized[idx + len(_WORKSPACE_MARKER) :]
            parts = rest.split("/", 2)
            if len(parts) >= 3 and parts[2]:
                normalized = parts[2]

    resolved = (root / normalized).resolve()
    if not resolved.is_relative_to(root):
        raise ToolException("Access denied: path outside workspace")
    return resolved


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
