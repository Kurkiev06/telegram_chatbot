from email import message
import telebot
from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot

# list of storages, you can use any storage
from telebot.asyncio_storage import StateMemoryStorage

# new feature for states.
from telebot.asyncio_handler_backends import State, StatesGroup

import configparser
import json
import asyncio
import time 

#get token from config.ini
config= configparser.ConfigParser()
config.read(r'./config.ini')
token = config['teleCfg']['token']
bot = AsyncTeleBot(token, state_storage=StateMemoryStorage())

#get projects info from json
data = {}
with open("projectsData.json") as read_file:
    data = json.load(read_file)


class MyStates(StatesGroup):
    name = State() # statesgroup should contain states


def get_projects_from_data():
    keyboard = telebot.types.InlineKeyboardMarkup()
    projects = list(data.keys())
    for project in projects:
        button = telebot.types.InlineKeyboardButton(project, callback_data="project:" + project)
        keyboard.row(button)   
    return keyboard

def get_tasks_from_project(project):
    keyboard = telebot.types.InlineKeyboardMarkup()
    tasks = list(data[project].keys())
    for task in tasks:
        button = telebot.types.InlineKeyboardButton(task, callback_data="task:" + project + ":" + task)
        keyboard.row(button)   
    return keyboard

# start info
@bot.message_handler(commands=['start'])
async def start(message):
    await bot.send_message(message.chat.id, 'Бот предназначен для учёта графика работы сотрудников.\nGitHub проекта - https://github.com/Kurkiev06/telegramChatbot')
    await bot.send_message(message.chat.id, 'Для просмотра возможностей напишите /help')

# help info
@bot.message_handler(commands=['help'])
async def help(message):
    await bot.send_message(message.chat.id, 'Помощь будет скоро!')

# get all time info
@bot.message_handler(commands=['worktime'])
async def worktime(message):
    result = ""
    for project in data:
        for task in data[project]:
            for name in data[project][task]:
                sec = data[project][task][name]["time"]
                ty_res = time.gmtime(sec)
                nowTime = time.strftime("%H:%M:%S", ty_res)
                result += name + ' проработал ' + str(nowTime) + '\n'
    await bot.send_message(message.chat.id, result)

# choose project
@bot.message_handler(commands=['project'])
async def get_projects(message):
    keyboard = get_projects_from_data()
    await bot.send_message(message.chat.id, "Выберите проект", reply_markup=keyboard)
    
# choose task
@bot.callback_query_handler(func=lambda call: call.data.startswith('project'))
async def callback_project(call):
    project = call.data.split(':')[1]
    if project not in data or len(list(data[project].keys())) == 0:
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
    
    if project not in data or task not in data[project]:
        await bot.answer_callback_query(call.id, "Список заданий пуст")

    await bot.set_state(call.from_user.id, MyStates.name, call.message.chat.id)
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as info:
        info['project'] = project
        info['task'] = task
    await bot.send_message(call.message.chat.id, text="Введите своё Имя")

# enter name    
@bot.message_handler(state=MyStates.name)
async def get_name(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    button = telebot.types.InlineKeyboardButton("Начать", callback_data="Начать")
    keyboard.row(button) 
    button = telebot.types.InlineKeyboardButton("Закончить", callback_data="Закончить")
    keyboard.row(button) 
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as info:
        info['name'] = message.text
    await bot.send_message(message.chat.id, "Начать/Закончить", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data in ["Начать", "Закончить"])
async def callback_task(call):
    async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as info:
        name = info["name"]
        task = info["task"]
        project = info["project"]
        if name not in data[project][task]:
            data[project][task][name] = {"start": 0, "time": 0}

        if call.data == "Начать":            
            data[project][task][name]["start"] = int(time.time())
        else:
            if data[project][task][name]["start"] != 0:
                data[project][task][name]["time"] += int(time.time()) - data[project][task][name]["start"]
        sec = data[project][task][name]["time"]
    ty_res = time.gmtime(sec)
    nowTime = time.strftime("%H:%M:%S",ty_res)
    await bot.send_message(call.message.chat.id, "Операция выполнена успешна, вы проработали: " + str(nowTime))


@bot.message_handler(content_types=['text'])
async def get_text_messages(message):
    await bot.send_message(message.chat.id, "Для помощи напишите /help.")

bot.add_custom_filter(asyncio_filters.StateFilter(bot))

'''
{
    "programming": {"learn python": {"kok": {"start": 0, "time": 0}}, "learn assembler": {}, "find job": {}}, 
    "chatting": {"find freind": {}, "write a message": {}}
}
'''