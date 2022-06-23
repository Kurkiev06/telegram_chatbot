from telebot import asyncio_filters
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Message
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup

import configparser
import time

from data_manager import ProjectsDataManager, UsersDataManager, CallbackDataManager

# Get token from config.ini
config = configparser.ConfigParser()
config.read(r'./config.ini')
token = config['teleCfg']['token']
password = config['teleCfg']['password']
bot = AsyncTeleBot(token, state_storage=StateMemoryStorage())

# Get dict from json
projects_manager = ProjectsDataManager()
users_manager = UsersDataManager()
callback_hasher = CallbackDataManager()


class MyStates(StatesGroup):
    unauthorized = State()
    name = State()
    add_project = State()
    add_task = State()
    project_name = State()
    worktime = State()
    message = State()


# Convert seconds to conviniant time
def convert_seconds(sec) -> str:
    ty_res = time.gmtime(sec)
    return time.strftime("%H:%M:%S", ty_res)


async def send_greetings(chat_id):
    await bot.send_message(chat_id, 'Добро пожаловать!\n\
    Бот предназначен для учёта графика работы сотрудников.\n\
    GitHub проекта - https://github.com/Kurkiev06/telegramChatbot')
    await bot.send_message(chat_id, 'Для просмотра возможностей \
    напишите /help')


# Decorator for all actions that require authorization
def authorization_required(func):
    async def is_user_authorized(user_id, chat_id):
        user_data = users_manager.data.get(str(user_id), {})
        is_authorized = user_data.get("authorized", False)
        if not is_authorized:
            await bot.set_state(user_id, MyStates.unauthorized, chat_id)
            await bot.send_message(chat_id, "Вы не авторизованы. Пожалуйста, введите пароль.")
            return False
        return True

    def wrapper(*args, **kwargs):
        if isinstance(args[0], Message):
            message = args[0]
        else:
            message = args[0].message

        user_id = message.from_user.id
        chat_id = message.chat.id
        if is_user_authorized(user_id=user_id, chat_id=chat_id):
            return func(*args, **kwargs)

    return wrapper


# Provide authorization
@bot.message_handler(state=MyStates.unauthorized)
async def handle_authorization(message):
    if message.text == password:
        users_manager.update_json(message.from_user.id, "authorized", True)
        await bot.delete_state(message.from_user.id, message.chat.id)
        await send_greetings(message.chat.id)
    else:
        await bot.send_message(message.chat.id, "Неправильный пароль. Повторите ввод.")


# Start info
@authorization_required
@bot.message_handler(commands=['start'])
async def start(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await send_greetings(message.chat.id)


# Help info
@authorization_required
@bot.message_handler(commands=['help'])
async def help(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, '''
/help - помощь по командам
/start - общая информация
/addproject - добавить проект
/addtask - добавить задание
/deleteentry - удалить проект/задание/вклад сотрудника
/worktime - посмотреть затраченное на задачу время
/projectworktime - посмотреть вклад сотрудников в проект
/project - выбрать задачу и Начать/Закончить работу
/logout - отозвать авторизацию аккаунта в боте
''')


# get all time info
@authorization_required
@bot.message_handler(commands=['worktime'])
async def worktime(message):
    await bot.set_state(message.from_user.id, MyStates.worktime,
                        message.chat.id)
    await bot.send_message(message.chat.id, "Введите имя сотрудника, \
чтобы посмотреть время работы над задачами")


# Get info about worker
@authorization_required
@bot.message_handler(state=MyStates.worktime)
async def worktime(message):
    workerName = message.text
    workerNameSplit = {names for names in workerName.lower().split()}
    result = workerName + ":\n"
    for project in projects_manager.data:
        for task in projects_manager.data[project]:
            for name in projects_manager.data[project][task]:
                nameSplit = {names for names in name.lower().split()}
                if nameSplit == workerNameSplit:
                    nowTime = convert_seconds(
                        projects_manager.data[project][task][name]["time"])
                    result += f"Проработал \"{nowTime}\" над \
задачей \"{task}\" проекта \"{project}\"\n"
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, result)


# Watch project work time
@authorization_required
@bot.message_handler(commands=['projectworktime'])
async def project_worktime(message):
    keyboard = get_projects_from_data(callback_postfix='project_worktime')
    await bot.send_message(message.chat.id, "Выберите проект", reply_markup=keyboard)


# Add new project
@authorization_required
@bot.message_handler(commands=['addproject'])
async def add_project(message):
    await bot.send_message(message.chat.id, "Введите название проекта")
    await bot.set_state(message.from_user.id,
                        MyStates.add_project,
                        message.chat.id)


# Add new task to project
@authorization_required
@bot.message_handler(commands=['addtask'])
async def add_task(message):
    await bot.send_message(message.chat.id,
                           "Введите название проекта, куда добавить задание")
    await bot.set_state(message.from_user.id,
                        MyStates.project_name,
                        message.chat.id)


def get_projects_from_data(callback_postfix='') -> InlineKeyboardMarkup():
    keyboard = InlineKeyboardMarkup()
    projects = list(projects_manager.data.keys())
    for project in projects:
        callback_data = callback_hasher.get_hash_by_data(f"project:{project}:{callback_postfix}")
        button = InlineKeyboardButton(project,
                                      callback_data=callback_data)
        keyboard.row(button)
    return keyboard


# Choose project
@authorization_required
@bot.message_handler(commands=['project'])
async def get_projects(message):
    keyboard = get_projects_from_data()
    await bot.delete_state(message.from_user.id,
                           message.chat.id)
    await bot.send_message(message.chat.id,
                           "Выберите проект",
                           reply_markup=keyboard)


@authorization_required
@bot.message_handler(commands=['deleteentry'])
async def delete_entry(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton('Проект', callback_data=callback_hasher.get_hash_by_data("delete_project")),
        InlineKeyboardButton('Задача', callback_data=callback_hasher.get_hash_by_data("delete_task")),
    )
    keyboard.row(InlineKeyboardButton('Вклад сотрудника',
                                      callback_data=callback_hasher.get_hash_by_data("delete_name")))

    await bot.send_message(message.chat.id,
                           "Выберите тип объекта для удаления",
                           reply_markup=keyboard)


# Choose Start or Finish
@authorization_required
@bot.callback_query_handler(
    func=lambda call: callback_hasher.get_data_by_hash(call.data) in ["delete_project", "delete_task", "delete_name"])
async def delete_entry_set_state(call):
    keyboard = get_projects_from_data(callback_postfix=callback_hasher.get_data_by_hash(call.data))
    await bot.edit_message_text("Выберите проект", call.message.chat.id, call.message.id, reply_markup=keyboard)


# Get project name and request task name
@authorization_required
@bot.message_handler(state=MyStates.project_name)
async def get_project_name(message):
    project = message.text
    await bot.set_state(message.from_user.id,
                        MyStates.add_task,
                        message.chat.id)
    async with bot.retrieve_data(message.from_user.id,
                                 message.chat.id) as info:
        info['project'] = project
    await bot.send_message(message.chat.id, "Введите название задания")


# Get task name
@authorization_required
@bot.message_handler(state=MyStates.add_task)
async def get_task_name(message):
    async with bot.retrieve_data(message.from_user.id,
                                 message.chat.id) as info:
        project = info['project']
    task = message.text
    projects_manager.update_json(project, task)
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id,
                           f"Задание \"{task}\" успешно добавлено в \"{project}\"!")


# Get project name
@authorization_required
@bot.message_handler(state=MyStates.add_project)
async def get_project_name(message):
    project = message.text
    projects_manager.update_json(project)
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id,
                           f"Проект \"{project}\" успешно добавлен!")


# Choose project
@authorization_required
@bot.callback_query_handler(func=lambda call: callback_hasher.get_data_by_hash(call.data).startswith('project'))
async def callback_project(call):
    def get_tasks_from_project(project, callback_postfix='') -> InlineKeyboardMarkup():
        keyboard = InlineKeyboardMarkup()
        tasks = list(projects_manager.data[project].keys())
        for task in tasks:
            button = InlineKeyboardButton(
                task,
                callback_data=callback_hasher.get_hash_by_data(f"task:{project}:{task}:{callback_postfix}"))
            keyboard.row(button)
        return keyboard

    def get_project_names_and_worktime(project):

        tasks = list(projects_manager.data[project].keys())
        names = {}
        for task in tasks:
            for name in projects_manager.data[project][task].keys():
                time = projects_manager.data[project][task][name].get("time", 0)
                names[name] = names.get(name, 0) + time

        if not names:
            text = f'Нет рабочего времени для проекта \"{project}\"'
        else:
            text = f'Вклад сотрудников в проект \"{project}\":\n' + \
               '\n'.join(f'{name.title()}: {convert_seconds(worktime)}' for name, worktime in names.items())

        return text

    call_data = callback_hasher.get_data_by_hash(call.data).split(':')
    project = call_data[1]
    callback_postfix = call_data[-1] if len(call_data) == 3 else ''

    keyboard = ReplyKeyboardMarkup()

    if project not in projects_manager.data:
        edit_text = f"В данных нет проекта \"{project}\""

    elif callback_postfix == 'delete_project':
        del projects_manager.data[project]
        projects_manager.write_json()

        [callback_hasher.clear_hash(callback_hasher.get_hash_by_data(f"project:{project}{postfix}"))
         for postfix in ['', ':delete_project', ':delete_task', ':delete_name']]

        edit_text = f"Проект \"{project}\" успешно удалён!"

    elif callback_postfix == 'project_worktime':
        edit_text = get_project_names_and_worktime(project)

    else:
        if len(list(projects_manager.data[project].keys())) == 0:
            edit_text = f"Список заданий проекта \"{project}\" пуст"

        else:
            edit_text = "Выберите задание"
            keyboard = get_tasks_from_project(project, callback_postfix)

    await bot.edit_message_text(chat_id=call.message.chat.id,
                                text=edit_text,
                                message_id=call.message.id,
                                reply_markup=keyboard)


# Choose task
@authorization_required
@bot.callback_query_handler(func=lambda call: callback_hasher.get_data_by_hash(call.data).startswith('task'))
async def callback_task(call):
    def get_names_from_task(project, task, callback_postfix='') -> InlineKeyboardMarkup():
        keyboard = InlineKeyboardMarkup()
        names = list(projects_manager.data[project][task].keys())
        for name in names:
            button = InlineKeyboardButton(
                name,
                callback_data=callback_hasher.get_hash_by_data(f"name:{project}:{task}:{name}:{callback_postfix}"))
            keyboard.row(button)
        return keyboard


    callback_data = callback_hasher.get_data_by_hash(call.data).split(':')
    project = callback_data[1]
    task = callback_data[2]
    callback_postfix = callback_data[-1] if len(callback_data) == 4 else ''

    edit_text = None
    keyboard = ReplyKeyboardMarkup()

    if project not in projects_manager.data or task not in projects_manager.data[project]:
        edit_text = "Не найден проект или задача."

    elif callback_postfix == 'delete_task':
        del projects_manager.data[project][task]
        projects_manager.write_json()

        [callback_hasher.clear_hash(callback_hasher.get_hash_by_data(f"task:{project}:{task}{postfix}"))
         for postfix in ['', ':delete_task', ':delete_name']]

        edit_text = f"Задача \"{task}\" из проекта \"{project}\" успешно удалена!"

    elif callback_postfix == 'delete_name':
        if len(list(projects_manager.data[project][task].keys())) == 0:
            edit_text = f"Список исполнителей задачи \"{task}\" в проекте \"{project}\" пуст"
        else:
            edit_text = "Выберите исполнителя"
            keyboard = get_names_from_task(project, task, callback_postfix)

    if edit_text:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=edit_text,
            message_id=call.message.id,
            reply_markup=keyboard)
        return

    await bot.set_state(call.from_user.id, MyStates.name, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id,
                                 call.message.chat.id) as info:
        info['project'] = project
        info['task'] = task
    await bot.send_message(call.message.chat.id, text="Введите своё имя")


@authorization_required
@bot.callback_query_handler(func=lambda call: callback_hasher.get_data_by_hash(call.data).endswith('delete_name'))
async def callback_delete_name(call):

    callback_data = callback_hasher.get_data_by_hash(call.data).split(':')
    project = callback_data[1]
    task = callback_data[2]
    name = callback_data[3]

    if project not in projects_manager.data or task not in projects_manager.data[project] or name not in projects_manager.data[project][task]:
        edit_text = "Не найден: проект, задача или сотрудник."

    else:
        del projects_manager.data[project][task][name]
        projects_manager.write_json()

        [callback_hasher.clear_hash(callback_hasher.get_hash_by_data(f"name:{project}:{task}:{name}{postfix}"))
         for postfix in ['', ':delete_name']]

        edit_text = f"Вклад сотрудника \"{name.title()}\" в задачу \"{task}\" из проекта \"{project}\" успешно удалён!"

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        text=edit_text,
        message_id=call.message.id,
        reply_markup=ReplyKeyboardMarkup())
    return


# Get name
@authorization_required
@bot.message_handler(state=MyStates.name)
async def get_name(message):

    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Начать", callback_data=callback_hasher.get_hash_by_data("Начать"))
    keyboard.row(button)
    button = InlineKeyboardButton("Закончить", callback_data=callback_hasher.get_hash_by_data("Закончить"))
    keyboard.row(button)
    async with bot.retrieve_data(message.from_user.id,
                                 message.chat.id) as info:
        info['name'] = message.text
        project = info['project']
        task = info['task']
    await bot.set_state(message.from_user.id,
                        MyStates.message,
                        message.chat.id)
    await bot.send_message(message.chat.id,
                           f"Начать/Закончить \"{task}\" в \"{project}\"",
                           reply_markup=keyboard)


# Choose Start or Finish
@authorization_required
@bot.callback_query_handler(func=lambda call: callback_hasher.get_data_by_hash(call.data) in ["Начать", "Закончить"])
async def callback_task(call):

    async with bot.retrieve_data(call.from_user.id,
                                 call.message.chat.id) as info:
        name = info['name']
        name = name.lower()
        task = info['task']
        project = info['project']
        call_data = callback_hasher.get_data_by_hash(call.data)
        if name not in projects_manager.data[project][task]:
            projects_manager.update_json(project, task, name, {"start": 0, "time": 0})
        if call_data == "Начать":
            times = {"start": int(time.time()),
                     "time": projects_manager.data[project][task][name]["time"]}
            projects_manager.update_json(
                project,
                task,
                name,
                times)
        else:
            if projects_manager.data[project][task][name]["start"] != 0:
                nameDict = projects_manager.data[project][task][name]
                times = nameDict["time"] + int(time.time()) - nameDict["start"]
                projects_manager.update_json(
                    project,
                    task,
                    name,
                    {"start": nameDict["start"],
                     "time": times})
        nowTime = convert_seconds(projects_manager.data[project][task][name]["time"])
    await bot.send_message(
        call.message.chat.id,
        f"Операция выполнена успешно, вы проработали: \"{nowTime}\"")


# Log out
@authorization_required
@bot.message_handler(commands=['logout'])
async def start(message):

    users_manager.update_json(message.from_user.id, "authorized", False)
    await bot.set_state(message.from_user.id, MyStates.unauthorized, message.chat.id)
    await bot.send_message(message.chat.id, "Ваш аккаунт более не авторизован. Для продолжения работы введите пароль.")


# Handler for any stranger text
@authorization_required
@bot.message_handler(content_types=['text'])
async def get_text_messages(message):

    await bot.send_message(message.chat.id, "Для помощи напишите /help.")


# Register filter
bot.add_custom_filter(asyncio_filters.StateFilter(bot))
