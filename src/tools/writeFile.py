from langchain.tools import BaseTool
from pathlib import Path
import os


def writeFile(content: str, src: str) -> bool | str | None:
    """Write the file content at src.

    Args:
        content: string
        src: string
    """

    try:
        with open(src, "w") as f:
            f.write(content)
        return True
    except FileNotFoundError:
        return f"Error: File not found at {src}"
    except Exception as e:
        return f"Error in writing file: {e}"
