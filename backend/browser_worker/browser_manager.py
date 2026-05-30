"""
Browser session manager - persistent Playwright sessions with multi-tab control.
"""
import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BROWSER_DATA_DIR = Path("./data/browser")


class BrowserSession:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.browser = None
        self.context = None
        self.pages: dict[str, object] = {}
        self.active_page_id: Optional[str] = None
        self.created_at = datetime.utcnow().isoformat()
        self.last_active = self.created_at
        self.user_data_dir = BROWSER_DATA_DIR / self.session_id
        self._lock = asyncio.Lock()

    async def launch(self, headless: bool = False):
        from playwright.async_api import async_playwright
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        p = await async_playwright().start()
        self.browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 720},
        )
        self.context = self.browser
        page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        page_id = str(uuid.uuid4())[:8]
        self.pages[page_id] = page
        self.active_page_id = page_id
        logger.info(f"Browser session {self.session_id} launched")

    async def new_page(self) -> str:
        page = await self.context.new_page()
        page_id = str(uuid.uuid4())[:8]
        self.pages[page_id] = page
        self.active_page_id = page_id
        self.last_active = datetime.utcnow().isoformat()
        return page_id

    async def close_page(self, page_id: str):
        if page_id in self.pages:
            await self.pages[page_id].close()
            del self.pages[page_id]
            if self.active_page_id == page_id:
                self.active_page_id = next(iter(self.pages.keys())) if self.pages else None

    async def get_active_page(self):
        if self.active_page_id and self.active_page_id in self.pages:
            return self.pages[self.active_page_id]
        if self.pages:
            self.active_page_id = next(iter(self.pages.keys()))
            return self.pages[self.active_page_id]
        return await self.context.new_page() if self.context else None

    async def goto(self, url: str, page_id: str = None):
        page = self.pages.get(page_id) or await self.get_active_page()
        await page.goto(url, wait_until="domcontentloaded")
        self.last_active = datetime.utcnow().isoformat()
        return page.url

    async def screenshot(self, page_id: str = None) -> bytes:
        page = self.pages.get(page_id) or await self.get_active_page()
        return await page.screenshot(full_page=True)

    async def evaluate(self, script: str, page_id: str = None):
        page = self.pages.get(page_id) or await self.get_active_page()
        return await page.evaluate(script)

    async def close(self):
        if self.context:
            await self.context.close()
        self.pages.clear()
        self.active_page_id = None
        logger.info(f"Browser session {self.session_id} closed")


class BrowserManager:
    def __init__(self):
        self.sessions: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
        BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    async def create_session(self, headless: bool = False) -> BrowserSession:
        session = BrowserSession()
        await session.launch(headless=headless)
        async with self._lock:
            self.sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        return self.sessions.get(session_id)

    async def close_session(self, session_id: str):
        async with self._lock:
            session = self.sessions.pop(session_id, None)
        if session:
            await session.close()

    async def close_all(self):
        async with self._lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for s in sessions:
            await s.close()

    def get_status(self) -> dict:
        return {
            "sessions": len(self.sessions),
            "active": [{
                "id": s.session_id,
                "pages": len(s.pages),
                "active_page": s.active_page_id,
                "created": s.created_at,
                "last_active": s.last_active,
            } for s in self.sessions.values()],
        }
