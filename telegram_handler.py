"""
Sync Telegram bot handler using httpx.
No aiogram, no asyncio — works reliably in Vercel serverless.

Button colors via Bot API 9.4 (style field):
  "success"  → green
  "danger"   → red
  "primary"  → blue/accent
  (no style) → default grey
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


def send(chat_id: int, text: str, reply_markup=None, parse_mode="HTML") -> dict:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", **payload)


def send_photo(chat_id: int, photo: str, caption: str, reply_markup=None, parse_mode="HTML") -> dict:
    payload = {"chat_id": chat_id, "photo": photo, "caption": caption, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendPhoto", **payload)


def delete_msg(chat_id: int, message_id: int) -> None:
    api("deleteMessage", chat_id=chat_id, message_id=message_id)


def answer_callback(callback_id: str, text: str = "", show_alert: bool = False) -> None:
    api("answerCallbackQuery", callback_query_id=callback_id, text=text, show_alert=show_alert)


def replace(chat_id: int, old_msg_id: int, text: str, reply_markup=None) -> dict:
    """Send new text message THEN delete old — no flicker."""
    result = send(chat_id, text, reply_markup=reply_markup)
    delete_msg(chat_id, old_msg_id)
    return result


def replace_photo(chat_id: int, old_msg_id: int, photo: str, caption: str, reply_markup=None) -> dict:
    """Send new photo THEN delete old — no flicker."""
    result = send_photo(chat_id, photo, caption, reply_markup=reply_markup)
    delete_msg(chat_id, old_msg_id)
    return result


# ── Button builder helper ──────────────────────────────────────────────────────
# style: "success" (green), "danger" (red), "primary" (blue), None (default)

def btn(text: str, callback_data: str, style: str | None = None) -> dict:
    b: dict = {"text": text, "callback_data": callback_data}
    if style:
        b["style"] = style
    return b


def btn_url(text: str, url: str, style: str | None = None) -> dict:
    b: dict = {"text": text, "url": url}
    if style:
        b["style"] = style
    return b


def btn_webapp(text: str, url: str) -> dict:
    return {"text": text, "web_app": {"url": url}}


# ── Keyboards ──────────────────────────────────────────────────────────────────

def kb_main():
    return {"inline_keyboard": [
        [btn("Оформить подписку", "subscribe", "success")],
        [
            btn("Открыть чат",  "open_chat", "primary"),
            btn("О сервисе",    "about"),
        ],
        [btn("Помощь", "support")],
    ]}


def kb_plans():
    rows = []
    for key, plan in PLANS.items():
        rows.append([btn(
            f"{plan['label']} — ${plan['price_usd']}",
            f"plan:{key}",
            "primary"
        )])
    rows.append([btn("Назад", "back_main")])
    return {"inline_keyboard": rows}


def kb_currencies(plan_key: str):
    keys = list(WALLETS.keys())
    rows = []
    for i in range(0, len(keys), 2):
        chunk = keys[i:i + 2]
        rows.append([btn(c, f"pay:{plan_key}:{c}") for c in chunk])
    rows.append([btn("Назад к тарифам", "subscribe")])
    return {"inline_keyboard": rows}


def kb_paid(plan_key: str):
    return {"inline_keyboard": [
        [btn("Я оплатил", f"paid:{plan_key}", "success")],
        [btn("Сменить валюту", f"plan:{plan_key}")],
        [btn("Главная",        "back_main")],
    ]}


def kb_back():
    return {"inline_keyboard": [[btn("Главная", "back_main")]]}


def kb_cancel():
    return {"inline_keyboard": [[btn("Отмена", "back_main", "danger")]]}


def kb_ticket():
    return {"inline_keyboard": [
        [btn("Отправить тикет", "send_ticket", "success")],
        [btn("Переписать",      "support")],
        [btn("Отмена",          "back_main", "danger")],
    ]}


def kb_webapp():
    webapp_url = os.getenv("WEBHOOK_HOST", "https://cld-mu.vercel.app") + "/webapp"
    return {"inline_keyboard": [
        [btn_webapp("Открыть чат Claude", webapp_url)],
        [btn("Назад", "back_main")],
    ]}


# ── Texts ──────────────────────────────────────────────────────────────────────

BANNER = os.getenv("BANNER_FILE_ID", "https://i.imgur.com/4M34hi2.png")

WELCOME = (
    "<b>Claude AI — подписка с доступом к Sonnet 4.5 / Opus 4</b>\n\n"
    "Пользуйтесь самыми мощными моделями без ограничений прямо в Telegram.\n\n"
    "◾ Неограниченные сообщения\n"
    "◾ Web-приложение с историей чатов\n"
    "◾ Оплата криптовалютой — анонимно\n"
    "◾ Доступ активируется вручную в течение 30 минут\n\n"
    "Выберите действие:"
)


def plans_text() -> str:
    """
    Прайс-лист в виде HTML-таблицы с выравниванием через моноширинный шрифт.
    Использует <blockquote> (Bot API 6.6+) и <code> для выравнивания колонок.
    """
    lines = [
        "<b>Тарифы Claude AI</b>\n",
        "<blockquote>",
        "<code>Период       Цена    Выгода</code>",
        "<code>─────────────────────────────</code>",
    ]

    savings = {
        "1_month":  "",
        "3_months": "−$10",
        "6_months": "−$30",
        "1_year":   "−$80",
    }

    for key, plan in PLANS.items():
        label  = plan["label"].ljust(12)
        price  = f"${plan['price_usd']}".ljust(7)
        saving = savings.get(key, "")
        badge  = f"  {plan.get('badge', '')}" if plan.get("badge") else ""
        lines.append(f"<code>{label} {price} {saving}</code>{badge}")

    lines.append("</blockquote>")
    lines.append("\nВыберите тариф:")
    return "\n".join(lines)


# ── Update router ──────────────────────────────────────────────────────────────

def handle_update(data: dict) -> None:
    if "message" in data:
        handle_message(data["message"])
    elif "callback_query" in data:
        handle_callback(data["callback_query"])


# ── Message handler ────────────────────────────────────────────────────────────

def handle_message(msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text    = msg.get("text", "")

    # /start
    if text == "/start":
        clear_state(user_id)
        send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main())
        return

    # Admin /reply <user_id> <text>
    if text.startswith("/reply") and user_id == ADMIN_ID:
        parts = text.split(" ", 2)
        if len(parts) < 3:
            send(chat_id, "Формат: /reply &lt;user_id&gt; &lt;текст&gt;")
            return
        try:
            target = int(parts[1])
            send(target, f"<b>Ответ поддержки:</b>\n\n{parts[2]}")
            send(chat_id, "Ответ отправлен.")
        except Exception as e:
            send(chat_id, f"Ошибка: {e}")
        return

    # FSM: waiting for ticket text
    if get_state(user_id) == "support:waiting":
        store = get_data(user_id)
        set_data(user_id, {**store, "ticket_text": text})
        set_state(user_id, "support:confirm")

        prompt_id = store.get("prompt_msg_id")
        if prompt_id:
            delete_msg(chat_id, prompt_id)
        delete_msg(chat_id, msg["message_id"])

        preview = send(
            chat_id,
            f"<b>Предпросмотр тикета:</b>\n\n<blockquote>{text}</blockquote>\n\nВсё верно? Отправить?",
            reply_markup=kb_ticket(),
        )
        new_id = preview.get("result", {}).get("message_id")
        set_data(user_id, {**get_data(user_id), "preview_msg_id": new_id})
        return


# ── Callback handler ───────────────────────────────────────────────────────────

def handle_callback(cb: dict) -> None:
    cb_id   = cb["id"]
    data    = cb.get("data", "")
    msg     = cb["message"]
    chat_id = msg["chat"]["id"]
    msg_id  = msg["message_id"]
    user    = cb["from"]
    user_id = user["id"]

    answer_callback(cb_id)

    # ── Main menu ──────────────────────────────────────────────────────────────
    if data == "back_main":
        clear_state(user_id)
        # Always: send first → delete after (no flicker)
        replace_photo(chat_id, msg_id, BANNER, WELCOME, reply_markup=kb_main())
        return

    if data == "about":
        replace(chat_id, msg_id,
            "<b>О сервисе</b>\n\n"
            "Этот бот позволяет оформить подписку на Claude AI.\n\n"
            "<b>Как это работает:</b>\n"
            "1. Выберите тариф и валюту\n"
            "2. Переведите сумму на указанный адрес\n"
            "3. Нажмите «Я оплатил» — мы получим уведомление\n"
            "4. В течение 30 минут доступ активируется вручную\n\n"
            "<b>Поддержка:</b> кнопка «Помощь»",
            reply_markup=kb_main()
        )
        return

    if data == "open_chat":
        replace(chat_id, msg_id,
            "<b>Claude Web App</b>\n\n"
            "Встроенный чат с историей диалогов.\n"
            "Без активной подписки доступ ограничен.",
            reply_markup=kb_webapp()
        )
        return

    # ── Subscription flow ──────────────────────────────────────────────────────
    if data == "subscribe":
        replace(chat_id, msg_id, plans_text(), reply_markup=kb_plans())
        return

    if data.startswith("plan:"):
        plan_key = data.split(":", 1)[1]
        plan = PLANS[plan_key]
        replace(chat_id, msg_id,
            f"<b>{plan['label']} — ${plan['price_usd']}</b>\n"
            f"<i>{plan['desc']}</i>\n\n"
            "<b>Выберите валюту оплаты:</b>",
            reply_markup=kb_currencies(plan_key)
        )
        return

    if data.startswith("pay:"):
        _, plan_key, currency = data.split(":", 2)
        plan   = PLANS[plan_key]
        wallet = WALLETS[currency]
        replace(chat_id, msg_id,
            f"<b>Реквизиты для оплаты</b>\n\n"
            f"<b>Тариф:</b> {plan['label']}\n"
            f"<b>Сумма:</b> <b>${plan['price_usd']}</b> в {currency}\n"
            f"<b>Сеть:</b> {wallet['network']}\n\n"
            f"<b>Адрес кошелька:</b>\n"
            f"<code>{wallet['address']}</code>\n\n"
            "<blockquote>⚠️ Переводите строго в указанной сети.\n"
            "Перевод в другую сеть не зачтётся.</blockquote>\n\n"
            "После оплаты нажмите <b>«Я оплатил»</b>.",
            reply_markup=kb_paid(plan_key)
        )
        return

    if data.startswith("paid:"):
        plan_key  = data.split(":", 1)[1]
        plan      = PLANS[plan_key]
        full_name = " ".join(filter(None, [user.get("first_name",""), user.get("last_name","")]))
        username  = user.get("username", "")

        send(ADMIN_ID,
            f"<b>Заявка на оплату</b>\n\n"
            f"👤 <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"🆔 <code>{user_id}</code>\n"
            f"📛 @{username or '—'}\n\n"
            f"📦 {plan['label']} — ${plan['price_usd']}\n\n"
            f"Проверь транзакцию и выдай доступ."
        )
        answer_callback(cb_id, "Уведомление отправлено!", show_alert=True)
        replace(chat_id, msg_id,
            "<b>Заявка принята!</b>\n\n"
            f"Тариф: <b>{plan['label']}</b>\n\n"
            "Доступ будет активирован в течение <b>30 минут</b>.\n"
            "Если прошло больше — напишите в «Помощь».",
            reply_markup=kb_back()
        )
        return

    # ── Support ────────────────────────────────────────────────────────────────
    if data == "support":
        clear_state(user_id)
        set_state(user_id, "support:waiting")
        result    = send(chat_id,
            "<b>Поддержка</b>\n\n"
            "Напишите ваш вопрос следующим сообщением 👇",
            reply_markup=kb_cancel()
        )
        delete_msg(chat_id, msg_id)
        prompt_id = result.get("result", {}).get("message_id")
        set_data(user_id, {"prompt_msg_id": prompt_id})
        return

    if data == "send_ticket":
        store     = get_data(user_id)
        ticket    = store.get("ticket_text", "")
        full_name = " ".join(filter(None, [user.get("first_name",""), user.get("last_name","")]))
        username  = user.get("username", "")

        send(ADMIN_ID,
            f"<b>Новый тикет</b>\n\n"
            f"👤 <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"🆔 <code>{user_id}</code>  |  @{username or '—'}\n\n"
            f"<blockquote>{ticket}</blockquote>"
        )
        clear_state(user_id)
        replace(chat_id, msg_id,
            "<b>Тикет отправлен!</b>\n\n"
            "Администратор ответит в ближайшее время.",
            reply_markup=kb_back()
        )
        return
