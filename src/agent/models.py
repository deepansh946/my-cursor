from langchain.chat_models import init_chat_model

SIMPLE_MODEL_ID = "gemini-2.5-flash-lite"
COMPLEX_MODEL_ID = "gemini-2.5-flash"
DEFAULT_MODEL_ID = "auto"

_COMPLEX_KEYWORDS = {
    "implement",
    "create",
    "build",
    "refactor",
    "fix",
    "write",
    "add",
    "update",
    "delete",
    "debug",
    "migrate",
    "rename",
    "move",
}

LLM_MODELS = [
    {
        "id": "auto",
        "name": "Auto",
        "description": "Routes simple requests to Flash Lite and complex ones to Flash",
    },
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "description": "The latest and greatest model from Google",
    },
    {
        "id": "gemini-2.5-flash-lite",
        "name": "Gemini 2.5 Flash Lite",
        "description": "A lighter version of Gemini 2.5 Flash",
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "description": "A pro version of Gemini 2.5 Flash",
    },
    {
        "id": "gemini-3-flash-preview",
        "name": "Gemini 3 Flash Preview",
        "description": "A preview version of Gemini 3 Flash",
    },
    {
        "id": "gemini-3.1-pro-preview",
        "name": "Gemini 3.1 Pro Preview",
        "description": "A preview version of Gemini 3.1 Pro",
    },
    {
        "id": "gemini-3.1-flash",
        "name": "Gemini 3.1 Flash",
        "description": "A version of Gemini 3.1 Flash",
    },
    {
        "id": "gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "description": "The latest and greatest model from Google",
    },
]

_ALLOWED_IDS = {m["id"] for m in LLM_MODELS}


def classify_complexity(text: str, has_repo: bool = False) -> str:
    if has_repo:
        return COMPLEX_MODEL_ID
    words = text.lower().split()
    if "```" in text or "`" in text:
        return COMPLEX_MODEL_ID
    if any(w in _COMPLEX_KEYWORDS for w in words):
        return COMPLEX_MODEL_ID
    if len(words) > 80:
        return COMPLEX_MODEL_ID
    return SIMPLE_MODEL_ID


def get_llm(model_id: str):
    return init_chat_model(model=f"google_genai:{model_id}")


def is_allowed_model(model_id: str) -> bool:
    return model_id in _ALLOWED_IDS


def list_models() -> list[dict]:
    return LLM_MODELS
