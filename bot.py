"""
Vercel serverless entry point.
Uses Flask + httpx (sync) to avoid asyncio/aiohttp event loop issues.
Telegram Bot API calls are made directly via httpx — no aiogram session needed.
"""
from __future__ import annotations

import json
import logging
import os

from flask import Flask, request, Response
from telegram_handler import handle_update

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        handle_update(data)
        return Response("ok", status=200)
    except Exception as e:
        logging.exception("Webhook error")
        return Response(str(e), status=500)


@app.route("/webapp/config.js", methods=["GET"])
def webapp_config():
    username = os.getenv("BOT_USERNAME", "")
    js = f"window.BOT_USERNAME = '{username}';\n"
    return Response(js, status=200, mimetype="application/javascript")


@app.route("/prices", methods=["GET"])
def prices():
    """Proxy Binance prices — avoids CORS issues from webapp."""
    import httpx as _httpx, json as _json
    symbols = {
        "TRX": "TRXUSDT", "ETH": "ETHUSDT", "BNB": "BNBUSDT",
        "BTC": "BTCUSDT", "SOL": "SOLUSDT", "TON": "TONUSDT",
    }
    result = {}
    for ticker, sym in symbols.items():
        try:
            r = _httpx.get(
                f"https://api.binance.com/api/v3/ticker/price?symbol={sym}",
                timeout=4
            )
            result[ticker] = float(r.json()["price"])
        except Exception:
            pass
    resp = Response(_json.dumps(result), status=200, mimetype="application/json")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.route("/", methods=["GET"])
def index():
    return Response("ok", status=200)


# Vercel looks for `app` (WSGI)
