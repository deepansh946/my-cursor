import subprocess
from langchain_core.tools import tool
from langchain_core.tools.base import ToolException


@tool
def terminal(command: str, cwd: str | None) -> str | None:
    """Execute a shell command and return its output.
    Use this to run commands like npm install, pip install, scripts, ls, cat etc

    Args:
        command: The command to execute
        cwd: Working directory to run the command
    """

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=cwd, timeout=60
        )

        output = ""

        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n {result.stderr}"
        if not output:
            output = f"Command exited with code: {result.returncode}"
        return output

    except subprocess.TimeoutExpired:
        raise ToolException("Error: Command timed out after 60 seconds")
    except Exception as e:
        raise ToolException(f"Error executing command: {str(e)}")
