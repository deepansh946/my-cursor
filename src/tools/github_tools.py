from pathlib import Path
from typing import Annotated

import subprocess
from github import Github
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langchain_core.tools.base import ToolException
from langgraph.types import interrupt


def _cfg(config: RunnableConfig) -> dict:
    return config.get("configurable") or {}


def _branch_name(thread_id: str) -> str:
    return f"piper/{thread_id[:8]}"


@tool
def clone_repo(config: Annotated[RunnableConfig, InjectedToolArg]) -> str:
    """Clone the bound GitHub repo into the thread workspace. Call first on repo-bound threads."""
    cfg = _cfg(config)
    repo_name = cfg.get("repo")
    repo_path = cfg.get("repo_path")
    token = cfg.get("github_token")
    thread_id = cfg.get("thread_id", "")

    if not repo_name or not repo_path:
        raise ToolException("Missing repo or repo_path")

    dest = Path(repo_path)
    if (dest / ".git").exists():
        return f"Repository already cloned at {repo_path}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    branch = _branch_name(thread_id)
    clone_url = (
        f"https://{token}@github.com/{repo_name}.git"
        if token
        else f"https://github.com/{repo_name}.git"
    )

    try:
        subprocess.run(
            ["git", "clone", clone_url, str(dest)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=str(dest),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or str(e)).strip()
        raise ToolException(f"Error cloning repository: {detail}")

    return "Repository cloned successfully."


@tool
def commit_changes(
    message: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Commit all local changes in the cloned repo in a single commit. Only call once when the user explicitly asks to commit or save to git."""
    cfg = _cfg(config)
    repo_path = cfg.get("repo_path")

    if not repo_path:
        raise ToolException("Missing repo_path")
    if not message:
        raise ToolException("Missing message")

    answer = interrupt({
        "question": f"Commit all changes with message: '{message}'?",
        "action": "commit",
        "options": ["yes", "no"],
    })
    if str(answer).lower() not in ("yes", "y", "approve"):
        return "Commit cancelled by user."

    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or str(e)).strip()
        raise ToolException(f"Error committing changes: {detail}")

    return result.stdout.strip() or "Changes committed successfully."


@tool
def create_pr(
    title: str,
    description: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Push the piper branch and open a pull request. Only call when the user explicitly asks to open/create a PR."""
    cfg = _cfg(config)
    repo_name = cfg.get("repo")
    repo_path = cfg.get("repo_path")
    token = cfg.get("github_token")
    thread_id = cfg.get("thread_id", "")

    if not repo_name or not repo_path:
        raise ToolException("Missing repo or repo_path")
    if not token:
        raise ToolException(
            "GitHub sign-in required to create a pull request. "
            "Sign in at /login to connect your GitHub account."
        )

    head_branch = _branch_name(thread_id)

    answer = interrupt({
        "question": f"Push branch and open PR '{title}'?",
        "action": "create_pr",
        "options": ["yes", "no"],
    })
    if str(answer).lower() not in ("yes", "y", "approve"):
        return "PR creation cancelled by user."

    try:
        subprocess.run(
            ["git", "push", "-u", "origin", head_branch],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        pr = repo.create_pull(
            title=title,
            body=description,
            head=head_branch,
            base=repo.default_branch,
        )
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or str(e)).strip()
        raise ToolException(f"Error pushing branch: {detail}")
    except Exception as e:
        raise ToolException(f"Error creating PR: {e}")

    return f"PR created successfully: {pr.html_url}"
