from email import message
import telebot
from telebot import asyncio_filters
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.async_telebot import AsyncTeleBot

# list of storages, you can use any storage
from telebot.asyncio_storage import StateMemoryStorage

# new feature for states.
from telebot.asyncio_handler_backends import State, StatesGroup

import configparser
import time 

from DataManager import DataManager

#get token from config.ini
config= configparser.ConfigParser()
config.read(r'./config.ini')
token = config['teleCfg']['token']
bot = AsyncTeleBot(token, state_storage=StateMemoryStorage())

# get dict from json
elements = DataManager()


class MyStates(StatesGroup):
    name = State() # statesgroup should contain states
    addProject = State()
    addTask = State()
    projectName = State()
    worktime = State()
    message = State()


# start info
@bot.message_handler(commands=['start'])
async def start(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, 'Бот предназначен для учёта графика работы сотрудников.\nGitHub проекта - https://github.com/Kurkiev06/telegramChatbot')
    await bot.send_message(message.chat.id, 'Для просмотра возможностей напишите /help')

# help info
@bot.message_handler(commands=['help'])
async def help(message):
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, '''
/help - помощь по командам
/start - общая информация
/addproject - добавить проект
/addtask - добавить задание
/worktime - посмотреть затраченное на задачу время
/project - выбрать задачу и Начать/Закончить работу''')

# get all time info
@bot.message_handler(commands=['worktime'])
async def worktime(message):
    await bot.set_state(message.from_user.id, MyStates.worktime, message.chat.id)
    await bot.send_message(message.chat.id, "Введите Имя, чтобы посмотреть время работы над задачами")

@bot.message_handler(state=MyStates.worktime)
async def worktime(message):
    workerName = message.text
    workerNameSplit = {name for name in workerName.lower().split()}
    result = workerName + ":\n"
    for project in elements.data:
        for task in elements.data[project]:
            for name in elements.data[project][task]:
                nameSplit = {name for name in name.lower().split()}
                if nameSplit == workerNameSplit:
                    sec = elements.data[project][task][name]["time"]
                    ty_res = time.gmtime(sec)
                    nowTime = time.strftime("%H:%M:%S", ty_res)
                    result += f"Проработал {nowTime} над задачей {task} проекта {project}\n"
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, result)

# add new project
@bot.message_handler(commands=['addproject'])
async def addproject(message):
    await bot.send_message(message.chat.id, "Введите название проекта")
    await bot.set_state(message.from_user.id, MyStates.addProject, message.chat.id)

# add new task to project
@bot.message_handler(commands=['addtask'])
async def addproject(message):
    await bot.send_message(message.chat.id, "Введите название проекта, куда добавить задание")
    await bot.set_state(message.from_user.id, MyStates.projectName, message.chat.id)

# choose project
@bot.message_handler(commands=['project'])
async def get_projects(message):
    def get_projects_from_data() -> InlineKeyboardMarkup():
        keyboard = InlineKeyboardMarkup()
        projects = list(elements.data.keys())
        for project in projects:
            button = InlineKeyboardButton(project, callback_data=f"project:{project}")
            keyboard.row(button)   
        return keyboard

    keyboard = get_projects_from_data()
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, "Выберите проект", reply_markup=keyboard)

@bot.message_handler(state=MyStates.projectName)
async def get_name(message):
    project = message.text
    await bot.set_state(message.from_user.id, MyStates.addTask, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as info:
        info['project'] = project
    await bot.send_message(message.chat.id, "Введите название задания")

@bot.message_handler(state=MyStates.addTask)
async def get_name(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as info:
        project = info['project']
    task = message.text
    elements.updateJson(project, task)
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, f"Задание {task} успешно добавлено в {project}!")

@bot.message_handler(state=MyStates.addProject)
async def get_name(message):
    project = message.text
    elements.updateJson(project)
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, f"Проект {project} успешно добавлен!")
    
# choose task
@bot.callback_query_handler(func=lambda call: call.data.startswith('project'))
async def callback_project(call):
    def get_tasks_from_project(project) -> InlineKeyboardMarkup():
        keyboard = InlineKeyboardMarkup()
        tasks = list(elements.data[project].keys())
        for task in tasks:
            button = InlineKeyboardButton(task, callback_data=f"task:{project}:{task}")
            keyboard.row(button)   
        return keyboard

    project = call.data.split(':')[1]
    if project not in elements.data or len(list(elements.data[project].keys())) == 0:
        await bot.answer_callback_query(call.id, "Список заданий пуст")
    else:
        keyboard = get_tasks_from_project(project)
        await bot.edit_message_text(chat_id=call.message.chat.id, text="Выберите задание", message_id=call.message.id, reply_markup=keyboard)

# choose task
@bot.callback_query_handler(func=lambda call: call.data.startswith('task'))
async def callback_task(call):
    infoFromCallback = call.data.split(':')
    project = infoFromCallback[1]
    task = infoFromCallback[2]
    
    if project not in elements.data or task not in elements.data[project]:
        await bot.answer_callback_query(call.id, "Список заданий пуст")

    await bot.set_state(call.from_user.id, MyStates.name, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as info:
        info['project'] = project
        info['task'] = task
    await bot.send_message(call.message.chat.id, text="Введите своё Имя")

# enter name    
@bot.message_handler(state=MyStates.name)
async def get_name(message):
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Начать", callback_data="Начать")
    keyboard.row(button) 
    button = InlineKeyboardButton("Закончить", callback_data="Закончить")
    keyboard.row(button) 
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as info:
        info['name'] = message.text
        project = info['project']
        task = info['task']
    await bot.set_state(message.from_user.id, MyStates.message, message.chat.id)
    await bot.send_message(message.chat.id, f"Начать/Закончить {task} в {project}", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data in ["Начать", "Закончить"])
async def callback_task(call):
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as info:
        name = info['name']
        task = info['task']
        project = info['project']
        if name not in elements.data[project][task]:
            elements.updateJson(project, task, name, {"start": 0, "time": 0})
        
        if call.data == "Начать":            
            elements.updateJson(project, task, name,{"start": int(time.time()), "time": elements.data[project][task][name]["time"]})
        else:
            if elements.data[project][task][name]["start"] != 0:
                nameDict = elements.data[project][task][name]
                elements.updateJson(project, task, name, {"start": nameDict["start"], "time": nameDict["time"] + int(time.time()) - nameDict["start"]})
        
        sec = elements.data[project][task][name]["time"]
    ty_res = time.gmtime(sec)
    nowTime = time.strftime("%H:%M:%S",ty_res)
    await bot.send_message(call.message.chat.id, f"Операция выполнена успешна, вы проработали: {nowTime}")


@bot.message_handler(content_types=['text'])
async def get_text_messages(message):
    await bot.send_message(message.chat.id, "Для помощи напишите /help.")

# register filter
bot.add_custom_filter(asyncio_filters.StateFilter(bot))
