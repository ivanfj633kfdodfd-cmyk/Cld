from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from keyboards import kb_support_cancel, kb_ticket_send, kb_back_main
from handlers.utils import replace_message_text, safe_delete

router = Router()


class TicketForm(StatesGroup):
    waiting_for_text = State()
    waiting_for_confirm = State()


# ── Open support ───────────────────────────────────────────────────────────────
@router.callback_query(lambda c: c.data == "support")
async def support_start(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.clear()

    msg = await replace_message_text(
        query,
        (
            "<b>🆘 Поддержка</b>\n\n"
            "Напишите ваш вопрос или описание проблемы.\n"
            "Сообщение будет отправлено администратору.\n\n"
            "<i>Просто отправьте текст следующим сообщением 👇</i>"
        ),
        reply_markup=kb_support_cancel(),
    )
    await state.update_data(prompt_msg_id=msg.message_id)
    await state.set_state(TicketForm.waiting_for_text)


# ── Receive ticket text ────────────────────────────────────────────────────────
@router.message(TicketForm.waiting_for_text, F.text)
async def receive_ticket(message: Message, state: FSMContext) -> None:
    data = await state.get_data()

    # Delete the bot's prompt message
    await safe_delete(message.bot, message.chat.id, data.get("prompt_msg_id", 0))
    # Delete user's message too (keep chat clean)
    await safe_delete(message.bot, message.chat.id, message.message_id)

    await state.update_data(ticket_text=message.text)
    await state.set_state(TicketForm.waiting_for_confirm)

    preview = await message.answer(
        (
            "<b>📝 Предпросмотр тикета:</b>\n\n"
            f"<blockquote>{message.text}</blockquote>\n\n"
            "Всё верно? Отправить?"
        ),
        reply_markup=kb_ticket_send(),
        parse_mode="HTML",
    )
    await state.update_data(preview_msg_id=preview.message_id)


# ── Send ticket ────────────────────────────────────────────────────────────────
@router.callback_query(lambda c: c.data == "send_ticket")
async def send_ticket(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    data = await state.get_data()
    ticket_text = data.get("ticket_text", "")
    user = query.from_user

    admin_msg = (
        f"📩 <b>Новый тикет</b>\n\n"
        f"👤 <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
        f"🆔 <code>{user.id}</code>  |  @{user.username or '—'}\n\n"
        f"<blockquote>{ticket_text}</blockquote>"
    )
    await query.bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")

    await state.clear()

    await replace_message_text(
        query,
        (
            "<b>✅ Тикет отправлен!</b>\n\n"
            "Администратор ответит вам в ближайшее время.\n"
            "Ответ придёт в этот чат от имени бота."
        ),
        reply_markup=kb_back_main(),
    )


# ── Admin reply to user ────────────────────────────────────────────────────────
# Usage: admin sends /reply <user_id> <text>
@router.message(F.text.startswith("/reply"))
async def admin_reply(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.answer("Формат: /reply <user_id> <текст>")
        return
    try:
        target_id = int(parts[1])
        reply_text = parts[2]
        await message.bot.send_message(
            target_id,
            f"<b>💬 Ответ поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML",
        )
        await message.answer("✅ Ответ отправлен.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
