"""
Page utilities: screenshots, summaries, SEO audits, safe scraping.
"""
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


async def take_screenshot(page, full_page: bool = True) -> bytes:
    return await page.screenshot(full_page=full_page)


async def capture_element_screenshot(page, selector: str) -> bytes:
    el = page.locator(selector).first
    return await el.screenshot()


async def summarize_page(page, max_words: int = 200) -> dict:
    text = await page.evaluate("() => document.body.innerText")
    title = await page.title()
    url = page.url
    words = text.split()
    summary = " ".join(words[:max_words])
    if len(words) > max_words:
        summary += "..."
    return {
        "url": url,
        "title": title,
        "summary": summary,
        "word_count": len(words),
    }


async def safe_scrape(page, selectors: list[str] = None) -> dict:
    if selectors:
        result = {}
        for sel in selectors:
            try:
                els = page.locator(sel)
                count = await els.count()
                items = []
                for i in range(count):
                    items.append(await els.nth(i).inner_text())
                result[sel] = items
            except Exception as e:
                result[sel] = {"error": str(e)}
        return result
    return {"text": await page.evaluate("() => document.body.innerText")}


async def test_links(page) -> list[dict]:
    links = await page.evaluate("""() =>
        Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.innerText.trim(),
            href: a.href,
        }))
    """)
    results = []
    for link in links[:50]:
        try:
            resp = await page.request.get(link["href"])
            results.append({
                "url": link["href"],
                "text": link["text"],
                "status": resp.status,
                "ok": resp.ok,
            })
        except Exception as e:
            results.append({"url": link["href"], "error": str(e)})
    return results


async def seo_audit(page) -> dict:
    info = await page.evaluate("""() => {
        const meta = document.querySelector('meta[name="description"]');
        const og = document.querySelector('meta[property="og:title"]');
        const h1 = document.querySelector('h1');
        const images = Array.from(document.images);
        return {
            title: document.title,
            title_length: document.title.length,
            meta_description: meta ? meta.content : null,
            meta_description_length: meta ? meta.content.length : 0,
            og_title: og ? og.content : null,
            h1_count: document.querySelectorAll('h1').length,
            h1_text: h1 ? h1.innerText : null,
            img_with_alt: images.filter(i => i.alt).length,
            img_without_alt: images.filter(i => !i.alt).length,
            links: document.querySelectorAll('a').length,
        };
    }""")
    issues = []
    if not info["meta_description"]:
        issues.append("Missing meta description")
    if info["title_length"] > 60:
        issues.append(f"Title too long ({info['title_length']} chars)")
    if info["h1_count"] > 1:
        issues.append(f"Multiple H1 tags ({info['h1_count']})")
    if info["img_without_alt"] > 0:
        issues.append(f"{info['img_without_alt']} images missing alt text")
    info["issues"] = issues
    info["score"] = max(0, 100 - len(issues) * 20)
    return info


async def check_uptime(url: str) -> dict:
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            start = datetime.utcnow()
            async with session.get(url, timeout=10) as resp:
                elapsed = (datetime.utcnow() - start).total_seconds()
                return {
                    "url": url,
                    "status": resp.status,
                    "ok": resp.ok,
                    "response_time_ms": round(elapsed * 1000),
                }
    except Exception as e:
        return {"url": url, "ok": False, "error": str(e)}


async def monitor_page_changes(page, previous_hash: str = None) -> dict:
    current_text = await page.evaluate("() => document.body.innerText")
    current_hash = str(hash(current_text))
    changed = previous_hash is not None and current_hash != previous_hash
    return {
        "changed": changed,
        "hash": current_hash,
        "previous_hash": previous_hash,
    }
