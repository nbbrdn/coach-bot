import logging
import re

import config
import external
from aiogram import F, Router, flags
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.chat_action import ChatActionMiddleware
from db.orm import (
    count_referrals,
    count_users,
    has_referrer,
    is_registered,
    save_message,
    update_referrer,
)

logger = logging.getLogger(__name__)

router = Router()
router.message.middleware(ChatActionMiddleware())

threads = {}


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    hasref = await has_referrer(user_id)

    if " " in message.text and not hasref:
        referrer_candidate = message.text.split()[1]
        try:
            referrer_candidate = int(referrer_candidate)
            registred = await is_registered(referrer_candidate)
            if user_id != referrer_candidate and registred:
                await update_referrer(user_id, referrer_candidate)
        except ValueError:
            pass

    kb = [
        [KeyboardButton(text="Давай разберем случайный кейс")],
        [KeyboardButton(text="Предложи список из 10 случайных кейсов")],
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Укажите способ выбора кейса",
    )

    await message.answer(
        ("Вы хотите выбрать кейс из предложенного списка, или выбрать случайный?"),
        reply_markup=keyboard,
    )


@router.message(Command("ref"))
async def cmd_ref(message: Message):
    await message.answer(
        "Вот ваша ссылка для приглашения новых пользователей: "
        f"{config.BOT_URL}?start={message.from_user.id}"
    )


@router.message(Command("refstat"))
async def cmd_refstat(message: Message):
    user_id = message.from_user.id
    referrals_cnt = await count_referrals(user_id)
    await message.answer(
        f"Зарегистрировано пользователей по вашей реферальной ссылке: {referrals_cnt}"
    )


@router.message(Command("stat"))
async def cmd_stat(message: Message):
    users_cnt = await count_users()
    await message.answer(f"Всего зарегистрированных пользователей: {users_cnt}")


@router.message(F.text)
@flags.chat_action(ChatAction.TYPING)
async def message_with_text(message: Message):
    user_id = message.from_user.id
    thread_id = threads.get(user_id, None)

    if not thread_id:
        thread_id = await external.create_thread()
        threads[user_id] = thread_id

    prompt = message.text
    # logging.info(f"user (id={user_id}): {prompt}")
    await save_message(user_id, prompt, True)

    message = await message.answer(
        "✍️ минутку, пишу ответ ...", reply_markup=ReplyKeyboardRemove()
    )

    text = await external.generate_text(prompt, thread_id)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)

    await message.delete()

    await message.answer(text)
    await save_message(user_id, text, False)
    # logging.info(f"bot (id={user_id}): {text}")
