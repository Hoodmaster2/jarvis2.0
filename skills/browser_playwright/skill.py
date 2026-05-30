"""
Browser automation skill using Playwright.
Provides web navigation, form filling, scraping, and screenshots.
"""
import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_browser = None
_page = None


async def execute(command: str, **kwargs) -> dict:
    """Execute a browser automation command."""
    commands = {
        "navigate": cmd_navigate,
        "click": cmd_click,
        "fill": cmd_fill,
        "scrape": cmd_scrape,
        "screenshot": cmd_screenshot,
        "get_html": cmd_get_html,
    }

    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}

    try:
        return await handler(**kwargs)
    except Exception as e:
        logger.error(f"Browser error: {e}")
        return {"error": str(e)}


async def _get_browser():
    """Lazy initialize Playwright browser."""
    global _browser, _page
    if _browser is None:
        try:
            from playwright.async_api import async_playwright
            p = await async_playwright().start()
            _browser = await p.chromium.launch(headless=True)
            _page = await _browser.new_page()
            logger.info("Playwright browser launched")
        except ImportError:
            raise RuntimeError("playwright not installed. Run: pip install playwright && playwright install")
        except Exception as e:
            raise RuntimeError(f"Failed to launch browser: {e}")
    return _page


async def cmd_navigate(url: str, headless: bool = True) -> dict:
    """Navigate to a URL."""
    page = await _get_browser()
    await page.goto(url, wait_until="domcontentloaded")
    title = await page.title()
    return {"status": "navigated", "url": url, "title": title}


async def cmd_click(selector: str) -> dict:
    """Click an element."""
    page = await _get_browser()
    await page.click(selector)
    return {"status": "clicked", "selector": selector}


async def cmd_fill(selector: str, value: str) -> dict:
    """Fill a form field."""
    page = await _get_browser()
    await page.fill(selector, value)
    return {"status": "filled", "selector": selector}


async def cmd_scrape(url: str = None) -> dict:
    """Scrape visible text from the page."""
    page = await _get_browser()
    if url:
        await page.goto(url, wait_until="domcontentloaded")
    text = await page.inner_text("body")
    # Clean up whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return {"content": "\n".join(lines[:500]), "lines": len(lines), "truncated": len(lines) > 500}


async def cmd_screenshot(path: str = None) -> dict:
    """Take a screenshot."""
    page = await _get_browser()
    if not path:
        path = str(Path.cwd() / "screenshot.png")
    await page.screenshot(path=path, full_page=True)
    return {"status": "screenshot_taken", "path": path}


async def cmd_get_html() -> dict:
    """Get page HTML."""
    page = await _get_browser()
    html = await page.content()
    return {"html": html, "size": len(html)}


async def cleanup():
    """Close browser."""
    global _browser, _page
    if _browser:
        await _browser.close()
        _browser = None
        _page = None
