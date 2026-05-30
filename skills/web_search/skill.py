"""
Web Search skill for JARVIS.
Searches the web via DuckDuckGo or other configured APIs.
"""
import asyncio
import json
import logging
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

import httpx


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "search": cmd_search,
        "fetch_page": cmd_fetch_page,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


async def cmd_search(query: str, num_results: int = 5) -> dict:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=num_results)):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
                if i >= num_results - 1:
                    break
        return {"results": results, "query": query}
    except ImportError:
        # Fallback: use httpx to scrape DuckDuckGo HTML
        return await _search_httpx(query, num_results)
    except Exception as e:
        return {"error": str(e)}


async def _search_httpx(query: str, num_results: int = 5) -> dict:
    """Fallback search using raw HTTP."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        from html.parser import HTMLParser

        class ResultParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self._in_result = False
                self._in_title = False
                self._in_snippet = False
                self._current = {}

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "a" and "result__a" in attrs_dict.get("class", ""):
                    self._in_title = True
                    self._current["url"] = attrs_dict.get("href", "")
                if tag == "a" and "result__snippet" in attrs_dict.get("class", ""):
                    self._in_snippet = True

            def handle_data(self, data):
                if self._in_title:
                    self._current["title"] = data.strip()
                if self._in_snippet:
                    self._current["snippet"] = data.strip()

            def handle_endtag(self, tag):
                if self._in_title and tag == "a":
                    self._in_title = False
                    if self._current.get("title"):
                        self.results.append(self._current)
                        self._current = {}
                if self._in_snippet and tag == "a":
                    self._in_snippet = False

        parser = ResultParser()
        parser.feed(resp.text)
        return {"results": parser.results[:num_results], "query": query, "source": "duckduckgo"}
    except Exception as e:
        return {"error": str(e)}


async def cmd_fetch_page(url: str) -> dict:
    """Fetch and extract text content from a URL."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()

        # Basic text extraction
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip_tags = {"script", "style", "nav", "footer", "header"}

            def handle_starttag(self, tag, attrs):
                if tag in self.skip_tags:
                    self._skip = True

            def handle_endtag(self, tag):
                if tag in self.skip_tags:
                    self._skip = False

            def handle_data(self, data):
                if not getattr(self, "_skip", False):
                    text = data.strip()
                    if text:
                        self.text.append(text)

        extractor = TextExtractor()
        extractor.feed(resp.text)
        content = "\n".join(extractor.text[:1000])
        return {"content": content, "url": url, "title": extractor.text[0] if extractor.text else ""}
    except Exception as e:
        return {"error": str(e)}
