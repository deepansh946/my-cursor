from pathlib import Path


def indexer(src: str, filter: str = "*"):
    """Returns the location of the files present in the repo.

    Args:
        src: root directory
        filter: glob pattern like index.js or *.js or **/*.py.
    """
    root = Path(src)

    if filter == "*":
        raise ValueError("Filter too broad, use something like *.js")

    if not any(x in filter for x in ["*", "/"]):
        filter = f"*{filter}"

    results = [
        {
            "path": str(p),
            "name": p.name,
            "type": "file",
        }
        for p in root.rglob(filter)
        if p.is_file() and not p.name.startswith(".")
    ]

    if not results:
        return [{"error": f"No files found for filter: {filter}"}]

    results.sort(key=lambda x: x["path"])

    return results[:20]
