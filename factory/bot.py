import logging
import os
import time
from pprint import pprint

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from openai import OpenAI
from states import FSMActivateAssistant, FSMCreateAssistant, FSMDeleteAssistant

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(name)s:%(levelname)s:%(message)s"
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("aiogram.dispatcher").setLevel(logging.ERROR)
logging.getLogger("aiogram.event").setLevel(logging.ERROR)

BOT_TOKEN = os.environ.get("FACTORY_BOT_TOKEN")
OPENAI_TOKEN = os.environ.get("OPENAI_TOKEN")

WORK_DIR = os.path.abspath(os.path.dirname(__file__))

finish_states = [
    "requires_action",
    "cancelling",
    "cancelled",
    "failed",
    "completed",
    "expired",
]

client = OpenAI(api_key=OPENAI_TOKEN)

storage = MemoryStorage()
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart(), StateFilter(default_state))
async def process_start_command(message: Message) -> None:
    """
    Handles the /start command for the Telegram bot.

    Sends a welcome message introducing the bot's purpose of demonstrating the creation
    of OpenAI assistants.

    Args:
        message (Message): The incoming message object.

    Returns:
        None
    """
    await message.answer(
        text="Это бот демонстрирует создание OpenAI ассистентов\n\n"
        "Чтобы перейти к созданию ассистента - "
        "отправьте команду /newassistant"
    )


@dp.message(Command(commands="cancel"), StateFilter(default_state))
async def process_cancel_command(message: Message) -> None:
    """
    Handles the /cancel command for the bot.

    Sends a message indicating that there's nothing to cancel and provides guidance on
    creating an assistant.

    Args:
        message (Message): The incoming message object.

    Returns:
        None
    """
    await message.answer(
        text="Отменять нечего.\n\n"
        "Чтобы перейти к созданию ассистента - "
        "отправьте команду /newassistant"
    )


@dp.message(Command(commands="cancel"), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext) -> None:
    """
    Handles the /cancel command when the bot is in a non-default state.

    Notifies the user about exiting the state machine and provides guidance on starting
    over.

    Args:
        message (Message): The incoming message object.
        state (FSMContext): The current state of the finite state machine.

    Returns:
        None
    """
    await message.answer(
        text="Вы вышли из машины состояний\n\n"
        "Чтобы снова перейти к заполнению анкеты - "
        "отправьте команду /newassistant"
    )

    await state.clear()


@dp.message(Command(commands="assistants"), StateFilter(default_state))
async def process_assistants_command(message: Message) -> None:
    """
    Handles the /assistants command to list user-specific assistants.

    Retrieves and displays a list of assistants associated with the user's Telegram ID.

    Args:
        message (Message): The incoming message object.

    Returns:
        None
    """
    my_assistants = []
    telegram_user_id = message.from_user.id
    assistants = client.beta.assistants.list()
    data = assistants.data
    for assistant in data:
        metadata = assistant.metadata
        if "client_id" in metadata:
            try:
                client_id = int(metadata["client_id"])
            except ValueError:
                client_id = 0
            if client_id == telegram_user_id:
                my_assistants.append({"id": assistant.id, "name": assistant.name})

    if my_assistants:
        text = ""
        for i, assistant in enumerate(my_assistants, start=1):
            text += f"{i}. {assistant['name']}\n"
        await message.answer(text=text)
    else:
        await message.answer(
            text="У вас нет асисстентов. Чтобы создать, введите команду /newassistant"
        )


@dp.message(Command(commands="startassistant"), StateFilter(default_state))
async def process_startassistant_command(message: Message, state: FSMContext) -> None:
    """
    Handles the /startassistant command to initiate interaction with a specific
    assistant.

    Retrieves the user's assistants and prompts the user to choose an assistant to
    interact with.

    Args:
        message (Message): The incoming message object.
        state (FSMContext): The current state of the finite state machine.

    Returns:
        None
    """
    my_assistants = []
    telegram_user_id = message.from_user.id
    assistants = client.beta.assistants.list()
    data = assistants.data
    for assistant in data:
        metadata = assistant.metadata
        if "client_id" in metadata:
            try:
                client_id = int(metadata["client_id"])
            except ValueError:
                client_id = 0
            if client_id == telegram_user_id:
                my_assistants.append({"id": assistant.id, "name": assistant.name})

    if my_assistants:
        await state.update_data(assistants=my_assistants)
        text = ""
        for i, assistant in enumerate(my_assistants, start=1):
            text += f"{i}. {assistant['name']}\n"
        await message.answer(text="Вот список ваших асисстентов: ")
        await message.answer(text=text)
        await message.answer("Введите номер ассистента, с которым хотите пообщаться:")
        await state.set_state(FSMActivateAssistant.activate_assistant)
    else:
        await message.answer(
            text="У вас нет асисстентов. Чтобы создать, введите команду /newassistant"
        )
        await state.clear()


@dp.message(
    StateFilter(FSMActivateAssistant.activate_assistant),
    lambda x: x.text.isdigit() and int(x.text) >= 0,
)
async def process_activate_assistant_number_sent(
    message: Message, state: FSMContext
) -> None:
    """
    Processes the assistant number sent by the user to activate a specific assistant.

    Retrieves the selected assistant based on the provided number and initiates
    communication with it.

    Args:
        message (Message): The incoming message object.
        state (FSMContext): The current state of the finite state machine.

    Returns:
        None
    """
    assistant_idx = int(message.text) - 1
    data = await state.get_data()
    assistants = data["assistants"]
    if len(assistants) <= assistant_idx:
        await message.answer(text="Ассистента с указанным номером не существует.")
    else:
        assistant = assistants[assistant_idx]
        await state.update_data(assistant_id=assistant["id"])

    if assistant:
        thread = client.beta.threads.create()
        await state.update_data(thread_id=thread.id)

        await message.answer(
            text="Можете начинать общение с асисстентом.\n\n"
            "Чтобы закончить общение, введите команду /stopassistant"
        )

        await state.set_state(FSMActivateAssistant.use_assistant)


# use_assistant
@dp.message(StateFilter(FSMActivateAssistant.use_assistant))
async def proccess_assistant_conversation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    thread_id = data["thread_id"]
    assistant_id = data["assistant_id"]

    client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=message.text
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id
    )

    keep_retrieving_status = None
    await message.answer("Минуту... пишу ответ")
    while keep_retrieving_status not in finish_states:
        keep_retrieving_run = client.beta.threads.runs.retrieve(
            thread_id=data["thread_id"], run_id=run.id
        )
        keep_retrieving_status = keep_retrieving_run.status
        logging.info(f"openai api request status): {keep_retrieving_status}")

        if keep_retrieving_status == "completed":
            break
        time.sleep(3)

    if keep_retrieving_status != "completed":
        logging.ERROR(f"got unexpected openai status: {keep_retrieving_status}")
        await message.answer(text="Ой... что-то пошло не так :(")

    all_messages = client.beta.threads.messages.list(thread_id=data["thread_id"])
    pprint(all_messages)
    gpt_response = all_messages.data[0].content[0].text.value
    await message.answer(gpt_response)


@dp.message(
    Command(commands="stopassistant"), StateFilter(FSMActivateAssistant.use_assistant)
)
async def process_cancel_assistant_conversation_state(
    message: Message, state: FSMContext
) -> None:
    await message.answer(
        text="Вы прервали общение с асисстентом\n\n"
        "Чтобы снова перейти к общению - "
        "отправьте команду /startassistant"
    )
    await state.clear()


# Этот хэндлер будет срабатывать на команду /delassistant, выводить
# список асисстентов пользователя и переводить в состояние ожидания ввода номера
# ассистента для удаления
@dp.message(Command(commands="delassistant"), StateFilter(default_state))
async def process_delassistant_command(message: Message, state: FSMContext) -> None:
    my_assistants = []
    telegram_user_id = message.from_user.id
    assistants = client.beta.assistants.list()
    data = assistants.data
    for assistant in data:
        metadata = assistant.metadata
        if "client_id" in metadata:
            try:
                client_id = int(metadata["client_id"])
            except ValueError:
                client_id = 0
            if client_id == telegram_user_id:
                my_assistants.append({"id": assistant.id, "name": assistant.name})

    if my_assistants:
        await state.update_data(assistants=my_assistants)
        text = ""
        for i, assistant in enumerate(my_assistants, start=1):
            text += f"{i}. {assistant['name']}\n"
        await message.answer(text="Вот список ваших асисстентов: ")
        await message.answer(text=text)
        await message.answer("Введите номер ассистента, которого хотите удалить:")
        await state.set_state(FSMDeleteAssistant.enter_assistant_number)
    else:
        await message.answer(
            text="У вас нет асисстентов. Чтобы создать, введите команду /newassistant"
        )
        await state.clear()


# Это хэндлер будет срабатывать, если введен корректный номер ассистента
# и запрашивать подтверждение на его удаление
@dp.message(
    StateFilter(FSMDeleteAssistant.enter_assistant_number),
    lambda x: x.text.isdigit() and int(x.text) >= 0,
)
async def process_assistant_number_sent(message: Message, state: FSMContext) -> None:
    assistant_idx = int(message.text) - 1
    data = await state.get_data()
    assistants = data["assistants"]
    if len(assistants) <= assistant_idx:
        await message.answer(text="Ассистента с указанным номером не существует.")
    else:
        assistant = assistants[assistant_idx]
        await state.update_data(assistant_id_to_delete=assistant["id"])

        yes_button = InlineKeyboardButton(text="Да", callback_data="yes")
        no_button = InlineKeyboardButton(text="Нет", callback_data="no")
        keyboard: list[list[InlineKeyboardButton]] = [[yes_button, no_button]]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(
            text=f"Вы действительно хотите удалить ассистента \"{assistant['name']}\"?",
            reply_markup=markup,
        )

        await state.set_state(FSMDeleteAssistant.confirm_del_action)


# Это хэндлер будет срабатывать на подтверждение удаления ассистента
# и выводить из машины состояний
@dp.callback_query(
    StateFilter(FSMDeleteAssistant.confirm_del_action), F.data.in_(["yes", "no"])
)
async def process_assistant_delete_confirm_press(
    callback: CallbackQuery, state: FSMContext
) -> None:
    if callback.data == "yes":
        data = await state.get_data()
        assistant_id = data["assistant_id_to_delete"]
        client.beta.assistants.delete(assistant_id=assistant_id)
        await callback.message.edit_text(text="Асисстент успешно удален!")
    else:
        await callback.message.edit_text(text="Удаление ассистента отменено!")
    await state.clear()


# Этот хэнтдер будет срабатывать на команду /newassistant
# и переводить в состояние ожидания ввода имени ассистента
@dp.message(
    Command(commands="newassistant"),
    StateFilter(default_state),
)
async def process_newassistant_command(message: Message, state: FSMContext) -> None:
    await message.answer(text="Пожалуйста введите имя ассистента")
    # Устанавливаем состояние ожидание ввода названия ассистента
    await state.set_state(FSMCreateAssistant.fill_assistant_name)


# Этот хэндлер будет срабатывать, если введено корректное имя
# и переводить в состояние ожидания ввода инструкции
@dp.message(StateFilter(FSMCreateAssistant.fill_assistant_name))
async def process_assistant_name_sent(message: Message, state: FSMContext) -> None:
    # Сохраняем введенное имя в хранилище по ключу "assistant_name"
    await state.update_data(assistant_name=message.text)
    await message.answer(
        text="Спасибо!\n\n А теперь введите текст инструкции для ассистента"
    )
    # Устанавливаем состояние ожидания ввода инструкции
    await state.set_state(FSMCreateAssistant.fill_assistant_instrustion)


# Это хэндлер будет срабатывать, если введена корректная инструкция
# и запрашивает загрузку файла
@dp.message(StateFilter(FSMCreateAssistant.fill_assistant_instrustion))
async def process_assistant_instruction_sent(
    message: Message, state: FSMContext
) -> None:
    # Сохраняем инструкцию в хранилище по ключу "assistant_instruction"
    await state.update_data(assistant_instruction=message.text)
    await message.answer(text="Загрузите файл базы знаний")
    await state.set_state(FSMCreateAssistant.upload_assistant_file)


# Этот хэндлер будет срабатывать, после загрузки файла
# и выводить из машины состояний
@dp.message(StateFilter(FSMCreateAssistant.upload_assistant_file))
async def process_assistant_file_upload(message: Message, state: FSMContext) -> None:
    file_ids = []
    document = message.document
    if document and document.file_size > 0:
        file_path = f"{WORK_DIR}//{document.file_name}"
        await bot.download(document, file_path)
        await state.update_data(file=file_path)
        file = client.files.create(file=open(file_path, "rb"), purpose="assistants")
        file_ids.append(file.id)
        await message.answer("Отлично! Файл загружен.")
    await message.answer(text="Приступаю к созданию ассистента...")

    data = await state.get_data()

    assistant = client.beta.assistants.create(
        name=data["assistant_name"],
        instructions=data["assistant_instruction"],
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}],
        metadata={"client_id": message.from_user.id},
        file_ids=file_ids,
    )

    pprint(assistant)

    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о завершении процесса
    await message.answer(text="Спасибо! Ваш ассистен создан!")


# Этот хэндлер будет срабатывать на любые сообщения, кроме тех
# для которых есть отдельные хэндлеры, вне состояний
@dp.message(StateFilter(default_state))
async def send_echo(message: Message) -> None:
    await message.reply(text="Извините, моя твоя не понимать")


if __name__ == "__main__":
    dp.run_polling(bot)
