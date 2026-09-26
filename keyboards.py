from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import PLANS, WALLETS


# ── Welcome keyboard ───────────────────────────────────────────────────────────
def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Оформить подписку",
                callback_data="subscribe"
            )
        ],
        [
            InlineKeyboardButton(text="💬 Открыть чат", callback_data="open_chat"),
            InlineKeyboardButton(text="ℹ️ О сервисе",   callback_data="about"),
        ],
        [
            InlineKeyboardButton(text="🆘 Помощь", callback_data="support")
        ],
    ])


# ── Plans keyboard ─────────────────────────────────────────────────────────────
def kb_plans() -> InlineKeyboardMarkup:
    rows = []
    for key, plan in PLANS.items():
        badge = plan.get("badge", "")
        label = f"{plan['emoji']} {plan['label']} — ${plan['price_usd']}"
        if badge:
            label += f"  {badge}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan:{key}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Currency keyboard ──────────────────────────────────────────────────────────
def kb_currencies(plan_key: str) -> InlineKeyboardMarkup:
    keys = list(WALLETS.keys())
    rows = []
    # two per row
    for i in range(0, len(keys), 2):
        chunk = keys[i:i + 2]
        row = [
            InlineKeyboardButton(
                text=f"{WALLETS[c]['emoji']} {c}",
                callback_data=f"pay:{plan_key}:{c}"
            )
            for c in chunk
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="subscribe")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Requisites keyboard ────────────────────────────────────────────────────────
def kb_paid(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{plan_key}")],
        [InlineKeyboardButton(text="◀️ Сменить валюту", callback_data=f"plan:{plan_key}")],
        [InlineKeyboardButton(text="🏠 Главная",        callback_data="back_main")],
    ])


# ── Support keyboard ───────────────────────────────────────────────────────────
def kb_support_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")]
    ])


def kb_ticket_send() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Отправить тикет", callback_data="send_ticket")],
        [InlineKeyboardButton(text="✏️ Переписать",      callback_data="support")],
        [InlineKeyboardButton(text="❌ Отмена",           callback_data="back_main")],
    ])


# ── Back to main ──────────────────────────────────────────────────────────────
def kb_back_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="back_main")]
    ])
