from pathlib import Path
from langchain_core.tools import tool
from langchain_core.tools.base import ToolException


def load_gitignore_patterns(root: Path) -> list[str]:
    """Load patterns from all .gitignore files in the repo."""
    patterns = []
    for gitignore in root.rglob(".gitignore"):
        try:
            with open(gitignore) as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass
    return patterns


def is_ignored(path: Path, root: Path, patterns: list[str]) -> bool:
    """Check if a path matches any gitignore pattern."""
    try:
        import fnmatch

        rel = path.relative_to(root)
        parts = rel.parts  # e.g. ('src', 'node_modules', 'lodash', 'index.js')

        for pattern in patterns:
            # Match against full relative path
            if fnmatch.fnmatch(str(rel), pattern):
                return True
            # Match against any part of the path (e.g. node_modules anywhere)
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
            # Match against filename only
            if fnmatch.fnmatch(path.name, pattern):
                return True

        return False
    except ValueError:
        return False


@tool
def indexer(
    src: str = ".",
    filter: str = "*",
):
    """Returns the location of the files present in the repo, respecting .gitignore.
    Args:
        src: root directory
        filter: glob pattern like index.js or *.js or **/*.py.
    """
    root = Path(src)

    if filter == "*":
        raise ValueError("Filter too broad, use something like *.js")

    # Always ignored regardless of .gitignore
    ALWAYS_IGNORE = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "coverage",
    }

    try:
        if not any(x in filter for x in ["*", "/"]):
            filter = f"*{filter}"

        gitignore_patterns = load_gitignore_patterns(root)

        results = [
            {
                "path": str(p),
                "name": p.name,
                "type": "file",
            }
            for p in root.rglob(filter)
            if p.is_file()
            # Skip hidden directories
            and not any(part.startswith(".") for part in p.parts)
            # Skip always-ignored directories
            and not any(part in ALWAYS_IGNORE for part in p.parts)
            # Skip gitignore patterns
            and not is_ignored(p, root, gitignore_patterns)
        ]

        if not results:
            return [{"error": f"No files found for filter: {filter}"}]

        results.sort(key=lambda x: x["path"])
        return results[:20]

    except Exception:
        raise ToolException(
            "File not found. Please verify the filename and try a different filter pattern."
        )
