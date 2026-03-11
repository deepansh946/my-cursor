from langchain.tools import BaseTool
from pathlib import Path
from typing import Optional
from langchain_community.tools.file_management import (
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
)


class ReadAndWriteTool(BaseTool):
    name: str = "read_and_write_tool"
    description: str = """
    Execute file system commands.
    Supported commands:
    - read_file
    - write_file
    - list_dir
    """
    root: Path = Path.cwd()
    read_tool: ReadFileTool | None = None
    write_tool: WriteFileTool | None = None
    list_tool: ListDirectoryTool | None = None

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()

        object.__setattr__(self, "root", Path(root_dir or Path.cwd()))

        object.__setattr__(self, "read_tool", ReadFileTool(root_dir=str(self.root)))
        object.__setattr__(self, "write_tool", WriteFileTool(root_dir=str(self.root)))
        object.__setattr__(
            self, "list_tool", ListDirectoryTool(root_dir=str(self.root))
        )

    def sanitize_path(self, path: str):
        path = path.lstrip("/")
        resolved = (self.root / path).resolve()

        if not str(resolved).startswith(str(self.root)):
            raise ValueError("Path escapes project root")

        return str(resolved.relative_to(self.root))

    def _run(
        self,
        command: str,
        path: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs,
    ):
        print("TOOL CALL:", command, path, content, kwargs)
        if path:
            path = self.sanitize_path(path)

        if command == "read_file":
            return self.read_tool.run({"file_path": "./" + path})

        if command == "write_file":
            return self.write_tool.run({"file_path": path, "text": content})

        if command == "list_dir":
            return self.list_tool.run({"dir_path": path or "."})

        return "Unknown command"
