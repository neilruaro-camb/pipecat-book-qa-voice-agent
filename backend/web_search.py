"""Web search functionality using Exa API."""

import os
from typing import List, Dict, Any

from loguru import logger

try:
    from exa_py import Exa
except ImportError:
    Exa = None
    logger.warning("exa-py not installed. Web search disabled.")


class WebSearcher:
    """Handles web search using Exa API."""

    def __init__(self, api_key: str = None):
        """Initialize the web searcher.

        Args:
            api_key: Exa API key. If not provided, reads from EXA_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self._client = None

        if Exa is None:
            logger.warning("Exa not available - web search will be disabled")
        elif not self.api_key:
            logger.warning("EXA_API_KEY not set - web search will be disabled")

    @property
    def client(self) -> "Exa":
        """Lazy initialization of Exa client."""
        if self._client is None and Exa is not None and self.api_key:
            self._client = Exa(api_key=self.api_key)
        return self._client

    async def search(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """Search the web using Exa.

        Args:
            query: The search query.
            num_results: Number of results to return.

        Returns:
            List of search results with title, url, and text.
        """
        if self.client is None:
            logger.warning("Web search not available")
            return [{"error": "Web search is not configured"}]

        try:
            logger.info(f"Searching web for: {query}")

            # Use search_and_contents for text snippets
            response = self.client.search_and_contents(
                query,
                num_results=num_results,
                text={"max_characters": 500},
            )

            results = []
            for result in response.results:
                results.append({
                    "title": result.title,
                    "url": result.url,
                    "text": result.text[:500] if result.text else "",
                })

            logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return [{"error": str(e)}]

    def format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for LLM consumption.

        Args:
            results: List of search results.

        Returns:
            Formatted string for LLM.
        """
        if not results:
            return "No results found."

        if "error" in results[0]:
            return f"Search error: {results[0]['error']}"

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result['title']}\n"
                f"   URL: {result['url']}\n"
                f"   {result['text']}"
            )

        return "\n\n".join(formatted)
