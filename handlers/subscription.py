from aiogram import Router
from aiogram.types import CallbackQuery

from config import PLANS, WALLETS, ADMIN_ID
from keyboards import kb_plans, kb_currencies, kb_paid, kb_back_main
from handlers.utils import replace_message_text

router = Router()


# ── Step 1: Show plans ─────────────────────────────────────────────────────────
@router.callback_query(lambda c: c.data == "subscribe")
async def show_plans(query: CallbackQuery) -> None:
    await query.answer()

    lines = ["<b>💳 Выберите тариф</b>\n"]
    for key, plan in PLANS.items():
        badge = f"  <b>{plan.get('badge', '')}</b>" if plan.get("badge") else ""
        lines.append(
            f"{plan['emoji']} <b>{plan['label']}</b> — <b>${plan['price_usd']}</b>{badge}\n"
            f"   <i>{plan['desc']}</i>\n"
        )

    await replace_message_text(
        query,
        "\n".join(lines),
        reply_markup=kb_plans(),
    )


# ── Step 2: Plan chosen → show currencies ─────────────────────────────────────
@router.callback_query(lambda c: c.data.startswith("plan:"))
async def choose_currency(query: CallbackQuery) -> None:
    await query.answer()
    plan_key = query.data.split(":", 1)[1]
    plan = PLANS[plan_key]

    text = (
        f"<b>{plan['emoji']} {plan['label']} — ${plan['price_usd']}</b>\n"
        f"<i>{plan['desc']}</i>\n\n"
        "<b>💱 Выберите валюту оплаты:</b>\n\n"
        "Все популярные сети — TRON, Ethereum, Bitcoin, Solana, BNB, TON."
    )
    await replace_message_text(
        query,
        text,
        reply_markup=kb_currencies(plan_key),
    )


# ── Step 3: Currency chosen → show requisites ─────────────────────────────────
@router.callback_query(lambda c: c.data.startswith("pay:"))
async def show_requisites(query: CallbackQuery) -> None:
    await query.answer()
    _, plan_key, currency = query.data.split(":", 2)

    plan = PLANS[plan_key]
    wallet = WALLETS[currency]

    text = (
        f"<b>📋 Реквизиты для оплаты</b>\n\n"
        f"<b>Тариф:</b> {plan['emoji']} {plan['label']}\n"
        f"<b>Сумма:</b> <b>${plan['price_usd']}</b> в {currency}\n"
        f"<b>Сеть:</b> {wallet['network']}\n\n"
        f"<b>Адрес кошелька:</b>\n"
        f"<code>{wallet['address']}</code>\n\n"
        "⚠️ <b>Важно:</b> переводите строго в указанной сети.\n"
        "Перевод в другой сети <b>не зачтётся</b>.\n\n"
        "После оплаты нажмите <b>«✅ Я оплатил»</b> — "
        "мы получим уведомление и активируем доступ в течение 30 минут."
    )
    await replace_message_text(
        query,
        text,
        reply_markup=kb_paid(plan_key),
    )


# ── Step 4: User claims payment ────────────────────────────────────────────────
@router.callback_query(lambda c: c.data.startswith("paid:"))
async def payment_claimed(query: CallbackQuery) -> None:
    await query.answer("Уведомление отправлено!", show_alert=True)
    plan_key = query.data.split(":", 1)[1]
    plan = PLANS[plan_key]
    user = query.from_user

    # Notify admin
    admin_text = (
        f"💰 <b>Заявка на оплату</b>\n\n"
        f"👤 Пользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📛 Username: @{user.username or '—'}\n\n"
        f"📦 Тариф: {plan['emoji']} {plan['label']} — ${plan['price_usd']}\n\n"
        f"Проверь транзакцию и выдай доступ вручную."
    )
    await query.bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")

    # Confirm to user
    await replace_message_text(
        query,
        (
            "<b>✅ Заявка принята!</b>\n\n"
            f"Тариф: {plan['emoji']} <b>{plan['label']}</b>\n\n"
            "Мы получили уведомление об оплате.\n"
            "Доступ будет активирован вручную в течение <b>30 минут</b>.\n\n"
            "Если прошло больше времени — создайте тикет через «🆘 Помощь»."
        ),
        reply_markup=kb_back_main(),
    )


# ── Open chat (web app) ────────────────────────────────────────────────────────
@router.callback_query(lambda c: c.data == "open_chat")
async def open_chat(query: CallbackQuery) -> None:
    await query.answer()
    import os
    webapp_url = os.getenv("WEBHOOK_HOST", "") + "/webapp"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Открыть чат Claude",
            web_app=WebAppInfo(url=webapp_url)
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])
    await replace_message_text(
        query,
        (
            "<b>💬 Claude Web App</b>\n\n"
            "Открывает встроенный чат с историей диалогов.\n"
            "Без активной подписки доступ ограничен."
        ),
        reply_markup=kb,
    )
