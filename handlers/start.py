import os
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from keyboards import kb_main
from handlers.utils import replace_message_photo, replace_message_text

router = Router()

# File ID баннера — после первой отправки замените на реальный file_id
# для экономии трафика. Пока берём из env, можно оставить URL или file_id.
BANNER = os.getenv("BANNER_FILE_ID", "https://i.imgur.com/4M34hi2.png")

WELCOME_TEXT = (
    "<b>Claude AI — подписка с доступом к Sonnet 4.5 / Opus 4</b>\n\n"
    "Пользуйтесь самыми мощными моделями без ограничений прямо в Telegram.\n\n"
    "◾ Неограниченные сообщения\n"
    "◾ Web-приложение с историей чатов\n"
    "◾ Оплата криптовалютой — анонимно\n"
    "◾ Доступ активируется вручную в течение 30 минут\n\n"
    "👇 Выберите действие:"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer_photo(
        photo=BANNER,
        caption=WELCOME_TEXT,
        reply_markup=kb_main(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "back_main")
async def back_main(query: CallbackQuery) -> None:
    await query.answer()
    await replace_message_photo(
        query,
        photo=BANNER,
        caption=WELCOME_TEXT,
        reply_markup=kb_main(),
    )


@router.callback_query(lambda c: c.data == "about")
async def about(query: CallbackQuery) -> None:
    await query.answer()
    text = (
        "<b>ℹ️ О сервисе</b>\n\n"
        "Этот бот позволяет оформить подписку на Claude AI и получить "
        "доступ к нему через встроенное Web-приложение прямо в Telegram.\n\n"
        "<b>Как это работает:</b>\n"
        "1. Выберите тариф и валюту\n"
        "2. Переведите сумму на указанный адрес\n"
        "3. Нажмите «Я оплатил» — мы получим уведомление\n"
        "4. В течение 30 минут вам откроют доступ вручную\n\n"
        "<b>Поддержка:</b> кнопка «🆘 Помощь» → создать тикет"
    )
    await replace_message_text(query, text, reply_markup=kb_main())
