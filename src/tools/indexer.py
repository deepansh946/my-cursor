from langchain.tools import BaseTool
from pathlib import Path
import os

from langchain_community.tools.file_management import (
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
)


def indexer() -> dict[str, str] | None:
    """Returns a dict of all the file locations.

    Args:
        location: string
    """

    srcLocation = os.getcwd() + "/tests"
    fileLocationsIndex: dict[str, str] = {}

    fileLocations = os.listdir(srcLocation)

    nonDotFiles = [file for file in fileLocations if not file.startswith(".")]

    for fileOrFolder in nonDotFiles:
        fullLocation = f"{srcLocation}/{fileOrFolder}"
        if os.path.isfile(fullLocation):
            fileLocationsIndex[fileOrFolder] = fullLocation

    return fileLocationsIndex
