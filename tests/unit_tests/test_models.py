from src.agent.models import (
    COMPLEX_MODEL_ID,
    SIMPLE_MODEL_ID,
    classify_complexity,
    is_allowed_model,
    list_models,
)


class TestClassifyComplexity:
    def test_simple_short_query(self):
        assert classify_complexity("what is this") == SIMPLE_MODEL_ID

    def test_backtick_triggers_complex(self):
        assert classify_complexity("show me `app.js`") == COMPLEX_MODEL_ID

    def test_code_block_triggers_complex(self):
        assert classify_complexity("here is ```python\ncode\n```") == COMPLEX_MODEL_ID

    def test_complex_keyword_implement(self):
        assert classify_complexity("implement auth") == COMPLEX_MODEL_ID

    def test_complex_keyword_fix(self):
        assert classify_complexity("fix the bug in routes") == COMPLEX_MODEL_ID

    def test_complex_keyword_refactor(self):
        assert classify_complexity("refactor the database layer") == COMPLEX_MODEL_ID

    def test_complex_keyword_debug(self):
        assert classify_complexity("debug this error") == COMPLEX_MODEL_ID

    def test_long_message_triggers_complex(self):
        text = "word " * 81
        assert classify_complexity(text) == COMPLEX_MODEL_ID

    def test_has_repo_always_complex(self):
        assert classify_complexity("what is this", has_repo=True) == COMPLEX_MODEL_ID

    def test_has_repo_overrides_short_simple(self):
        assert classify_complexity("hi", has_repo=True) == COMPLEX_MODEL_ID

    def test_empty_string_is_simple(self):
        assert classify_complexity("") == SIMPLE_MODEL_ID

    def test_exactly_80_words_is_simple(self):
        text = "word " * 80
        assert classify_complexity(text.strip()) == SIMPLE_MODEL_ID


class TestIsAllowedModel:
    def test_auto_is_allowed(self):
        assert is_allowed_model("auto") is True

    def test_flash_is_allowed(self):
        assert is_allowed_model("gemini-2.5-flash") is True

    def test_flash_lite_is_allowed(self):
        assert is_allowed_model("gemini-2.5-flash-lite") is True

    def test_unknown_is_rejected(self):
        assert is_allowed_model("gpt-4o") is False

    def test_empty_string_rejected(self):
        assert is_allowed_model("") is False

    def test_partial_match_rejected(self):
        assert is_allowed_model("gemini") is False


class TestListModels:
    def test_non_empty(self):
        assert len(list_models()) > 0

    def test_auto_is_first(self):
        assert list_models()[0]["id"] == "auto"

    def test_all_entries_have_required_keys(self):
        for m in list_models():
            assert "id" in m
            assert "name" in m
            assert "description" in m

    def test_all_ids_are_allowed(self):
        for m in list_models():
            assert is_allowed_model(m["id"])
