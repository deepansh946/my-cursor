import pytest

from src.agent.usage import clear_usage, get_usage, merge_usage, set_empty_usage


def make_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


class TestSetEmptyUsage:
    def test_stores_empty_dict(self):
        config = make_config("thread-set-1")
        result = set_empty_usage(config)
        assert result == {}

    def test_resets_existing_usage(self):
        config = make_config("thread-set-2")
        merge_usage(config, {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})
        set_empty_usage(config)
        assert get_usage(config) == {}

    def teardown_method(self):
        for tid in ("thread-set-1", "thread-set-2"):
            clear_usage(tid)


class TestGetUsage:
    def test_returns_empty_for_unknown_thread(self):
        config = make_config("thread-get-unknown")
        assert get_usage(config) == {}

    def test_returns_stored_usage(self):
        config = make_config("thread-get-1")
        set_empty_usage(config)
        merge_usage(config, {"input_tokens": 5, "output_tokens": 3, "total_tokens": 8})
        usage = get_usage(config)
        assert usage.get("input_tokens") == 5

    def teardown_method(self):
        clear_usage("thread-get-1")


class TestMergeUsage:
    def test_accumulates_tokens_across_calls(self):
        config = make_config("thread-merge-1")
        set_empty_usage(config)
        merge_usage(config, {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})
        merge_usage(config, {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30})
        usage = get_usage(config)
        assert usage["input_tokens"] == 30
        assert usage["output_tokens"] == 15
        assert usage["total_tokens"] == 45

    def test_no_thread_id_is_noop(self):
        config = {"configurable": {}}
        merge_usage(config, {"input_tokens": 99, "output_tokens": 99, "total_tokens": 198})

    def teardown_method(self):
        clear_usage("thread-merge-1")


class TestClearUsage:
    def test_removes_thread_entry(self):
        config = make_config("thread-clear-1")
        set_empty_usage(config)
        merge_usage(config, {"input_tokens": 5, "output_tokens": 3, "total_tokens": 8})
        clear_usage("thread-clear-1")
        # Use a fresh config so we don't hit the stale cfg["usage_data"] fallback
        fresh_config = make_config("thread-clear-1")
        assert get_usage(fresh_config) == {}

    def test_clear_nonexistent_is_noop(self):
        clear_usage("thread-does-not-exist")
