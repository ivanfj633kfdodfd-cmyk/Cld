"""
Sync Telegram bot handler using httpx.
No aiogram, no asyncio — works reliably in Vercel serverless.
"""
from __future__ import annotations

import logging
import os
from typing import Any

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
    """Send new message THEN delete old — no flicker."""
    result = send(chat_id, text, reply_markup=reply_markup)
    delete_msg(chat_id, old_msg_id)
    return result


# ── Keyboards ──────────────────────────────────────────────────────────────────

def kb_main():
    return {"inline_keyboard": [
        [{"text": "✅ Оформить подписку", "callback_data": "subscribe"}],
        [
            {"text": "💬 Открыть чат",  "callback_data": "open_chat"},
            {"text": "ℹ️ О сервисе",    "callback_data": "about"},
        ],
        [{"text": "🆘 Помощь", "callback_data": "support"}],
    ]}


def kb_plans():
    rows = []
    for key, plan in PLANS.items():
        badge = f"  {plan.get('badge', '')}" if plan.get("badge") else ""
        rows.append([{
            "text": f"{plan['emoji']} {plan['label']} — ${plan['price_usd']}{badge}",
            "callback_data": f"plan:{key}"
        }])
    rows.append([{"text": "◀️ Назад", "callback_data": "back_main"}])
    return {"inline_keyboard": rows}


def kb_currencies(plan_key: str):
    keys = list(WALLETS.keys())
    rows = []
    for i in range(0, len(keys), 2):
        chunk = keys[i:i + 2]
        rows.append([{
            "text": f"{WALLETS[c]['emoji']} {c}",
            "callback_data": f"pay:{plan_key}:{c}"
        } for c in chunk])
    rows.append([{"text": "◀️ Назад к тарифам", "callback_data": "subscribe"}])
    return {"inline_keyboard": rows}


def kb_paid(plan_key: str):
    return {"inline_keyboard": [
        [{"text": "✅ Я оплатил",        "callback_data": f"paid:{plan_key}"}],
        [{"text": "◀️ Сменить валюту",   "callback_data": f"plan:{plan_key}"}],
        [{"text": "🏠 Главная",           "callback_data": "back_main"}],
    ]}


def kb_back():
    return {"inline_keyboard": [[{"text": "🏠 Главная", "callback_data": "back_main"}]]}


def kb_cancel():
    return {"inline_keyboard": [[{"text": "❌ Отмена", "callback_data": "back_main"}]]}


def kb_ticket():
    return {"inline_keyboard": [
        [{"text": "📨 Отправить тикет", "callback_data": "send_ticket"}],
        [{"text": "✏️ Переписать",      "callback_data": "support"}],
        [{"text": "❌ Отмена",           "callback_data": "back_main"}],
    ]}


def kb_webapp():
    webapp_url = os.getenv("WEBHOOK_HOST", "https://cld-mu.vercel.app") + "/webapp"
    return {"inline_keyboard": [
        [{"text": "💬 Открыть чат Claude", "web_app": {"url": webapp_url}}],
        [{"text": "◀️ Назад", "callback_data": "back_main"}],
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
    "👇 Выберите действие:"
)


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
    text = msg.get("text", "")

    # /start
    if text == "/start":
        clear_state(user_id)
        send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main())
        return

    # Admin reply: /reply <user_id> <text>
    if text.startswith("/reply") and user_id == ADMIN_ID:
        parts = text.split(" ", 2)
        if len(parts) < 3:
            send(chat_id, "Формат: /reply &lt;user_id&gt; &lt;текст&gt;")
            return
        try:
            target = int(parts[1])
            send(target, f"<b>💬 Ответ поддержки:</b>\n\n{parts[2]}")
            send(chat_id, "✅ Ответ отправлен.")
        except Exception as e:
            send(chat_id, f"❌ Ошибка: {e}")
        return

    # FSM: waiting for ticket text
    if get_state(user_id) == "support:waiting":
        data_store = get_data(user_id)
        set_data(user_id, {**data_store, "ticket_text": text})
        set_state(user_id, "support:confirm")

        # Delete prompt msg
        prompt_id = data_store.get("prompt_msg_id")
        if prompt_id:
            delete_msg(chat_id, prompt_id)
        # Delete user message
        delete_msg(chat_id, msg["message_id"])

        preview = send(
            chat_id,
            f"<b>📝 Предпросмотр тикета:</b>\n\n<blockquote>{text}</blockquote>\n\nВсё верно? Отправить?",
            reply_markup=kb_ticket(),
        )
        set_data(user_id, {**get_data(user_id), "preview_msg_id": preview.get("result", {}).get("message_id")})
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

    # ── Main menu ──
    if data == "back_main":
        clear_state(user_id)
        send_photo(chat_id, BANNER, WELCOME, reply_markup=kb_main())
        delete_msg(chat_id, msg_id)
        return

    if data == "about":
        replace(chat_id, msg_id,
            "<b>ℹ️ О сервисе</b>\n\n"
            "Этот бот позволяет оформить подписку на Claude AI.\n\n"
            "<b>Как это работает:</b>\n"
            "1. Выберите тариф и валюту\n"
            "2. Переведите сумму на указанный адрес\n"
            "3. Нажмите «Я оплатил» — мы получим уведомление\n"
            "4. В течение 30 минут доступ активируется вручную\n\n"
            "<b>Поддержка:</b> кнопка «🆘 Помощь»",
            reply_markup=kb_main()
        )
        return

    if data == "open_chat":
        replace(chat_id, msg_id,
            "<b>💬 Claude Web App</b>\n\n"
            "Встроенный чат с историей диалогов.\n"
            "Без активной подписки доступ ограничен.",
            reply_markup=kb_webapp()
        )
        return

    # ── Subscription flow ──
    if data == "subscribe":
        lines = ["<b>💳 Выберите тариф</b>\n"]
        for key, plan in PLANS.items():
            badge = f"  <b>{plan.get('badge','')}</b>" if plan.get("badge") else ""
            lines.append(
                f"{plan['emoji']} <b>{plan['label']}</b> — <b>${plan['price_usd']}</b>{badge}\n"
                f"   <i>{plan['desc']}</i>\n"
            )
        replace(chat_id, msg_id, "\n".join(lines), reply_markup=kb_plans())
        return

    if data.startswith("plan:"):
        plan_key = data.split(":", 1)[1]
        plan = PLANS[plan_key]
        replace(chat_id, msg_id,
            f"<b>{plan['emoji']} {plan['label']} — ${plan['price_usd']}</b>\n"
            f"<i>{plan['desc']}</i>\n\n"
            "<b>💱 Выберите валюту оплаты:</b>",
            reply_markup=kb_currencies(plan_key)
        )
        return

    if data.startswith("pay:"):
        _, plan_key, currency = data.split(":", 2)
        plan   = PLANS[plan_key]
        wallet = WALLETS[currency]
        replace(chat_id, msg_id,
            f"<b>📋 Реквизиты для оплаты</b>\n\n"
            f"<b>Тариф:</b> {plan['emoji']} {plan['label']}\n"
            f"<b>Сумма:</b> <b>${plan['price_usd']}</b> в {currency}\n"
            f"<b>Сеть:</b> {wallet['network']}\n\n"
            f"<b>Адрес кошелька:</b>\n"
            f"<code>{wallet['address']}</code>\n\n"
            "⚠️ <b>Важно:</b> переводите строго в указанной сети.\n"
            "После оплаты нажмите <b>«✅ Я оплатил»</b>.",
            reply_markup=kb_paid(plan_key)
        )
        return

    if data.startswith("paid:"):
        plan_key = data.split(":", 1)[1]
        plan = PLANS[plan_key]
        full_name = " ".join(filter(None, [user.get("first_name",""), user.get("last_name","")]))
        username  = user.get("username", "")

        send(ADMIN_ID,
            f"💰 <b>Заявка на оплату</b>\n\n"
            f"👤 <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"🆔 <code>{user_id}</code>\n"
            f"📛 @{username or '—'}\n\n"
            f"📦 {plan['emoji']} {plan['label']} — ${plan['price_usd']}\n\n"
            f"Проверь транзакцию и выдай доступ."
        )
        answer_callback(cb_id, "Уведомление отправлено!", show_alert=True)
        replace(chat_id, msg_id,
            "<b>✅ Заявка принята!</b>\n\n"
            f"Тариф: {plan['emoji']} <b>{plan['label']}</b>\n\n"
            "Доступ будет активирован в течение <b>30 минут</b>.\n"
            "Если прошло больше — напишите в «🆘 Помощь».",
            reply_markup=kb_back()
        )
        return

    # ── Support ──
    if data == "support":
        clear_state(user_id)
        set_state(user_id, "support:waiting")
        result = send(chat_id,
            "<b>🆘 Поддержка</b>\n\n"
            "Напишите ваш вопрос следующим сообщением 👇",
            reply_markup=kb_cancel()
        )
        delete_msg(chat_id, msg_id)
        prompt_id = result.get("result", {}).get("message_id")
        set_data(user_id, {"prompt_msg_id": prompt_id})
        return

    if data == "send_ticket":
        store = get_data(user_id)
        ticket_text = store.get("ticket_text", "")
        full_name = " ".join(filter(None, [user.get("first_name",""), user.get("last_name","")]))
        username  = user.get("username", "")

        send(ADMIN_ID,
            f"📩 <b>Новый тикет</b>\n\n"
            f"👤 <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"🆔 <code>{user_id}</code>  |  @{username or '—'}\n\n"
            f"<blockquote>{ticket_text}</blockquote>"
        )
        clear_state(user_id)
        replace(chat_id, msg_id,
            "<b>✅ Тикет отправлен!</b>\n\n"
            "Администратор ответит в ближайшее время.",
            reply_markup=kb_back()
        )
        return
