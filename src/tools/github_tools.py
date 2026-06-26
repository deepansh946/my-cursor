from pathlib import Path
from typing import Annotated

import subprocess
from github import Github
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langchain_core.tools.base import ToolException


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

    if not repo_name or not repo_path or not token:
        raise ToolException("Missing repo, repo_path, or github_token")

    dest = Path(repo_path)
    if (dest / ".git").exists():
        return f"Repository already cloned at {repo_path}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    branch = _branch_name(thread_id)

    try:
        subprocess.run(
            ["git", "clone", f"https://{token}@github.com/{repo_name}.git", str(dest)],
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

    return f"Repository cloned to {repo_path} on branch {branch}"


@tool
def commit_changes(
    message: str,
    file_path: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Commit local file changes in the cloned repo after writeFile."""
    cfg = _cfg(config)
    repo_path = cfg.get("repo_path")

    if not repo_path:
        raise ToolException("Missing repo_path")
    if not message or not file_path:
        raise ToolException("Missing message or file_path")

    full_path = Path(repo_path) / file_path
    if not full_path.exists():
        raise ToolException(
            f"File not found: {file_path}. Write it first with writeFile."
        )

    try:
        subprocess.run(
            ["git", "add", file_path],
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

    return result.stdout.strip() or f"Changes committed for {file_path}"


@tool
def create_pr(
    title: str,
    description: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Push the piper branch and open a pull request."""
    cfg = _cfg(config)
    repo_name = cfg.get("repo")
    repo_path = cfg.get("repo_path")
    token = cfg.get("github_token")
    thread_id = cfg.get("thread_id", "")

    if not repo_name or not repo_path or not token:
        raise ToolException("Missing repo, repo_path, or github_token")

    head_branch = _branch_name(thread_id)

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
