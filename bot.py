"""
Entry point — Vercel serverless function.
Vercel вызывает handler(request, response) для каждого POST /webhook.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from http.server import BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from config import BOT_TOKEN, WEBHOOK_URL
from handlers import start, subscription, support

logging.basicConfig(level=logging.INFO)

# ── Build bot & dispatcher once (module-level, reused across warm invocations) ─
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(subscription.router)
dp.include_router(support.router)


async def _process_update(data: dict) -> None:
    update = Update(**data)
    await dp.feed_update(bot, update)


# ── Vercel handler ─────────────────────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # silence default access log
        pass

    def do_GET(self):
        # Used by Vercel health checks & webhook setup
        if self.path == "/setup_webhook":
            asyncio.run(self._setup())
            self._respond(200, {"ok": True, "webhook": WEBHOOK_URL})
        else:
            self._respond(200, {"ok": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            asyncio.run(_process_update(data))
            self._respond(200, {"ok": True})
        except Exception as e:
            logging.exception("Update processing error")
            self._respond(500, {"ok": False, "error": str(e)})

    def _respond(self, status: int, payload: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    async def _setup(self) -> None:
        await bot.set_webhook(WEBHOOK_URL)


# ── Local run (python bot.py) ──────────────────────────────────────────────────
if __name__ == "__main__":
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    import aiohttp.web as web

    async def on_startup(application: web.Application) -> None:
        await bot.set_webhook(WEBHOOK_URL)

    async def on_shutdown(application: web.Application) -> None:
        await bot.delete_webhook()

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", 8000))
    web.run_app(app, host="0.0.0.0", port=port)
