from aiogram.fsm.state import State, StatesGroup


class FSMCreateAssistant(StatesGroup):
    fill_assistant_name = State()
    fill_assistant_instrustion = State()
    upload_assistant_file = State()


class FSMDeleteAssistant(StatesGroup):
    enter_assistant_number = State()
    confirm_del_action = State()


class FSMActivateAssistant(StatesGroup):
    activate_assistant = State()
    use_assistant = State()
