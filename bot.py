from collections import defaultdict  # Импортируем defaultdict для удобного хранения данных

import gspread  # Импортируем библиотеку для работы с Google Sheets
import phonenumbers  # Импортируем библиотеку для работы с номерами телефонов
from phonenumbers import NumberParseException  # Импортируем исключение для обработки некорректных номеров

from telebot import types, TeleBot  # Импортируем типы и класс для создания Telegram ботов
from telebot.types import Message  # Импортируем тип сообщения для обработки

from email_validator import validate_email, EmailNotValidError  # Импортируем функции для валидации email
from utils import get_correct_city_name, get_filial_cities
import config  # Импортируем файл конфигурации с токенами бота и ID таблицы Google Sheets
from utils import get_credits  # Импортируем функцию для получения учетных данных
from bot_utils.anketa import Anketa  # Импортируем класс анкеты
from bot_utils.user_status import UserStatus  # Импортируем класс для статусов пользователей

# Определяем текстовые значения кнопок
BTN_RESTART = "🔄 Перезапуск"
BTN_SURVEY = "📝 Заполнить анкету"
BTN_CANCEL = "Отмена"

# Используем defaultdict для хранения анкет пользователей
ankets = defaultdict(Anketa)

# Получаем учетные данные и авторизуемся в Google Sheets
creds = get_credits()
client = gspread.authorize(creds)  # Авторизация с использованием учетных данных
sheet = client.open_by_key(config.SPREADSHEET_ID).sheet1  # Открываем таблицу по ID
bot = TeleBot(config.TG_TOKEN)  # Создаем экземпляр бота с токеном


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def welcome(message: Message):
    ankets[message.from_user.id].status = UserStatus.NEW_USER  # Устанавливаем статус нового пользователя

    # Создаем клавиатуру с кнопками
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(BTN_SURVEY)  # Кнопка "Заполнить анкету"
    btn2 = types.KeyboardButton(BTN_RESTART)  # Кнопка "Перезапуск"
    markup.add(btn1, btn2)  # Добавляем кнопки в клавиатуру
    bot.send_message(message.chat.id,
                     "Добро пожаловать, {0.first_name}!\nЯ - {1.first_name}, бот созданный чтобы быть подопытным кроликом.".format(
                         message.from_user, bot.get_me()),
                     parse_mode='html', reply_markup=markup)  # Отправляем приветственное сообщение


# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def loco(message: Message):
    if message.chat.type == 'private':  # Проверяем, что сообщение в личном чате
        if message.text == BTN_RESTART:  # Если нажата кнопка "Перезапуск"
            welcome(message)  # Перезапускаем анкету
        # elif message.text == BTN_SURVEY:
        #     bot.send_message(message.chat.id, "Заполните анкету:", reply_markup=generate_anketa_markup())
        else:
            process_anketa(message)  # Обрабатываем анкету
        # else:
        #     bot.send_message(message.chat.id, 'Я не знаю что ответить 😢')


# Функция для генерации клавиатуры анкетирования
def generate_anketa_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton(BTN_CANCEL))  # Добавляем кнопку "Отмена"
    return markup


# Функция для генерации клавиатуры "Да/Нет"
def generate_yes_no_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton('Да'))  # Кнопка "Да"
    markup.add(types.KeyboardButton('Нет'))  # Кнопка "Нет"
    return markup


# Обработчик нажатия кнопки "Отмена"
@bot.message_handler(func=lambda message: message.text == BTN_CANCEL)
def cancel_anketa(message: Message):
    bot.send_message(message.chat.id, "Анкета отменена.")  # Уведомление об отмене анкеты
    welcome(message)  # Возвращаемся к приветствию


# Функция для обработки анкеты
def process_anketa(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    print(anketa)  # Печатаем анкету для отладки
    match anketa.status:  # Используем сопоставление статусов
        case UserStatus.NEW_USER:
            start_anketa(message)  # Начинаем анкету
        case UserStatus.INPUT_NAME:
            input_name(message)  # Запрос имени
        case UserStatus.INPUT_CITY:
            input_city(message)  # Запрос города
        case UserStatus.INPUT_EMAIL:
            input_email(message)  # Запрос email
        case UserStatus.INPUT_PHONE:
            input_phone(message)  # Запрос номера телефона
        case UserStatus.INPUT_REPAIR_SKILLS:
            input_repair_skill(message)  # Запрос навыков ремонта
        case UserStatus.INPUT_CLIENT_SKILLS:
            input_client_skill(message)  # Запрос клиентских навыков
        case UserStatus.INPUT_SALARY:
            input_salary(message)  # Запрос зарплаты
        case UserStatus.FINISHED:
            bot.send_message(message.chat.id, "Анкета сохранена")  # Сообщение о завершении
        case _:  # Обработка несуществующих состояний
            ...


# Функция для начала анкеты
def start_anketa(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    anketa.status = UserStatus.INPUT_NAME  # Переходим к вводу имени
    bot.send_message(message.chat.id, "Введите ФИО:")  # Запрашиваем ФИО


# Функция для ввода имени
def input_name(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    anketa.fio = message.text.strip()  # Сохраняем ФИО
    if not anketa.fio:  # Проверка на пустое значение
        bot.send_message(message.chat.id, "Введите ФИО!")  # Запрашиваем ФИО заново
        return
    anketa.status = UserStatus.INPUT_CITY  # Переходим к следующему этапу
    bot.send_message(message.chat.id, "Введите город:")  # Запрашиваем город


# Функция для ввода города
def input_city(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    city_input = message.text.strip()  # Сохраняем введенный город
    if not city_input:  # Проверка на пустое значение
        bot.send_message(message.chat.id, "Введите город!")  # Запрашиваем город заново
        return

    corrected_city = get_correct_city_name(city_input)

    if corrected_city:
        anketa.city = corrected_city
        filial_cities = get_filial_cities()
        if corrected_city in get_filial_cities() or filial_cities is None:
            anketa.status = UserStatus.INPUT_EMAIL  # Переходим к следующему этапу
            bot.send_message(message.chat.id, "Введите email:")  # Запрашиваем email
        else:
            text = "Наши филиалы представлены в следующих городах:\n\n• "
            text += '\n• '.join(sorted(get_filial_cities()))
            bot.send_message(message.chat.id, text)  # Запрашиваем email
    else:
        bot.send_message(message.chat.id, f"Город '{city_input}' не найден. Пожалуйста, введите корректное название.")


# Функция для ввода email
def input_email(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    try:
        anketa.email = message.text.strip()  # Сохраняем email
        if not anketa.email:  # Проверка на пустое значение
            bot.send_message(message.chat.id, "Введите корректный email!")  # Запрашиваем email заново
            return
        validate_email(anketa.email, check_deliverability=False)  # Валидация email
    except EmailNotValidError as e:  # Если email некорректный
        bot.send_message(message.chat.id, f"Некорректный email!")  # Уведомление об ошибке
        return
    anketa.status = UserStatus.INPUT_PHONE  # Переходим к следующему этапу
    bot.send_message(message.chat.id, "Введите номер телефона:")  # Запрашиваем номер телефона


# Функция для ввода номера телефона
def input_phone(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    anketa.phone = message.text.strip()  # Сохраняем номер телефона
    if not anketa.phone:  # Проверка на пустое значение
        bot.send_message(message.chat.id, "Введите номер телефона!")  # Запрашиваем номер заново
        return
    try:
        phone_parsed = phonenumbers.parse(anketa.phone, "RU")  # Парсим номер
        if not phonenumbers.is_valid_number(phone_parsed):  # Проверка на валидность номера
            raise NumberParseException  # Генерируем исключение, если номер невалидный
    except Exception:  # Обработка исключений при парсинге номера
        bot.send_message(message.chat.id, "Некорректный номер телефона!")  # Уведомление об ошибке
        return
    anketa.status = UserStatus.INPUT_REPAIR_SKILLS  # Переходим к следующему этапу
    bot.send_message(message.chat.id, "Умеете ремонтировать технику? Да/Нет",
                     reply_markup=generate_yes_no_markup())  # Запрос навыков ремонта


# Функция для ввода навыков ремонта
def input_repair_skill(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    anketa.repair_skill = message.text.strip()  # Сохраняем ответ о навыках ремонта
    if anketa.repair_skill not in ('Да', 'Нет'):  # Проверка ответа на допустимые значения
        bot.send_message(message.chat.id, "Умеете ремонтировать технику? Да/Нет",
                         reply_markup=generate_yes_no_markup())  # Запрашиваем ответ повторно
        return
    anketa.status = UserStatus.INPUT_CLIENT_SKILLS  # Переходим к следующему этапу
    bot.send_message(message.chat.id, "Умеете общаться с клиентами? Да/Нет",
                     reply_markup=generate_yes_no_markup())  # Запрашиваем клиентские навыки


# Функция для ввода клиентских навыков
def input_client_skill(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    anketa.clients_skill = message.text.strip()  # Сохраняем ответ о навыках общения
    if anketa.clients_skill not in ('Да', 'Нет'):  # Проверка ответа на допустимые значения
        bot.send_message(message.chat.id, "Умеете общаться с клиентами? Да/Нет",
                         reply_markup=generate_yes_no_markup())  # Запрашиваем ответ повторно
        return
    anketa.status = UserStatus.INPUT_SALARY  # Переходим к следующему этапу
    bot.send_message(message.chat.id, "Введите ожидаемую зарплату:")  # Запрашиваем зарплату


# Функция для ввода зарплаты
def input_salary(message: Message):
    anketa = ankets[message.from_user.id]  # Получаем анкету пользователя
    if not message.text.strip().isdigit():  # Проверка на число
        bot.send_message(message.chat.id, "Введите число для зарплаты!")  # Запрашиваем число заново
        return
    anketa.salary = int(message.text.strip())  # Сохраняем зарплату
    anketa.status = UserStatus.FINISHED  # Завершаем анкету
    bot.send_message(message.chat.id, "Анкета успешно заполнена!")  # Уведомление об успешном завершении
    anketa.send(sheet, message.from_user.username)  # Отправляем анкету в Google Sheets


# Запускаем бота на постоянное прослушивание сообщений
bot.polling(none_stop=True)
