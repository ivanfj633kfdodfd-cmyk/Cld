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

from config import BOT_TOKEN, ADMIN_ID, PLANS, WALLETS
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
        [{"text": "My Profile", "callback_data": "profile",
          "thumbnail_url": "https://raw.githubusercontent.com/ivanfj633kfdodfd-cmyk/Cld/main/Claude_3-7_illustration.png"}],
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
    "<b>Claude Pro — subscription via crypto</b>\n\n"
    "Get full access to Claude AI: Sonnet 5, Opus 5, Haiku — all models, "
    "no usage caps, Claude Code, Projects, and more."
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


def plans_text() -> str:
    rows = []
    for key, plan in PLANS.items():
        badge = f"  [{plan['badge']}]" if plan.get("badge") else ""
        rows.append(f"{plan['label']}  —  ${plan['price_usd']}/mo{badge}")

    listing = "\n".join(rows)
    return (
        "<b>Claude — plans and pricing</b>\n\n"
        "<pre>"
        f"{listing}"
        "</pre>\n\n"
        "<i>Official plans · claude.com/pricing</i>\n\n"
        "Select a plan:"
    )


def plan_detail_text(plan_key: str) -> str:
    plan   = PLANS[plan_key]
    feats  = "\n".join(f"  {f}" for f in plan["features"])
    saving = f"\n<b>Saving:</b> {plan['saving']}" if plan["saving"] else ""
    return (
        f"<b>{plan['label']}</b>\n"
        f"<b>Price:</b> ${plan['price_usd']} total "
        f"(${plan['per_month']}/month){saving}\n\n"
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
            send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main_inline())
            send(chat_id, plans_text(), reply_markup=kb_plans())
            return

        if param == "profile":
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

        # Default start — remove any old reply keyboard, send welcome
        send(chat_id, "\u200b", reply_markup={"remove_keyboard": True})
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

        text = (
            "<b>My Profile</b>\n\n"
            f"<b>Name:</b> {full_name}\n"
            f"<b>Username:</b> {uname_str}\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Language:</b> {lang}\n\n"
            "<b>Subscription</b>\n"
            "<blockquote>"
            "No active subscription.\n"
            "Tap Subscribe to get full access to Claude Pro."
            "</blockquote>\n\n"
            "<b>Access level:</b> Free plan\n"
            "<b>Models available:</b> —\n"
            "<b>Claude Code:</b> —\n"
            "<b>Usage limit:</b> 0 messages"
        )
        replace(chat_id, msg_id, text, reply_markup=kb_back())
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
