from langchain_core.tools import tool
from langchain_core.tools.base import ToolException
from github import Github
from langchain_core.runnables import RunnableConfig
from pprint import pprint
import subprocess


@tool
def clone_repo(config: RunnableConfig):
    """Clones a GitHub repository.
        Args:
        config: RunnableConfig
    """
    cfg = config.get("configurable")
    if not cfg or not cfg.get("repo_path") or not cfg.get("github_token"):
        raise ToolException("Missing repo_path or github_token")

    repo = cfg.get("repo")
    repo_path = cfg.get("repo_path")
    token = cfg.get("github_token")

    try:
        g = Github(token)
        repo = g.get_repo(repo)
        pprint(repo, "repo")
        result = subprocess.run(
            ["git", "clone", f"https://{token}@github.com/{repo}.git", repo_path],
            check=True,
        )
        pprint(result, "result")
    except Exception as e:
        pprint(e, "error")
        raise ToolException(f"Error in cloning repository: {e}")

    return f"Repository cloned to {repo_path} successfully"

@tool
def commit_changes(message: str, file_path: str, content: str, config: RunnableConfig):
    """Commits changes to a file in a GitHub repository.
            Args:
            message: The commit message
            file_path: The path to the file to commit the changes to
            content: The content to commit to the file
            config: RunnableConfig
        """
    cfg = config.get("configurable")
    if not cfg or not cfg.get("repo_path") or not cfg.get("github_token"):
        raise ToolException("Missing repo_path or github_token")

    repo_path = cfg.get("repo_path")
    token = config.get("github_token")
    if not repo_path or not token:
        raise ToolException("Missing repo_path or github_token")

    if not file_path or not content:
        raise ToolException("Missing file_path or content in commit_changes")

    try:
        g = Github(token)
        repo = g.get_repo(repo_path)
        contents = repo.get_contents(file_path, ref="main")

        repo.update_file(
            path=contents.path,
            message=message,
            content=content,
            sha=contents.sha,
            branch="main"
        )
    except Exception as e:
        raise ToolException(f"Error in committing changes: {e}")
    return f"Changes committed to {file_path} successfully"

@tool
def create_pr(title: str, description: str, config: RunnableConfig):
    """Creates a pull request in a GitHub repository.
        Args:
        title: The title of the pull request
        description: The description of the pull request
        config: RunnableConfig
    """
    cfg = config.get("configurable")
    if not cfg or not cfg.get("repo_path") or not cfg.get("github_token"):
        raise ToolException("Missing repo_path or github_token")

    repo_path = cfg.get("repo_path")
    token = config.get("github_token")

    BASE_BRANCH = 'main'
    NEW_BRANCH = f"piper/{config.get('thread_id')[:8]}"

    if not repo_path or not token:
        raise ToolException("Missing repo_path or github_token")

    try:
        g = Github(token)
        repo = g.get_repo(repo_path)

        pr = repo.create_pull(
            title=title,
            body=description,
            head=NEW_BRANCH,
            base=BASE_BRANCH,
            draft=False
        )
    except Exception as e:
        raise ToolException(f"Error in creating PR: {e}")
    return f"PR created successfully: {pr.html_url}"