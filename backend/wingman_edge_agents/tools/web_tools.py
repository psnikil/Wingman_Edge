from tools.data_models import DDGSearchArgs
import os
from typing import Optional, List
from langchain.tools import tool
from langchain_community.tools.brave_search.tool import BraveSearch
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_tavily import TavilySearch
import requests
from bs4 import BeautifulSoup

from .data_models import WebSearchArgs

def _optimize_query(query: str, context: Optional[str] = None) -> str:
    """Optimizes a search query by incorporating context if provided."""
    if context:
        return f"{query} {context}"
    return query

def _extract_content(url: str) -> Optional[str]:
    """Extracts main text content from a URL using BeautifulSoup."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text and clean up whitespace
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return None

@tool(
    parse_docstring=True, 
    args_schema=WebSearchArgs,
    description="""Performs a high-quality web search using the Brave Search API.
    Examples:
    - Simple search: web_search_brave(query="latest react hooks")
    - With context: web_search_brave(query="debugging memory leaks", context="Node.js")
    
    When to use: Best for finding up-to-date technical info, news, and general knowledge."""
)
def web_search_brave(query: str, context: Optional[str] = None) -> str:
    """Performs a web search using Brave Search."""
    args = WebSearchArgs(query=query, context=context)
    optimized_query = _optimize_query(args.query, args.context)
    brave = BraveSearch.from_api_key(api_key=os.getenv("BRAVE_SEARCH_API_KEY", ""))
    results_str = brave.run(optimized_query)
    return results_str

@tool(
    parse_docstring=True, 
    args_schema=DDGSearchArgs,
    description="""Performs a web search using DuckDuckGo with automated content extraction.
    Example: web_search_duckduckgo(query="python 3.12 release notes")
    
    When to use: Ideal for in-depth research when raw page content is needed."""
)
def web_search_duckduckgo(query: str, context: Optional[str] = None, **kwargs) -> str:
    """Performs a web search using DuckDuckGo."""
    args = DDGSearchArgs(query=query, **kwargs)
    optimized_query = _optimize_query(args.query)
    # Use wrapper to get results as list of dicts
    wrapper = DuckDuckGoSearchAPIWrapper()
    results = wrapper.results(optimized_query, max_results=args.max_results, source=args.source)
    
    enhanced_results = []
    for res in results:
        content = _extract_content(res['link'])
        enhanced_results.append({**res, "full_content": content[:1500] if content else "No content extracted"})
        
    return str(enhanced_results)

@tool(
    parse_docstring=True, 
    args_schema=WebSearchArgs,
    description="""Performs an AI-optimized search using Tavily, specifically for agents.
    Example: web_search_tavily(query="best practices for RAG systems")
    
    When to use: Provides cleaned results that are easiest for LLMs to process."""
)
def web_search_tavily(query: str, context: Optional[str] = None) -> str:
    """Performs an AI-optimized search using Tavily."""
    args = WebSearchArgs(query=query, context=context)
    optimized_query = _optimize_query(args.query, args.context)

    search_tool = TavilySearch()
    return search_tool.run(optimized_query)

__all__ = ["web_search_brave", "web_search_duckduckgo", "web_search_tavily"]
