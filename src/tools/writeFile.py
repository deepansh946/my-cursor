from langchain_core.tools import tool
from langchain_core.tools.base import ToolException


@tool
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
        raise ToolException(f"Error: File not found at {src}")
    except Exception as e:
        raise ToolException(f"Error in writing file: {e}")
