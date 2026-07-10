from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langchain_core.tools.base import ToolException

from src.tools.paths import display_path, resolve_workspace_path


@tool
def writeFile(
    content: str,
    src: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,
) -> bool | str | None:
    """Write the file content at src.

    Args:
        content: string
        src: string
    """
    path = resolve_workspace_path(src, config)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return True
    except ToolException:
        raise
    except Exception as e:
        raise ToolException(f"Error writing file {display_path(src)}: {e}")
