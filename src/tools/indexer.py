from pathlib import Path


def indexer(src: str, filter: str = "*"):
    """Returns the location of the files present in the repo.

    Args:
        src: root directory
        filter: glob pattern like index.js or *.js or **/*.py.
    """
    root = Path(src)

    results = [
        {
            "path": str(p),
            "name": p.name,
            "type": "file" if p.is_file() else "folder",
        }
        for p in root.rglob(filter)
        if not p.name.startswith(".")
    ]

    return results[:20]
