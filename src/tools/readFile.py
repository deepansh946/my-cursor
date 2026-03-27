from langchain.tools import BaseTool
from pathlib import Path
import os


def readFile(src: str) -> str | None:
    """Reads the file present at src.

    Args:
        src: string
    """

    try:
        with open(src, "r") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Error: File not found at {src}"
    except Exception as e:
        return f"Error in reading file: {e}"
