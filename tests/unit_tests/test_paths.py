from pathlib import Path

import pytest
from langchain_core.tools.base import ToolException

from src.tools.paths import display_path, resolve_workspace_path


def make_config(repo_path: str) -> dict:
    return {"configurable": {"repo_path": repo_path}}


class TestResolveWorkspacePath:
    def test_relative_path_inside_workspace(self, tmp_path):
        (tmp_path / "src").mkdir()
        config = make_config(str(tmp_path))
        result = resolve_workspace_path("src/main.py", config)
        assert result == tmp_path.resolve() / "src" / "main.py"

    def test_path_traversal_raises(self, tmp_path):
        config = make_config(str(tmp_path))
        with pytest.raises(ToolException, match="Access denied"):
            resolve_workspace_path("../../etc/passwd", config)

    def test_absolute_path_inside_workspace(self, tmp_path):
        (tmp_path / "file.py").touch()
        config = make_config(str(tmp_path))
        abs_path = str(tmp_path.resolve() / "file.py")
        result = resolve_workspace_path(abs_path, config)
        assert result == tmp_path.resolve() / "file.py"

    def test_absolute_path_outside_workspace_raises(self, tmp_path):
        config = make_config(str(tmp_path))
        with pytest.raises(ToolException, match="Access denied"):
            resolve_workspace_path("/tmp/evil", config)

    def test_workspace_marker_stripping(self, tmp_path):
        config = make_config(str(tmp_path))
        # Simulate LLM passing full tmp/piper/<thread>/<repo>/src/main.py
        marker_path = f"tmp/piper/abc12345/my_repo/src/main.py"
        result = resolve_workspace_path(marker_path, config)
        assert result == tmp_path.resolve() / "src" / "main.py"

    def test_duplicate_root_prefix_stripped(self, tmp_path):
        config = make_config(str(tmp_path))
        # LLM passes repo_path + relative segment
        prefixed = str(tmp_path.resolve()) + "/src/main.py"
        result = resolve_workspace_path(prefixed, config)
        assert result == tmp_path.resolve() / "src" / "main.py"

    def test_single_filename_resolves(self, tmp_path):
        config = make_config(str(tmp_path))
        result = resolve_workspace_path("README.md", config)
        assert result == tmp_path.resolve() / "README.md"

    def test_dot_dot_in_middle_raises(self, tmp_path):
        (tmp_path / "src").mkdir()
        config = make_config(str(tmp_path))
        with pytest.raises(ToolException, match="Access denied"):
            resolve_workspace_path("src/../../etc/shadow", config)


class TestDisplayPath:
    def test_workspace_marker_returns_inner_path(self):
        path = "tmp/piper/abc12345/my_repo/src/main.py"
        assert display_path(path) == "src/main.py"

    def test_short_path_returns_basename(self):
        assert display_path("main.py") == "main.py"

    def test_two_segment_path_returns_basename(self):
        # display_path returns basename for paths with <= 2 segments
        assert display_path("src/main.py") == "main.py"

    def test_longer_path_returns_last_two_segments(self):
        assert display_path("a/b/c/main.py") == "c/main.py"

    def test_empty_string_unchanged(self):
        assert display_path("") == ""

    def test_workspace_marker_without_enough_segments_falls_through(self):
        # Only 2 segments after marker (thread, main.py) — not enough for repo/path,
        # falls through to last-two-segments logic
        path = "tmp/piper/thread/main.py"
        result = display_path(path)
        assert result == "thread/main.py"
