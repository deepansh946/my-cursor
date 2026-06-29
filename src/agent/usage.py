from typing import Annotated

from langchain_core.messages.ai import add_usage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

_usage_store: dict[str, dict] = {}


def _thread_id(config: RunnableConfig) -> str | None:
    cfg = config.get("configurable") or {}
    tid = cfg.get("thread_id")
    return tid if isinstance(tid, str) else None


def set_empty_usage(
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> dict:
    cfg = config.get("configurable") or {}
    tid = _thread_id(config)
    if tid:
        _usage_store[tid] = {}
    usage = _usage_store.get(tid, {})
    cfg["usage_data"] = usage
    return usage


def get_usage(
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> dict:
    tid = _thread_id(config)
    if tid and tid in _usage_store:
        return _usage_store[tid]
    cfg = config.get("configurable") or {}
    return cfg.get("usage_data") or {}


def merge_usage(
    config: Annotated[RunnableConfig, InjectedToolArg],
    usage_data: dict,
) -> None:
    tid = _thread_id(config)
    if not tid:
        return
    current = _usage_store.get(tid)
    merged = add_usage(current, usage_data)
    _usage_store[tid] = merged
    cfg = config.get("configurable") or {}
    cfg["usage_data"] = merged


def clear_usage(thread_id: str) -> None:
    _usage_store.pop(thread_id, None)
