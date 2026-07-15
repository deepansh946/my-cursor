import os

from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web for current information, documentation, or anything not in the codebase."""
    from tavily import TavilyClient

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Web search unavailable: TAVILY_API_KEY not set."
    client = TavilyClient(api_key=api_key)
    results = client.search(query, max_results=10)
    items = results.get("results", [])
    if not items:
        return f"Query: {query}\n\nNo results found."

    sources = "\n".join(
        f"- {r.get('title', '')} ({r.get('url', '')})" for r in items
    )
    details = "\n\n".join(
        f"**{r.get('title', '')}** ({r.get('url', '')})\n{r.get('content', '')}"
        for r in items
    )
    return f"Query: {query}\n\nSources:\n{sources}\n\n{details}"
