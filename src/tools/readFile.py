from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langchain_core.tools.base import ToolException

from src.tools.paths import display_path, resolve_workspace_path


@tool
def readFile(
    src: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> str | None:
    """Reads the file present at src.

    Args:
        src: string
    """
    path = resolve_workspace_path(src, config)

    try:
        with open(path, "r") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        raise ToolException(f"Error: File not found at {display_path(src)}")
    except ToolException:
        raise
    except Exception as e:
        raise ToolException(f"Error in reading file: {e}")
