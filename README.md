# Piper API

FastAPI + LangGraph backend for the Piper coding assistant.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
# Install dependencies (creates venv automatically)
uv sync

# Copy env file and fill in values
cp .env.example .env
```

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `LANGSMITH_API_KEY` | LangSmith tracing key | No |

## Run

```bash
uvicorn main:app --reload --port 8000
```

API available at [http://localhost:8000](http://localhost:8000).

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Send a message, streams SSE response |

## Tests

```bash
pytest
```
