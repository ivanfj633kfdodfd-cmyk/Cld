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

import httpx

from config import BOT_TOKEN, ADMIN_ID, PLANS, WALLETS
from fsm_store import get_state, set_state, get_data, set_data, clear_state

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
log = logging.getLogger(__name__)


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


# ── Button helpers ─────────────────────────────────────────────────────────────

def btn(text: str, cb: str, style: str | None = None) -> dict:
    b: dict = {"text": text, "callback_data": cb}
    if style:
        b["style"] = style
    return b


def btn_webapp(text: str, url: str) -> dict:
    return {"text": text, "web_app": {"url": url}}


# ── Keyboards ──────────────────────────────────────────────────────────────────

def kb_main() -> dict:
    return {"inline_keyboard": [
        [btn("Subscribe", "subscribe", "success")],
        [
            btn("Open chat",  "open_chat", "primary"),
            btn("About",      "about"),
        ],
        [btn("Support", "support")],
    ]}


def kb_plans() -> dict:
    rows = []
    for key, plan in PLANS.items():
        label = plan["label"]
        price = f"${plan['price_usd']}"
        badge = f"  {plan['badge']}" if plan.get("badge") else ""
        rows.append([btn(f"{label} — {price}{badge}", f"plan:{key}", "primary")])
    rows.append([btn("Back", "back_main")])
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
        [btn("Main menu", "back_main")],
    ]}


def kb_back() -> dict:
    return {"inline_keyboard": [[btn("Main menu", "back_main")]]}


def kb_cancel() -> dict:
    return {"inline_keyboard": [[btn("Cancel", "back_main", "danger")]]}


def kb_ticket() -> dict:
    return {"inline_keyboard": [
        [btn("Send ticket", "send_ticket", "success")],
        [btn("Rewrite",     "support")],
        [btn("Cancel",      "back_main", "danger")],
    ]}


def kb_webapp_open() -> dict:
    host = os.getenv("WEBHOOK_HOST", "https://cld-mu.vercel.app")
    return {"inline_keyboard": [
        [btn_webapp("Open Claude chat", f"{host}/webapp")],
        [btn("Back", "back_main")],
    ]}


# ── Static texts ───────────────────────────────────────────────────────────────

BANNER = os.getenv("BANNER_FILE_ID", "https://i.imgur.com/4M34hi2.png")

WELCOME = (
    "<b>Claude Pro — subscription via crypto</b>\n\n"
    "Get full access to Claude AI: Sonnet, Opus, Haiku — all models, "
    "no usage caps, Claude Code, Projects, and more.\n\n"
    "Access is activated manually within 30 minutes after payment."
)

ABOUT = (
    "<b>About this service</b>\n\n"
    "We provide Claude Pro subscriptions paid anonymously via cryptocurrency.\n\n"
    "<b>How it works</b>\n"
    "1. Choose a plan\n"
    "2. Select a payment currency\n"
    "3. Send the exact amount to the wallet address shown\n"
    "4. Tap \"I have paid\" — we get notified instantly\n"
    "5. Access is activated within 30 minutes\n\n"
    "<b>Plans are based on official claude.com pricing.</b>\n"
    "For help, use the Support button."
)


def plans_text() -> str:
    """Price table using monospaced code block for alignment."""
    lines = [
        "<b>Claude Pro — plans and pricing</b>",
        "",
        "Based on the official Claude Pro plan ($20/month).",
        "Multi-month packs include a discount.",
        "",
        "<blockquote>",
        "<code>Plan          Price    Per mo   Saving</code>",
        "<code>────────────────────────────────────────</code>",
    ]
    for key, plan in PLANS.items():
        label   = plan["label"].replace("Claude Pro — ", "").ljust(13)
        price   = f"${plan['price_usd']}".ljust(8)
        per_mo  = f"${plan['per_month']}/mo".ljust(8)
        saving  = plan["saving"] or "—"
        lines.append(f"<code>{label} {price} {per_mo} {saving}</code>")
    lines.append("</blockquote>")
    lines.append("")
    lines.append("Select a plan:")
    return "\n".join(lines)


def plan_detail_text(plan_key: str) -> str:
    plan = PLANS[plan_key]
    feats = "\n".join(f"  {f}" for f in plan["features"])
    saving = f"\n<b>Saving:</b> {plan['saving']}" if plan["saving"] else ""
    return (
        f"<b>{plan['label']}</b>\n"
        f"<b>Price:</b> ${plan['price_usd']} total"
        f" (${plan['per_month']}/month){saving}\n\n"
        f"<b>Includes:</b>\n{feats}\n\n"
        "Select payment currency:"
    )


def requisites_text(plan_key: str, currency: str) -> str:
    plan   = PLANS[plan_key]
    wallet = WALLETS[currency]
    return (
        f"<b>Payment details</b>\n\n"
        f"<b>Plan:</b> {plan['label']}\n"
        f"<b>Amount:</b> <b>${plan['price_usd']}</b> in {currency}\n"
        f"<b>Network:</b> {wallet['network']}\n\n"
        f"<b>Wallet address:</b>\n"
        f"<code>{wallet['address']}</code>\n\n"
        "<blockquote>Send only via the network shown above.\n"
        "Transfers on a different network will not be credited.</blockquote>\n\n"
        "After sending, tap <b>\"I have paid\"</b>."
    )


# ── Update router ──────────────────────────────────────────────────────────────

def handle_update(data: dict) -> None:
    if "message" in data:
        _handle_message(data["message"])
    elif "callback_query" in data:
        _handle_callback(data["callback_query"])


# ── Message handler ────────────────────────────────────────────────────────────

def _handle_message(msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text    = msg.get("text", "")

    if text == "/start":
        clear_state(user_id)
        send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main())
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

    # FSM: ticket text input
    if get_state(user_id) == "support:waiting":
        store = get_data(user_id)
        set_data(user_id, {**store, "ticket_text": text})
        set_state(user_id, "support:confirm")

        if store.get("prompt_msg_id"):
            delete_msg(chat_id, store["prompt_msg_id"])
        delete_msg(chat_id, msg["message_id"])

        preview = send(
            chat_id,
            f"<b>Ticket preview:</b>\n\n<blockquote>{text}</blockquote>\n\nLooks good?",
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

    if data == "open_chat":
        replace(chat_id, msg_id,
            "<b>Claude Web App</b>\n\n"
            "Chat interface with conversation history.\n"
            "An active subscription is required to send messages.",
            reply_markup=kb_webapp_open()
        )
        return

    # Subscription flow
    if data == "subscribe":
        replace(chat_id, msg_id, plans_text(), reply_markup=kb_plans())
        return

    if data.startswith("plan:"):
        plan_key = data.split(":", 1)[1]
        replace(chat_id, msg_id,
            plan_detail_text(plan_key),
            reply_markup=kb_currencies(plan_key)
        )
        return

    if data.startswith("pay:"):
        _, plan_key, currency = data.split(":", 2)
        replace(chat_id, msg_id,
            requisites_text(plan_key, currency),
            reply_markup=kb_paid(plan_key)
        )
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
        replace(chat_id, msg_id,
            "<b>Request received</b>\n\n"
            f"Plan: <b>{plan['label']}</b>\n\n"
            "The admin has been notified. "
            "Access will be activated within <b>30 minutes</b>.\n\n"
            "If it takes longer, please open a support ticket.",
            reply_markup=kb_back()
        )
        return

    # Support
    if data == "support":
        clear_state(user_id)
        set_state(user_id, "support:waiting")
        result    = send(chat_id,
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
        full_name = " ".join(filter(None, [
            user.get("first_name", ""), user.get("last_name", "")
        ]))
        username = user.get("username", "")

        send(ADMIN_ID,
            f"<b>New support ticket</b>\n\n"
            f"From: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"ID: <code>{user_id}</code>  |  @{username or 'none'}\n\n"
            f"<blockquote>{ticket}</blockquote>"
        )
        clear_state(user_id)
        replace(chat_id, msg_id,
            "<b>Ticket sent</b>\n\n"
            "The admin will reply shortly. "
            "Replies arrive in this chat from the bot.",
            reply_markup=kb_back()
        )
        return
