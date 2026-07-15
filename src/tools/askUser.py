from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def ask_user(question: str, options: list[str] | None = None) -> str:
    """Ask the user to choose when multiple strategies exist or a decision is unclear.
    Always call this instead of guessing. Pass 2–4 concrete options when listing strategies.
    """
    payload = {
        "question": question,
        "action": "ask_user",
        "options": options or [],
    }
    answer = interrupt(payload)
    return f"User response: {answer}"
