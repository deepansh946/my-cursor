from langchain_core.tools import tool
from langchain_core.tools.base import ToolException


@tool
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
        raise ToolException(f"Error: File not found at {src}")
    except Exception as e:
        raise ToolException(f"Error in reading file: {e}")
