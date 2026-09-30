"""
Sync Telegram bot handler using httpx.
No aiogram, no asyncio — works reliably in Vercel serverless.

Button colors via Bot API 9.4 (style field):
  "success"  — green
  "danger"   — red
  "primary"  — blue/accent
  (no style) — default
"""
from __future__ import annotations

import logging
import os
import random
import string

import httpx

from config import BOT_TOKEN, ADMIN_ID, PLANS, WALLETS, API_PACKS, API_PRICE_PER_1M, API_MIN_USD
from fsm_store import get_state, set_state, get_data, set_data, clear_state

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
log = logging.getLogger(__name__)

# In-memory user registry — counts unique users per warm instance
# (resets on cold start, but enough for notifications)
_known_users: set[int] = set()


# ── Low-level API ──────────────────────────────────────────────────────────────

def api(method: str, **kwargs) -> dict:
    try:
        r = httpx.post(f"{API}/{method}", json=kwargs, timeout=10)
        return r.json()
    except Exception as e:
        log.error(f"API error {method}: {e}")
        return {}


def send(chat_id: int, text: str, reply_markup=None, parse_mode: str = "HTML") -> dict:
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", **payload)


def send_photo(chat_id: int, photo: str, caption: str,
               reply_markup=None, parse_mode: str = "HTML") -> dict:
    payload: dict = {
        "chat_id": chat_id, "photo": photo,
        "caption": caption, "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendPhoto", **payload)


def delete_msg(chat_id: int, message_id: int) -> None:
    api("deleteMessage", chat_id=chat_id, message_id=message_id)


def answer_cb(callback_id: str, text: str = "", show_alert: bool = False) -> None:
    api("answerCallbackQuery",
        callback_query_id=callback_id, text=text, show_alert=show_alert)


def replace(chat_id: int, old_id: int, text: str, reply_markup=None) -> dict:
    """Send new text THEN delete old — no flicker."""
    result = send(chat_id, text, reply_markup=reply_markup)
    delete_msg(chat_id, old_id)
    return result


def replace_photo(chat_id: int, old_id: int, photo: str,
                  caption: str, reply_markup=None) -> dict:
    """Send new photo THEN delete old — no flicker."""
    result = send_photo(chat_id, photo, caption, reply_markup=reply_markup)
    delete_msg(chat_id, old_id)
    return result


# ── Ticket ID ──────────────────────────────────────────────────────────────────

def gen_ticket_id() -> str:
    chars = string.ascii_uppercase + string.digits
    return "TKT-" + "".join(random.choices(chars, k=6))


# ── Button helpers ─────────────────────────────────────────────────────────────

def btn(text: str, cb: str, style: str | None = None) -> dict:
    b: dict = {"text": text, "callback_data": cb}
    if style:
        b["style"] = style
    return b


def btn_url(text: str, url: str, style: str | None = None) -> dict:
    b: dict = {"text": text, "url": url}
    if style:
        b["style"] = style
    return b


def btn_webapp(text: str, url: str, style: str | None = None) -> dict:
    b: dict = {"text": text, "web_app": {"url": url}}
    if style:
        b["style"] = style
    return b


# ── Keyboards ──────────────────────────────────────────────────────────────────

def kb_main_inline() -> dict:
    host = os.getenv("WEBHOOK_HOST", "https://cld-mu.vercel.app")
    return {"inline_keyboard": [
        [btn_webapp("Chat with Claude", f"{host}/webapp", "success")],
        [btn("My Profile", "profile", "primary")],
        [btn("API Key",    "api_key",  "success")],
        [
            btn("About",   "about",   "danger"),
            btn("Support", "support", "danger"),
        ],
    ]}


def kb_main_reply() -> dict:
    """Removed — reply keyboard caused duplicate Chat with Claude button."""
    return {"remove_keyboard": True}


def kb_main() -> dict:
    """Legacy alias."""
    return kb_main_inline()


def kb_plans() -> dict:
    rows = []
    for key, plan in PLANS.items():
        label = plan["label"]
        price = f"${plan['price_usd']}"
        badge = f"  {plan['badge']}" if plan.get("badge") else ""
        rows.append([btn(f"{label} — {price}{badge}", f"plan:{key}", "primary")])
    rows.append([btn("Back to menu", "back_main", "primary")])
    return {"inline_keyboard": rows}


def kb_currencies(plan_key: str) -> dict:
    keys = list(WALLETS.keys())
    rows = []
    for i in range(0, len(keys), 2):
        chunk = keys[i:i + 2]
        rows.append([btn(c, f"pay:{plan_key}:{c}") for c in chunk])
    rows.append([btn("Back to plans", "subscribe")])
    return {"inline_keyboard": rows}


def kb_paid(plan_key: str) -> dict:
    return {"inline_keyboard": [
        [btn("I have paid", f"paid:{plan_key}", "success")],
        [btn("Change currency", f"plan:{plan_key}")],
        [btn("Back to menu", "back_main", "primary")],
    ]}


def kb_back() -> dict:
    return {"inline_keyboard": [[btn("Back to menu", "back_main", "primary")]]}


def kb_api_packs() -> dict:
    rows = []
    for key, pack in API_PACKS.items():
        badge = f"  {pack['badge']}" if pack.get("badge") else ""
        rows.append([btn(
            f"{pack['label']}{badge}",
            f"api_pack:{key}", "primary"
        )])
    rows.append([btn("Custom amount", "api_custom", "success")])
    rows.append([btn("Back to menu",  "back_main",  "primary")])
    return {"inline_keyboard": rows}


def kb_api_currencies(pack_key: str) -> dict:
    keys = list(WALLETS.keys())
    rows = []
    for i in range(0, len(keys), 2):
        chunk = keys[i:i + 2]
        rows.append([btn(c, f"api_pay:{pack_key}:{c}") for c in chunk])
    rows.append([btn("Back to API plans", "api_key", "primary")])
    return {"inline_keyboard": rows}


def kb_api_paid(pack_key: str) -> dict:
    return {"inline_keyboard": [
        [btn("I have paid",      f"api_paid:{pack_key}", "success")],
        [btn("Change currency",  f"api_pack:{pack_key}")],
        [btn("Back to menu",     "back_main", "primary")],
    ]}


def kb_cancel() -> dict:
    return {"inline_keyboard": [[btn("Cancel", "back_main", "danger")]]}


def kb_ticket() -> dict:
    return {"inline_keyboard": [
        [btn("Send ticket", "send_ticket", "success")],
        [btn("Rewrite",     "support")],
        [btn("Cancel",      "back_main", "danger")],
    ]}


# ── Static texts ───────────────────────────────────────────────────────────────

BANNER = os.getenv("BANNER_FILE_ID", "https://raw.githubusercontent.com/ivanfj633kfdodfd-cmyk/Cld/main/banner.jpg")

WELCOME = (
    "<b>Claude AI — subscription via crypto</b>\n\n"
    "Get full access to Claude AI: all models, Claude Code, "
    "Projects, web search, and more.\n\n"
    "<blockquote>"
    "✓ Sonnet 5, Opus 5, Opus 5.5, Haiku — all models\n"
    "✓ Claude Code, Projects, memory, web search\n"
    "✓ Web App inside Telegram\n"
    "✓ API key for developers — available on request"
    "</blockquote>"
)

# About — Claude model changelog as of September 2026
ABOUT = (
    "<b>What's new in Claude — September 2026</b>\n\n"

    "<b>Claude Opus 5.5</b>  <i>Sep 22, 2026</i>\n"
    "<blockquote>"
    "First model in the Claude 5.5 family. Reaches Fable 5.1-level "
    "coding performance at 40% lower cost than Opus 5. New default for "
    "Claude Max. Best scores on Anthropic's behavioral audit to date."
    "</blockquote>\n\n"

    "<b>Claude Opus 5</b>  <i>May 2026</i>\n"
    "<blockquote>"
    "State-of-the-art on Frontier-Bench and GDPval-AA. Doubles Opus 4.8 "
    "performance on software engineering at the same cost. Best model on "
    "Claude Pro. Outperforms all others on ARC-AGI 3 and OSWorld 2.0."
    "</blockquote>\n\n"

    "<b>Claude Sonnet 5</b>  <i>default on Free and Pro</i>\n"
    "<blockquote>"
    "Most agentic Sonnet yet. Close to Opus 4.8 performance at lower cost. "
    "Adaptive thinking on by default. Strong multi-step coding and tool use."
    "</blockquote>\n\n"

    "<b>Plans available</b>\n"
    "Claude Pro · Claude Max 5× · Claude Max 20×\n\n"

    "<a href=\"https://www.anthropic.com/news\">Learn more on Anthropic blog</a>"
)


def api_key_text() -> str:
    """Sent via sendRichMessage for native table support."""
    return (
        "# API Key — prepaid tokens\n\n"
        "Get an Anthropic API key for VS Code, Cursor, Claude Code, or any integration.\n\n"
        "## How it works\n\n"
        "> 1. Choose a token pack\n"
        "> 2. Pay with crypto\n"
        "> 3. Receive your API key (`sk-ant-...`) within 30 min\n"
        "> 4. Paste the key into your app or IDE\n\n"
        "## Packs\n\n"
        "| Pack | Tokens | Per month | Best for |\n"
        "| :--- | :---: | :---: | :--- |\n"
        "| **$100** | ~12.5M | ~$100 | 6 months avg dev |\n"
        "| **$200** | ~25M | ~$200 | 1 year avg dev |\n"
        "| **$500** | ~65M | ~$500 | Heavy usage |\n\n"
        "---\n\n"
        f"*${API_PRICE_PER_1M}/1M tokens · minimum order ${API_MIN_USD}*\n\n"
        "Or enter a custom amount with the button below."
    )


def _send_api_key_message(chat_id: int, reply_markup: dict) -> dict:
    """Use sendRichMessage for native table; fallback to sendMessage."""
    markdown = api_key_text()
    result = api("sendRichMessage",
        chat_id=chat_id,
        rich_message={"markdown": markdown},
        reply_markup=reply_markup
    )
    if not result.get("ok"):
        # Fallback: plain text
        plain = (
            "<b>API Key — prepaid tokens</b>\n\n"
            "Get an Anthropic API key for VS Code, Cursor, Claude Code.\n\n"
            "<b>Packs:</b>\n"
            "<pre>"
            "$100  →  12.5M tokens\n"
            "$200  →  25M tokens   [Popular]\n"
            "$500  →  65M tokens   [Best value]"
            "</pre>\n\n"
            f"<i>${API_PRICE_PER_1M}/1M tokens · min ${API_MIN_USD}</i>"
        )
        result = api("sendMessage",
            chat_id=chat_id,
            text=plain,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    return result


def api_pack_detail(pack_key: str) -> str:
    pack = API_PACKS[pack_key]
    return (
        f"<b>{pack['label']}</b>\n\n"
        f"<b>Tokens:</b> ~{pack['tokens_m']}M\n"
        f"<b>Price:</b> ${pack['price_usd']} USD\n\n"
        f"<blockquote>{pack['desc']}</blockquote>\n\n"
        "Select payment currency:"
    )


# ── Crypto price lookup ────────────────────────────────────────────────────────
_STABLE  = {"USDT TRC-20", "USDT ERC-20", "USDC ERC-20", "USDT", "USDC"}

# Binance symbols for each currency
_BINANCE_SYM: dict[str, str] = {
    "TRX":          "TRXUSDT",
    "ETH":          "ETHUSDT",
    "BNB":          "BNBUSDT",
    "BTC":          "BTCUSDT",
    "SOL":          "SOLUSDT",
    "TON":          "TONUSDT",
}

# Hardcoded fallback rates (updated Sep 2026)
_FALLBACK: dict[str, float] = {
    "TRX": 0.13, "ETH": 2500, "BNB": 580,
    "BTC": 95000, "SOL": 145, "TON": 4.8,
}

_price_cache: dict[str, tuple[float, float]] = {}
_CACHE_TTL = 120  # 2 min


def get_crypto_price(currency: str) -> float:
    """Return USD price of 1 unit. Stablecoins = 1.0. Never returns None."""
    import time
    # Normalize: "ETH", "BTC", "USDT TRC-20" → ticker
    ticker = currency.split()[0]

    if ticker in ("USDT", "USDC"):
        return 1.0

    sym = _BINANCE_SYM.get(ticker)
    if not sym:
        return _FALLBACK.get(ticker, 1.0)

    now = time.time()
    if sym in _price_cache:
        price, ts = _price_cache[sym]
        if now - ts < _CACHE_TTL:
            return price

    try:
        r = httpx.get(
            f"https://api.binance.com/api/v3/ticker/price",
            params={"symbol": sym},
            timeout=5
        )
        data  = r.json()
        price = float(data["price"])
        _price_cache[sym] = (price, now)
        log.info(f"Price {sym}: ${price}")
        return price
    except Exception as e:
        log.warning(f"Price fetch failed for {sym}: {e}")
        # Return stale cache or fallback
        if sym in _price_cache:
            return _price_cache[sym][0]
        return _FALLBACK.get(ticker, 1.0)


def format_crypto_amount(usd: float, currency: str) -> str:
    """Return human-readable crypto amount, e.g. '0.005263 ETH'."""
    ticker = currency.split()[0]
    price  = get_crypto_price(currency)
    amount = usd / price

    if ticker in ("USDT", "USDC"):
        return f"{int(usd)} {ticker}"
    elif amount >= 1000:
        fmt = f"{amount:.2f}"
    elif amount >= 1:
        fmt = f"{amount:.4f}"
    elif amount >= 0.0001:
        fmt = f"{amount:.6f}"
    else:
        fmt = f"{amount:.8f}"

    return f"{fmt} {ticker}"


def api_requisites_text(pack_key: str, currency: str, usd: int | None = None,
                        tokens_m: float | None = None) -> str:
    if pack_key.startswith("custom_") and usd:
        label = f"API Custom — ${usd}"
        tok   = tokens_m or round(usd / API_PRICE_PER_1M, 1)
        price = usd
    else:
        pack  = API_PACKS[pack_key]
        label = pack["label"]
        tok   = pack["tokens_m"]
        price = pack["price_usd"]
    wallet       = WALLETS[currency]
    crypto_amount = format_crypto_amount(price, currency)
    return (
        f"<b>API Key payment</b>\n\n"
        f"<b>Pack:</b> {label}\n"
        f"<b>Tokens:</b> ~{tok}M\n"
        f"<b>Amount:</b> <b>{crypto_amount}</b>  <i>(≈ ${price} USD)</i>\n"
        f"<b>Network:</b> {wallet['network']}\n\n"
        f"<b>Wallet address:</b>\n"
        f"<code>{wallet['address']}</code>\n\n"
        "<blockquote>Send exactly the amount shown above via the network indicated.\n"
        "After payment tap <b>\"I have paid\"</b> — "
        "your API key will arrive within 30 minutes.</blockquote>"
    )

def plans_text() -> str:
    rows = []
    for key, plan in PLANS.items():
        badge = f" [{plan['badge']}]" if plan.get("badge") else ""
        rows.append(f"| **{plan['label']}** | ${plan['price_usd']}/mo{badge} |")
    table = "\n".join(rows)
    return (
        "# Claude — plans and pricing\n\n"
        "| Plan | Price |\n"
        "| :--- | :---: |\n"
        f"{table}\n\n"
        "---\n\n"
        "*Official plans · [claude.com/pricing](https://claude.com/pricing)*"
    )


def _send_plans_message(chat_id: int, reply_markup: dict) -> dict:
    result = api("sendRichMessage",
        chat_id=chat_id,
        rich_message={"markdown": plans_text()},
        reply_markup=reply_markup
    )
    if not result.get("ok"):
        plain = "<b>Claude — plans and pricing</b>\n\n"
        plain += "<pre>"
        for key, plan in PLANS.items():
            badge = f"  [{plan['badge']}]" if plan.get("badge") else ""
            plain += f"{plan['label']}  —  ${plan['price_usd']}/mo{badge}\n"
        plain += "</pre>\n\n<i>Official plans · claude.com/pricing</i>"
        result = api("sendMessage",
            chat_id=chat_id, text=plain,
            parse_mode="HTML", reply_markup=reply_markup
        )
    return result


def plan_detail_text(plan_key: str) -> str:
    plan   = PLANS[plan_key]
    feats  = "\n".join(f"  ✓ {f}" for f in plan["features"])
    saving = f"\n<b>Saving:</b> {plan['saving']}" if plan["saving"] else ""
    return (
        f"<b>{plan['label']}</b>\n"
        f"<b>Price:</b> ${plan['price_usd']}/month{saving}\n\n"
        f"<b>Includes:</b>\n"
        f"<blockquote>{feats}</blockquote>\n\n"
        "Select payment currency:"
    )


def requisites_text(plan_key: str, currency: str) -> str:
    plan         = PLANS[plan_key]
    wallet       = WALLETS[currency]
    crypto_amount = format_crypto_amount(plan["price_usd"], currency)
    return (
        f"<b>Payment details</b>\n\n"
        f"<b>Plan:</b> {plan['label']}\n"
        f"<b>Amount:</b> <b>{crypto_amount}</b>  <i>(≈ ${plan['price_usd']} USD)</i>\n"
        f"<b>Network:</b> {wallet['network']}\n\n"
        f"<b>Wallet address:</b>\n"
        f"<code>{wallet['address']}</code>\n\n"
        "<blockquote>Send only via the network shown above.\n"
        "Transfers on a different network will not be credited.</blockquote>\n\n"
        "After sending, tap <b>\"I have paid\"</b>."
    )


# ── New user notification ──────────────────────────────────────────────────────

def notify_new_user(user: dict, total: int) -> None:
    user_id   = user.get("id")
    full_name = " ".join(filter(None, [
        user.get("first_name", ""), user.get("last_name", "")
    ]))
    username  = user.get("username", "")
    uname_str = f"@{username}" if username else "no username"
    dialog    = f"tg://user?id={user_id}"

    send(ADMIN_ID,
        f"<b>New user</b>\n\n"
        f"Name: <a href='{dialog}'>{full_name}</a>\n"
        f"Username: {uname_str}\n"
        f"ID: <code>{user_id}</code>\n\n"
        f"Total users seen: <b>{total}</b>"
    )


# ── Update router ──────────────────────────────────────────────────────────────

def handle_update(data: dict) -> None:
    if "message" in data:
        msg = data["message"]
        # web_app_data comes as a special message field
        if "web_app_data" in msg:
            _handle_webapp_data(msg)
        else:
            _handle_message(msg)
    elif "callback_query" in data:
        _handle_callback(data["callback_query"])


# ── Web App data handler ───────────────────────────────────────────────────────

def _handle_webapp_data(msg: dict) -> None:
    chat_id  = msg["chat"]["id"]
    user_id  = msg["from"]["id"]
    payload  = msg.get("web_app_data", {}).get("data", "")

    if payload == "open_subscribe":
        clear_state(user_id)
        send(chat_id, plans_text(), reply_markup=kb_plans())


# ── Message handler ────────────────────────────────────────────────────────────

def _handle_message(msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    user    = msg["from"]
    user_id = user["id"]
    text    = msg.get("text", "")

    if text.startswith("/start"):
        # Parse deep link parameter: /start subscribe → show plans immediately
        parts = text.split(" ", 1)
        param = parts[1].strip() if len(parts) > 1 else ""

        # Track new users
        if user_id not in _known_users:
            _known_users.add(user_id)
            notify_new_user(user, len(_known_users))

        clear_state(user_id)

        if param == "subscribe":
            rm = send(chat_id, "\u200b", reply_markup={"remove_keyboard": True, "selective": False})
            rm_id = rm.get("result", {}).get("message_id")
            if rm_id: delete_msg(chat_id, rm_id)
            send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main_inline())
            send(chat_id, plans_text(), reply_markup=kb_plans())
            return

        if param.startswith("api_"):
            # format: api_{usd}_{currency_underscored}
            rm = send(chat_id, "\u200b", reply_markup={"remove_keyboard": True, "selective": False})
            rm_id = rm.get("result", {}).get("message_id")
            if rm_id: delete_msg(chat_id, rm_id)
            send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main_inline())
            try:
                parts2     = param.split("_", 2)  # api, usd, currency
                usd        = int(parts2[1])
                currency   = parts2[2].replace("_", " ")
                tokens_m   = round(usd / API_PRICE_PER_1M, 1)
                custom_key = f"custom_{usd}"
                set_data(user_id, {"custom_pack": {
                    "label":     f"API Custom — ${usd}",
                    "price_usd": usd,
                    "tokens_m":  tokens_m,
                    "badge":     None,
                    "desc":      f"~{tokens_m}M токенов",
                }})
                wallet = WALLETS.get(currency, list(WALLETS.values())[0])
                send(chat_id,
                    f"<b>Оплата API пакета</b>\n\n"
                    f"<b>Сумма:</b> ${usd}\n"
                    f"<b>Токенов:</b> ~{tokens_m}M\n"
                    f"<b>Валюта:</b> {currency}\n"
                    f"<b>Сеть:</b> {wallet['network']}\n\n"
                    f"<b>Адрес:</b>\n<code>{wallet['address']}</code>\n\n"
                    "<blockquote>После оплаты нажмите «I have paid».</blockquote>",
                    reply_markup=kb_api_paid(custom_key)
                )
            except Exception:
                send(chat_id, api_key_text(), reply_markup=kb_api_packs())
            return

        if param == "profile":
            rm = send(chat_id, "\u200b", reply_markup={"remove_keyboard": True, "selective": False})
            rm_id = rm.get("result", {}).get("message_id")
            if rm_id: delete_msg(chat_id, rm_id)
            send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main_inline())
            # Immediately show profile
            full_name = " ".join(filter(None, [
                user.get("first_name", ""), user.get("last_name", "")
            ]))
            username  = user.get("username", "")
            uname_str = f"@{username}" if username else "not set"
            lang      = user.get("language_code", "—").upper()
            send(chat_id,
                f"<b>My Profile</b>\n\n"
                f"<b>Name:</b> {full_name}\n"
                f"<b>Username:</b> {uname_str}\n"
                f"<b>ID:</b> <code>{user_id}</code>\n"
                f"<b>Language:</b> {lang}\n\n"
                "<b>Subscription:</b>\n"
                "<blockquote>No active subscription.\n"
                "Use Chat with Claude to subscribe.</blockquote>",
                reply_markup=kb_back()
            )
            return

        # Default start — delete lingering reply keyboard, then send welcome
        rm = send(chat_id, "\u200b", reply_markup={"remove_keyboard": True, "selective": False})
        rm_id = rm.get("result", {}).get("message_id")
        if rm_id:
            delete_msg(chat_id, rm_id)
        send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main_inline())
        return

    # Admin: /reply <user_id> <text>
    if text.startswith("/reply") and user_id == ADMIN_ID:
        parts = text.split(" ", 2)
        if len(parts) < 3:
            send(chat_id, "Usage: /reply &lt;user_id&gt; &lt;message&gt;")
            return
        try:
            target = int(parts[1])
            send(target, f"<b>Support reply:</b>\n\n{parts[2]}")
            send(chat_id, "Sent.")
        except Exception as e:
            send(chat_id, f"Error: {e}")
        return

    # FSM: API custom amount
    if get_state(user_id) == "api:waiting_amount":
        store = get_data(user_id)
        if store.get("api_prompt_id"):
            delete_msg(chat_id, store["api_prompt_id"])
        delete_msg(chat_id, msg["message_id"])
        clear_state(user_id)
        try:
            amount = float(text.replace("$", "").replace(",", ".").strip())
            if amount < API_MIN_USD:
                send(chat_id,
                    f"Minimum amount is ${API_MIN_USD}. Please enter a larger amount.",
                    reply_markup={"inline_keyboard": [[btn("Cancel", "api_key")]]}
                )
                set_state(user_id, "api:waiting_amount")
                return
            tokens_m = round(amount / API_PRICE_PER_1M, 1)
            # Create ad-hoc pack
            custom_key = f"custom_{int(amount)}"
            # Store in FSM for currency step
            set_data(user_id, {"custom_pack": {
                "label":     f"API Custom — ${int(amount)}",
                "price_usd": int(amount),
                "tokens_m":  tokens_m,
                "badge":     None,
                "desc":      f"~{tokens_m}M токенов",
            }})
            # Build currency keyboard with custom key
            keys = list(WALLETS.keys())
            rows = []
            for i in range(0, len(keys), 2):
                chunk = keys[i:i + 2]
                rows.append([btn(c, f"api_pay:{custom_key}:{c}") for c in chunk])
            rows.append([btn("Back to API plans", "api_key", "primary")])
            kb = {"inline_keyboard": rows}
            send(chat_id,
                f"<b>Custom API pack</b>\n\n"
                f"<b>Amount:</b> ${int(amount)} USD\n"
                f"<b>Tokens:</b> ~{tokens_m}M\n\n"
                "Select payment currency:",
                reply_markup=kb
            )
        except ValueError:
            send(chat_id,
                "Please enter a number, e.g. <code>300</code>",
                reply_markup={"inline_keyboard": [[btn("Cancel", "api_key")]]}
            )
            set_state(user_id, "api:waiting_amount")
        return

    # FSM: ticket text input
    if get_state(user_id) == "support:waiting":
        store = get_data(user_id)
        ticket_id = gen_ticket_id()
        set_data(user_id, {**store, "ticket_text": text, "ticket_id": ticket_id})
        set_state(user_id, "support:confirm")

        if store.get("prompt_msg_id"):
            delete_msg(chat_id, store["prompt_msg_id"])
        delete_msg(chat_id, msg["message_id"])

        preview = send(
            chat_id,
            f"<b>Ticket preview</b>  <code>{ticket_id}</code>\n\n"
            f"<blockquote>{text}</blockquote>\n\n"
            "Looks good?",
            reply_markup=kb_ticket(),
        )
        new_id = preview.get("result", {}).get("message_id")
        set_data(user_id, {**get_data(user_id), "preview_msg_id": new_id})
        return


# ── Callback handler ───────────────────────────────────────────────────────────

def _handle_callback(cb: dict) -> None:
    cb_id   = cb["id"]
    data    = cb.get("data", "")
    msg     = cb["message"]
    chat_id = msg["chat"]["id"]
    msg_id  = msg["message_id"]
    user    = cb["from"]
    user_id = user["id"]

    answer_cb(cb_id)

    # Main menu
    if data == "back_main":
        clear_state(user_id)
        replace_photo(chat_id, msg_id, BANNER, WELCOME, reply_markup=kb_main())
        return

    if data == "about":
        replace(chat_id, msg_id, ABOUT, reply_markup=kb_back())
        return

    if data == "profile":
        full_name = " ".join(filter(None, [
            user.get("first_name", ""), user.get("last_name", "")
        ]))
        username  = user.get("username", "")
        uname_str = f"@{username}" if username else "not set"
        lang      = user.get("language_code", "—").upper()

        PROFILE_IMG = "https://raw.githubusercontent.com/ivanfj633kfdodfd-cmyk/Cld/main/Claude_3-7_illustration.png"

        caption = (
            "<b>My Profile</b>\n\n"
            f"<b>Name:</b> {full_name}\n"
            f"<b>Username:</b> {uname_str}\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Language:</b> {lang}\n\n"
            "<b>Subscription</b>\n"
            "<blockquote>"
            "No active subscription.\n"
            "Subscribe to get full access to Claude Pro."
            "</blockquote>\n\n"
            "<b>Access level:</b> Free plan\n"
            "<b>Models available:</b> Sonnet 5, Haiku 5\n"
            "<b>Claude Code:</b> —\n"
            "<b>Usage limit:</b> 0 messages"
        )
        kb_profile = {"inline_keyboard": [
            [btn("Subscribe", "subscribe", "success")],
            [btn("Back to menu", "back_main", "primary")],
        ]}
        # Send photo with profile, then delete old message
        send_photo(chat_id, PROFILE_IMG, caption, reply_markup=kb_profile)
        delete_msg(chat_id, msg_id)
        return

    # ── API Key flow ──────────────────────────────────────────────────────────
    if data == "api_key":
        delete_msg(chat_id, msg_id)
        _send_api_key_message(chat_id, kb_api_packs())
        return

    if data.startswith("api_pack:"):
        pack_key = data.split(":", 1)[1]
        replace(chat_id, msg_id,
            api_pack_detail(pack_key),
            reply_markup=kb_api_currencies(pack_key)
        )
        return

    if data == "api_custom":
        set_state(user_id, "api:waiting_amount")
        result = send(chat_id,
            "<b>Custom API amount</b>\n\n"
            f"Minimum order: <b>${API_MIN_USD}</b>\n\n"
            f"Enter amount in USD (e.g. <code>300</code>)\n"
            f"Rate: $1 = {1 / API_PRICE_PER_1M * 1000:.0f}K tokens",
            reply_markup={"inline_keyboard": [[btn("Cancel", "api_key")]]}
        )
        delete_msg(chat_id, msg_id)
        set_data(user_id, {"api_prompt_id": result.get("result", {}).get("message_id")})
        return

    if data.startswith("api_pay:"):
        _, pack_key, currency = data.split(":", 2)
        if pack_key.startswith("custom_"):
            store = get_data(user_id)
            pack  = store.get("custom_pack", {
                "label":     f"Custom ${pack_key.split('_')[1]}",
                "price_usd": int(pack_key.split("_")[1]),
                "tokens_m":  round(int(pack_key.split("_")[1]) / API_PRICE_PER_1M, 1),
            })
            usd      = pack["price_usd"]
            tokens_m = pack["tokens_m"]
        else:
            pack     = API_PACKS[pack_key]
            usd      = pack["price_usd"]
            tokens_m = pack["tokens_m"]
        wallet = WALLETS[currency]
        replace(chat_id, msg_id,
            api_requisites_text(pack_key, currency, usd=usd, tokens_m=tokens_m),
            reply_markup=kb_api_paid(pack_key)
        )
        return

    if data.startswith("api_paid:"):
        pack_key  = data.split(":", 1)[1]
        pack      = API_PACKS[pack_key]
        full_name = " ".join(filter(None, [
            user.get("first_name", ""), user.get("last_name", "")
        ]))
        username = user.get("username", "")

        send(ADMIN_ID,
            f"<b>API Key payment claim</b>\n\n"
            f"User: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"ID: <code>{user_id}</code>  @{username or '—'}\n\n"
            f"Pack: {pack['label']} — ${pack['price_usd']} USD\n"
            f"Tokens: ~{pack['tokens_m']}M\n\n"
            "Issue API key and send to user via /reply."
        )
        import datetime
        order_id   = gen_ticket_id()
        updated_at = datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
        kb_order = {"inline_keyboard": [
            [btn("Refresh status", f"api_refresh:{pack_key}", "success")],
            [btn("Back to menu",   "back_main", "primary")],
        ]}
        replace(chat_id, msg_id,
            f"<b>Order status</b>\n\n"
            f"<b>Order ID:</b> <code>{order_id}</code>\n"
            f"<b>Pack:</b> {pack['label']}\n"
            f"<b>Tokens:</b> ~{pack['tokens_m']}M\n"
            f"<b>Amount:</b> ${pack['price_usd']} USD\n\n"
            f"<b>Status:</b> ⏳ Processing\n\n"
            f"<i>Last updated: {updated_at}</i>\n\n"
            "Your API key will be sent to this chat once payment is confirmed.",
            reply_markup=kb_order
        )
        return

    if data.startswith("api_refresh:"):
        pack_key  = data.split(":", 1)[1]
        pack      = API_PACKS[pack_key]
        import datetime, time
        existing  = msg.get("text", "")
        order_id  = "—"
        for line in existing.splitlines():
            if "Order ID:" in line:
                order_id = line.split("Order ID:")[-1].strip()
                break
        kb_order = {"inline_keyboard": [
            [btn("Refresh status", f"api_refresh:{pack_key}", "success")],
            [btn("Back to menu",   "back_main", "primary")],
        ]}
        api("editMessageText", chat_id=chat_id, message_id=msg_id,
            text=(f"<b>Order status</b>\n\n"
                  f"<b>Order ID:</b> <code>{order_id}</code>\n\n"
                  f"♻️ <i>Refreshing...</i>"),
            parse_mode="HTML", reply_markup=kb_order)
        answer_cb(cb_id, show_alert=False)
        time.sleep(1)
        updated_at = datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
        api("editMessageText", chat_id=chat_id, message_id=msg_id,
            text=(f"<b>Order status</b>\n\n"
                  f"<b>Order ID:</b> <code>{order_id}</code>\n"
                  f"<b>Pack:</b> {pack['label']}\n"
                  f"<b>Tokens:</b> ~{pack['tokens_m']}M\n"
                  f"<b>Amount:</b> ${pack['price_usd']}\n\n"
                  f"<b>Status:</b> ⏳ Processing\n\n"
                  f"<i>Last updated: {updated_at}</i>\n\n"
                  "API ключ придёт в этот чат после подтверждения оплаты."),
            parse_mode="HTML", reply_markup=kb_order)
        return

    # Subscription flow
    if data == "subscribe":
        delete_msg(chat_id, msg_id)
        _send_plans_message(chat_id, kb_plans())
        return

    if data.startswith("plan:"):
        plan_key = data.split(":", 1)[1]
        plan  = PLANS[plan_key]
        feats = "\n".join(f"| ✓ | {f} |" for f in plan["features"])
        badge = f"  [{plan['badge']}]" if plan.get("badge") else ""
        md = (
            f"# {plan['label']} — ${plan['price_usd']}/mo{badge}\n\n"
            "## Includes\n\n"
            "| | Feature |\n"
            "| :---: | :--- |\n"
            f"{feats}\n\n"
            "---\n\n"
            "*Select payment currency:*"
        )
        result = api("sendRichMessage",
            chat_id=chat_id,
            rich_message={"markdown": md},
            reply_markup=kb_currencies(plan_key)
        )
        if not result.get("ok"):
            replace(chat_id, msg_id,
                plan_detail_text(plan_key),
                reply_markup=kb_currencies(plan_key)
            )
        else:
            delete_msg(chat_id, msg_id)
        return

    if data.startswith("pay:"):
        _, plan_key, currency = data.split(":", 2)
        plan          = PLANS[plan_key]
        wallet        = WALLETS[currency]
        crypto_amount = format_crypto_amount(plan["price_usd"], currency)
        md = (
            "# Payment details\n\n"
            "| | |\n"
            "| :--- | :--- |\n"
            f"| **Plan** | {plan['label']} |\n"
            f"| **Amount** | `{crypto_amount}` |\n"
            f"| **≈ USD** | ${plan['price_usd']} |\n"
            f"| **Network** | {wallet['network']} |\n\n"
            "**Wallet address:**\n\n"
            f"`{wallet['address']}`\n\n"
            "> Send only via the network shown above.\n"
            "> After sending tap **\"I have paid\"**."
        )
        result = api("sendRichMessage",
            chat_id=chat_id,
            rich_message={"markdown": md},
            reply_markup=kb_paid(plan_key)
        )
        if not result.get("ok"):
            replace(chat_id, msg_id,
                requisites_text(plan_key, currency),
                reply_markup=kb_paid(plan_key)
            )
        else:
            delete_msg(chat_id, msg_id)
        return

    if data.startswith("paid:"):
        plan_key  = data.split(":", 1)[1]
        plan      = PLANS[plan_key]
        full_name = " ".join(filter(None, [
            user.get("first_name", ""), user.get("last_name", "")
        ]))
        username = user.get("username", "")

        send(ADMIN_ID,
            f"<b>Payment claim</b>\n\n"
            f"User: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"ID: <code>{user_id}</code>\n"
            f"Username: @{username or 'none'}\n\n"
            f"Plan: {plan['label']} — ${plan['price_usd']}\n\n"
            "Verify the transaction and grant access."
        )
        answer_cb(cb_id, "Notification sent to admin.", show_alert=True)

        # Store order info for refresh button
        import datetime
        updated_at = datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
        uname_str  = f"@{username}" if username else "—"
        order_id   = gen_ticket_id()

        order_text = (
            "<b>Order status</b>\n\n"
            f"<b>Order ID:</b> <code>{order_id}</code>\n"
            f"<b>Plan:</b> {plan['label']}\n"
            f"<b>Amount:</b> ${plan['price_usd']}\n"
            f"<b>Account:</b> {uname_str}  <code>{user_id}</code>\n\n"
            f"<b>Status:</b>  ⏳ Processing\n\n"
            f"<i>Last updated: {updated_at}</i>"
        )
        kb_order = {"inline_keyboard": [
            [btn("Refresh status", f"order_refresh:{plan_key}", "success")],
            [btn("Back to menu",   "back_main", "primary")],
        ]}
        replace(chat_id, msg_id, order_text, reply_markup=kb_order)
        return

    if data.startswith("order_refresh:"):
        plan_key = data.split(":", 1)[1]
        plan     = PLANS[plan_key]
        import datetime, time
        username  = user.get("username", "")
        uname_str = f"@{username}" if username else "—"

        # Retrieve order_id from message text
        existing_text = msg.get("text") or msg.get("caption") or ""
        order_id = "—"
        for line in existing_text.splitlines():
            if "Order ID:" in line:
                order_id = line.split("Order ID:")[-1].strip()
                break

        kb_order = {"inline_keyboard": [
            [btn("Refresh status", f"order_refresh:{plan_key}", "success")],
            [btn("Back to menu",   "back_main", "primary")],
        ]}

        # Step 1: show "refreshing" immediately
        api("editMessageText",
            chat_id=chat_id,
            message_id=msg_id,
            text=(
                f"<b>Order status</b>\n\n"
                f"<b>Order ID:</b> <code>{order_id}</code>\n\n"
                f"♻️ <i>Refreshing...</i>"
            ),
            parse_mode="HTML",
            reply_markup=kb_order
        )
        answer_cb(cb_id, show_alert=False)

        # Step 2: wait 1 second, then show real status
        time.sleep(1)
        updated_at = datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
        api("editMessageText",
            chat_id=chat_id,
            message_id=msg_id,
            text=(
                "<b>Order status</b>\n\n"
                f"<b>Order ID:</b> <code>{order_id}</code>\n"
                f"<b>Plan:</b> {plan['label']}\n"
                f"<b>Amount:</b> ${plan['price_usd']}\n"
                f"<b>Account:</b> {uname_str}  <code>{user_id}</code>\n\n"
                f"<b>Status:</b>  ⏳ Processing\n\n"
                f"<i>Last updated: {updated_at}</i>"
            ),
            parse_mode="HTML",
            reply_markup=kb_order
        )
        return

    # Support
    if data == "support":
        clear_state(user_id)
        set_state(user_id, "support:waiting")
        result = send(chat_id,
            "<b>Support</b>\n\n"
            "Describe your issue and send it as the next message.",
            reply_markup=kb_cancel()
        )
        delete_msg(chat_id, msg_id)
        prompt_id = result.get("result", {}).get("message_id")
        set_data(user_id, {"prompt_msg_id": prompt_id})
        return

    if data == "send_ticket":
        store     = get_data(user_id)
        ticket    = store.get("ticket_text", "")
        ticket_id = store.get("ticket_id", gen_ticket_id())
        full_name = " ".join(filter(None, [
            user.get("first_name", ""), user.get("last_name", "")
        ]))
        username = user.get("username", "")

        send(ADMIN_ID,
            f"<b>New support ticket</b>  <code>{ticket_id}</code>\n\n"
            f"From: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"ID: <code>{user_id}</code>  |  @{username or 'none'}\n\n"
            f"<blockquote>{ticket}</blockquote>"
        )
        clear_state(user_id)
        replace(chat_id, msg_id,
            f"<b>Ticket created</b>\n\n"
            f"Your ticket ID: <code>{ticket_id}</code>\n\n"
            "The admin will reply shortly. "
            "Replies arrive in this chat from the bot.",
            reply_markup=kb_back()
        )
        return
