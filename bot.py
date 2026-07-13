"""
Бот: подписка на ТГ-канал → ссылка на мануал.

1. Пользователь пишет /start
2. Если не подписан — просим подписаться
3. Если подписан — выдаём ссылку на мануал
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "").strip()
MANUAL_URL = os.getenv("MANUAL_URL", "").strip()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("manual-bot")


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        }
    except Exception as e:
        logger.warning("Ошибка проверки подписки user_id=%s: %s", user_id, e)
        return False


def subscribe_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ Я подписался — получить мануал", callback_data="check")],
        ]
    )


def manual_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📘 Открыть мануал", url=MANUAL_URL)],
        ]
    )


async def cmd_start(message: Message, bot: Bot) -> None:
    name = message.from_user.full_name

    if not await is_subscribed(bot, message.from_user.id):
        await message.answer(
            f"👋 Привет, <b>{name}</b>!\n\n"
            "Чтобы получить ссылку на мануал, подпишись на наш канал.\n\n"
            "1. Нажми «Подписаться на канал»\n"
            "2. Подпишись\n"
            "3. Нажми «Я подписался — получить мануал»",
            reply_markup=subscribe_kb(),
        )
        return

    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        "✅ Подписка есть — вот ссылка на мануал:",
        reply_markup=manual_kb(),
    )


async def check_sub(callback: CallbackQuery, bot: Bot) -> None:
    if not await is_subscribed(bot, callback.from_user.id):
        await callback.answer("Ты ещё не подписан на канал 😕", show_alert=True)
        try:
            await callback.message.edit_text(
                "⛔ Подписка не найдена.\n\n"
                "Подпишись на канал и нажми кнопку ещё раз.",
                reply_markup=subscribe_kb(),
            )
        except Exception:
            await callback.message.answer(
                "⛔ Подписка не найдена.\n\n"
                "Подпишись на канал и нажми кнопку ещё раз.",
                reply_markup=subscribe_kb(),
            )
        return

    await callback.answer("Готово! ✅")
    text = (
        "🎉 <b>Спасибо за подписку!</b>\n\n"
        "Вот ссылка на мануал:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=manual_kb())
    except Exception:
        await callback.message.answer(text, reply_markup=manual_kb())


async def any_message(message: Message, bot: Bot) -> None:
    """Любое другое сообщение — снова проверяем подписку."""
    if not await is_subscribed(bot, message.from_user.id):
        await message.answer(
            "⛔ Чтобы получить мануал, нужно подписаться на канал.",
            reply_markup=subscribe_kb(),
        )
        return

    await message.answer(
        "✅ Подписка есть. Вот ссылка на мануал:",
        reply_markup=manual_kb(),
    )


def validate_config() -> None:
    missing = []
    if not BOT_TOKEN or BOT_TOKEN.startswith("123456"):
        missing.append("BOT_TOKEN")
    if not CHANNEL_ID or CHANNEL_ID in {"@your_channel", ""}:
        missing.append("CHANNEL_ID")
    if not CHANNEL_URL or "your_channel" in CHANNEL_URL:
        missing.append("CHANNEL_URL")
    if not MANUAL_URL or MANUAL_URL in {"https://example.com/manual", ""}:
        missing.append("MANUAL_URL")
    if missing:
        raise SystemExit(
            "Заполни .env (см. .env.example). Не задано: " + ", ".join(missing)
        )


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.message.register(cmd_start, CommandStart())
    dp.callback_query.register(check_sub, F.data == "check")
    dp.message.register(any_message)

    # Всё, что ниже — должно быть внутри main()
    me = await bot.get_me()
    logger.info("Бот %s запущен | Канал: %s", me.username, CHANNEL_ID)

    try:
        chat = await bot.get_chat(CHANNEL_ID)
        logger.info("Канал OK: %s", chat.title or CHANNEL_ID)
    except Exception as e:
        logger.error(
            "Не вижу канал %s. Добавь бота АДМИНОМ в канал. Ошибка: %s",
            CHANNEL_ID,
            e,
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())