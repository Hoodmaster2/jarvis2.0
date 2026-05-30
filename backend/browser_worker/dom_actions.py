"""
DOM inspection and interaction actions for Playwright browser sessions.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def click_element(page, selector: str = None, text: str = None, xpath: str = None):
    if xpath:
        el = await page.locator(f"xpath={xpath}").first
    elif text:
        el = await page.get_by_text(text, exact=True).first
    elif selector:
        el = await page.locator(selector).first
    else:
        raise ValueError("Provide selector, text, or xpath")
    await el.scroll_into_view_if_needed()
    await el.click()
    return {"clicked": selector or text or xpath}


async def fill_form(page, selector: str, value: str):
    el = await page.locator(selector).first
    await el.fill(value)
    return {"filled": selector, "value": value}


async def get_text_content(page, selector: str = "body") -> str:
    el = await page.locator(selector).first
    return await el.inner_text()


async def get_page_info(page) -> dict:
    return {
        "url": page.url,
        "title": await page.title(),
        "viewport": page.viewport_size,
    }


async def get_visible_text(page) -> str:
    return await page.evaluate("() => document.body.innerText")


async def get_links(page) -> list[dict]:
    return await page.evaluate("""() =>
        Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.innerText.trim(),
            href: a.href,
            visible: a.offsetParent !== null
        }))
    """)


async def get_forms(page) -> list[dict]:
    return await page.evaluate("""() =>
        Array.from(document.querySelectorAll('form')).map((f, i) => ({
            index: i,
            action: f.action,
            method: f.method,
            inputs: Array.from(f.querySelectorAll('input, select, textarea')).map(el => ({
                name: el.name,
                type: el.type || el.tagName.toLowerCase(),
                placeholder: el.placeholder,
                required: el.required,
            }))
        }))
    """)


async def get_html(page, selector: str = "body") -> str:
    el = await page.locator(selector).first
    return await el.inner_html()


async def check_element(page, selector: str = None, text: str = None) -> dict:
    try:
        if text:
            el = page.get_by_text(text, exact=True).first
        else:
            el = page.locator(selector).first
        exists = await el.count() > 0
        if exists:
            return {
                "exists": True,
                "visible": await el.is_visible(),
                "enabled": await el.is_enabled(),
                "text": await el.text_content(),
            }
        return {"exists": False}
    except Exception as e:
        return {"exists": False, "error": str(e)}


async def fill_form_fields(page, fields: dict):
    results = []
    for selector, value in fields.items():
        try:
            el = page.locator(selector).first
            await el.fill(str(value))
            results.append({"selector": selector, "filled": True})
        except Exception as e:
            results.append({"selector": selector, "filled": False, "error": str(e)})
    return results
