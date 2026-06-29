import asyncio
from tavily import TavilyClient
from app.config import settings

async def perform_web_search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using Tavily API and returns a formatted string of the top results.
    """
    if not settings.TAVILY_API_KEY:
        return "Web search failed: TAVILY_API_KEY is not configured in .env"

    try:
        def _search():
            client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            return client.search(query=query, search_depth="basic", max_results=max_results)

        # Run the synchronous Tavily client in an executor to avoid blocking the event loop
        response = await asyncio.to_thread(_search)
        results = response.get("results", [])
        
        if not results:
            return f"No results found for query: '{query}'"
            
        formatted_results = [f"Search Results for '{query}':"]
        for idx, res in enumerate(results, start=1):
            title = res.get('title', 'No Title')
            href = res.get('url', 'No URL')
            body = res.get('content', 'No Description')
            formatted_results.append(f"{idx}. {title}\n   URL: {href}\n   Snippet: {body}\n")
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Web search failed for query '{query}': {str(e)}"
