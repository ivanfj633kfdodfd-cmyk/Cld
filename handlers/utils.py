"""
Helpers: safe delete + send so the chat never flickers empty.
Always send first, then delete the old message.
"""
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest


async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass


async def replace_message_text(
    query: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> Message:
    """Send a new message, THEN delete the old one."""
    new_msg = await query.message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    await safe_delete(query.bot, query.message.chat.id, query.message.message_id)
    return new_msg


async def replace_message_photo(
    query: CallbackQuery,
    photo: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> Message:
    """Send photo first, then delete old message."""
    new_msg = await query.message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    await safe_delete(query.bot, query.message.chat.id, query.message.message_id)
    return new_msg
