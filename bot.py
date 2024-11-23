from collections import defaultdict

import gspread
import phonenumbers
from phonenumbers import NumberParseException

from telebot import types, TeleBot
from telebot.types import Message

from email_validator import validate_email, EmailNotValidError

import config  # Ваш файл с токеном бота и Google Sheets
from utils import get_credits
from bot_utils.anketa import Anketa
from bot_utils.user_status import UserStatus

BTN_RESTART = "🔄 Перезапуск"
BTN_SURVEY = "📝 Заполнить анкету"
BTN_CANCEL = "Отмена"

ankets = defaultdict(Anketa)

creds = get_credits()
client = gspread.authorize(creds)
sheet = client.open_by_key(config.SPREADSHEET_ID).sheet1
bot = TeleBot(config.TG_TOKEN)


@bot.message_handler(commands=['start'])
def welcome(message: Message):
    ankets[message.from_user.id].status = UserStatus.NEW_USER

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(BTN_SURVEY)
    btn2 = types.KeyboardButton(BTN_RESTART)
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id,
                     "Добро пожаловать, {0.first_name}!\nЯ - {1.first_name}, бот созданный чтобы быть подопытным кроликом.".format(
                         message.from_user, bot.get_me()),
                     parse_mode='html', reply_markup=markup)


@bot.message_handler(content_types=['text'])
def loco(message: Message):
    if message.chat.type == 'private':
        if message.text == BTN_RESTART:
            welcome(message)  # Используем функцию welcome для перезапуска
        # elif message.text == BTN_SURVEY:
        #     bot.send_message(message.chat.id, "Заполните анкету:", reply_markup=generate_anketa_markup())
        else:
            process_anketa(message)
        # else:
        #     bot.send_message(message.chat.id, 'Я не знаю что ответить 😢')


def generate_anketa_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton(BTN_CANCEL))
    return markup


def generate_yes_no_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton('Да'))
    markup.add(types.KeyboardButton('Нет'))
    return markup


@bot.message_handler(func=lambda message: message.text == BTN_CANCEL)
def cancel_anketa(message: Message):
    bot.send_message(message.chat.id, "Анкета отменена.")
    welcome(message)


def process_anketa(message: Message):
    anketa = ankets[message.from_user.id]
    print(anketa)
    match anketa.status:
        case UserStatus.NEW_USER:
            start_anketa(message)
        case UserStatus.INPUT_NAME:
            input_name(message)
        case UserStatus.INPUT_CITY:
            input_city(message)
        case UserStatus.INPUT_EMAIL:
            input_email(message)
        case UserStatus.INPUT_PHONE:
            input_phone(message)
        case UserStatus.INPUT_REPAIR_SKILLS:
            input_repair_skill(message)
        case UserStatus.INPUT_CLIENT_SKILLS:
            input_client_skill(message)
        case UserStatus.INPUT_SALARY:
            input_salary(message)
        case UserStatus.FINISHED:
            bot.send_message(message.chat.id, "Анкета сохранена")
        case _:
            ...



def start_anketa(message: Message):
    anketa = ankets[message.from_user.id]
    anketa.status = UserStatus.INPUT_NAME
    bot.send_message(message.chat.id, "Введите ФИО:")


def input_name(message: Message):
    anketa = ankets[message.from_user.id]
    anketa.fio = message.text.strip()
    if not anketa.fio:
        bot.send_message(message.chat.id, "Введите ФИО!")
        return
    anketa.status = UserStatus.INPUT_CITY
    bot.send_message(message.chat.id, "Введите город:")


def input_city(message: Message):
    anketa = ankets[message.from_user.id]
    anketa.city = message.text.strip()
    if not anketa.city:
        bot.send_message(message.chat.id, "Введите город!")
        return
    anketa.status = UserStatus.INPUT_EMAIL
    bot.send_message(message.chat.id, "Введите email:")


def input_email(message: Message):
    anketa = ankets[message.from_user.id]
    try:
        anketa.email = message.text.strip()
        if not anketa.email:
            bot.send_message(message.chat.id, "Введите корректный email!")
            return
        validate_email(anketa.email, check_deliverability=False)
    except EmailNotValidError as e:
        bot.send_message(message.chat.id, f"Некорректный email!")
        return
    anketa.status = UserStatus.INPUT_PHONE
    bot.send_message(message.chat.id, "Введите номер телефона:")


def input_phone(message: Message):
    anketa = ankets[message.from_user.id]
    anketa.phone = message.text.strip()
    if not anketa.phone:
        bot.send_message(message.chat.id, "Введите номер телефона!")
        return
    try:
        phone_parsed = phonenumbers.parse(anketa.phone, "RU")
        if not phonenumbers.is_valid_number(phone_parsed):
            raise NumberParseException
    except Exception:
        bot.send_message(message.chat.id, "Некорректный номер телефона!")
        return
    anketa.status = UserStatus.INPUT_REPAIR_SKILLS
    bot.send_message(message.chat.id, "Умеете ремонтировать технику? Да/Нет", reply_markup=generate_yes_no_markup())


def input_repair_skill(message: Message):
    anketa = ankets[message.from_user.id]
    anketa.repair_skill = message.text.strip()
    if anketa.repair_skill not in ('Да', 'Нет'):
        bot.send_message(message.chat.id, "Умеете ремонтировать технику? Да/Нет", reply_markup=generate_yes_no_markup())
        return
    anketa.status = UserStatus.INPUT_CLIENT_SKILLS
    bot.send_message(message.chat.id, "Умеете общаться с клиентами? Да/Нет", reply_markup=generate_yes_no_markup())


def input_client_skill(message: Message):
    anketa = ankets[message.from_user.id]
    anketa.clients_skill = message.text.strip()
    if anketa.clients_skill not in ('Да', 'Нет'):
        bot.send_message(message.chat.id, "Умеете общаться с клиентами? Да/Нет", reply_markup=generate_yes_no_markup())
        return
    anketa.status = UserStatus.INPUT_SALARY
    bot.send_message(message.chat.id, "Введите ожидаемую зарплату:")


def input_salary(message: Message):
    anketa = ankets[message.from_user.id]
    if not message.text.strip().isdigit():
        bot.send_message(message.chat.id, "Введите число для зарплаты!")
        return
    anketa.salary = int(message.text.strip())
    anketa.status = UserStatus.FINISHED
    bot.send_message(message.chat.id, "Анкета успешно заполнена!")
    anketa.send(sheet, message.from_user.username)


bot.polling(none_stop=True)
