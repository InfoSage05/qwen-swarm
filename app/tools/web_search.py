from duckduckgo_search import DDGS
import asyncio

async def perform_web_search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo and returns a formatted string of the top results.
    """
    try:
        def _search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results

        # Run the synchronous duckduckgo_search in an executor to avoid blocking the event loop
        results = await asyncio.to_thread(_search)
        
        if not results:
            return f"No results found for query: '{query}'"
            
        formatted_results = [f"Search Results for '{query}':"]
        for idx, res in enumerate(results, start=1):
            title = res.get('title', 'No Title')
            href = res.get('href', 'No URL')
            body = res.get('body', 'No Description')
            formatted_results.append(f"{idx}. {title}\n   URL: {href}\n   Snippet: {body}\n")
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Web search failed for query '{query}': {str(e)}"
