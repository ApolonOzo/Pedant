import json
import math
import os
import logging
from functools import wraps, lru_cache
from typing import List, Optional, Set, Tuple
import smtplib

import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build  # Импорт для построения Google API сервиса

from jinja2 import Template

import config

logger = logging.getLogger(__name__)
logger.setLevel(config.LOG)


def get_credits() -> Credentials:
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CREDENTIALS_FILE, config.SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(config.TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds


def correct_city_name_decorator(function):
    city_association_dict = {}
    with open('data/city_association.txt', encoding='utf-8') as city_association:
        for line in map(str.strip, city_association.readlines()):
            if '->' in line:
                city, correct_city = line.split("->")
                city = city.lower().strip()
                correct_city = correct_city.strip()
                city_association_dict[city] = correct_city.strip()

    @wraps(function)
    def wrapper(user_input: str):
        nonlocal city_association_dict
        from_dict = city_association_dict.get(user_input.lower())
        if from_dict:
            return from_dict
        return function(user_input)

    return wrapper


@lru_cache(10000)
@correct_city_name_decorator
def get_correct_city_name(user_input: str) -> str | None:
    geolocator = Nominatim(user_agent="city_checker")
    try:
        # Попытка найти введённый город
        location = geolocator.geocode(user_input, exactly_one=True, language='ru')
        if location:
            return location.address.split(",")[0]  # Первое слово в адресе - название города
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.error(f"Ошибка соединения с сервисом: {e}")
        return


def get_item(arr: List[str], index: int) -> Optional[str]:
    if index < 0 or index >= len(arr):
        return
    return arr[index]


def email_decorator(function):
    smtpObj = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
    smtpObj.starttls()
    smtpObj.login(config.SMTP_LOGIN, config.SMTP_PASSWORD)
    header = '''Content-Type: text/html; charset="utf-8"
Content-Transfer-Encoding: 8bit
MIME-Version: 1.0
To: {}
From: {}
Subject: Новая заявка
X-Peer: ::1

'''

    @wraps(function)
    def wrapper(email: str, text: str):
        text = (header.format(email, config.SMTP_LOGIN) + text).encode('utf-8')
        return function(email, text, smtpObj)

    return wrapper


@email_decorator
def send_email(email: str, text: str, smtpObj=None):
    smtpObj.sendmail(config.SMTP_LOGIN, email, text)


def post_decorator(function):
    with open('data/post_template.html', encoding='utf-8') as f:
        template_text = f.read()
    template = Template(template_text)

    @wraps(function)
    def wrapper(values: dict):
        msg = template.render(**values)
        return msg

    return wrapper


@post_decorator
def get_post(values) -> str:
    pass


@lru_cache(100)
def get_filial_cities() -> Optional[Set[str]]:
    '''
    Получение списка городов филиалов из таблицы Google Sheets

    :return: Список множнество с городами
    '''
    creds = get_credits()
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()  # Создание объекта для работы с таблицей
    result = (
        sheet.values()
        .get(spreadsheetId=config.SPREADSHEET_ID, range=config.LIST_CITY_NAME + "!B2:B")
        .execute()
    )
    values = result.get("values", [])  # Извлечение значений из ответа API
    if not values:
        print("No data found.")  # Если данных нет, выводим сообщение
        return
    cities = set()
    for row in values:
        if len(row) != 1:
            continue
        city = row[0].strip()
        if city and not city[-1].isdigit():
            cities.add(city)
    return cities



def get_coordinates_decorator(function):
    with open(config.COORDS_FILE, encoding='utf-8') as f:
        cache = json.load(f)

    @wraps(function)
    def wrapper(city_name: str) -> Tuple[float, float]:
        if isinstance(city_name, str):
            if city_name in cache:
                return cache[city_name]

        result = function(city_name)
        if isinstance(city_name, str):
            cache[city_name] = result
            with open(config.COORDS_FILE, "w", encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=4)
        return result

    return wrapper


@get_coordinates_decorator
def get_coordinates(city_name: str) -> Tuple[float, float]:
    """
    Нахождение координат города

    :param city_name: название города
    :return: координаты города (долгота, широта)
    """
    logger.info(f"get_coordinates: {city_name}")
    print(city_name)
    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": config.YANDEX_MAP_API,
            'geocode': city_name,
            'format': 'json'
        }
        data = requests.get(url, params).json()
        coordinates_str = data['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['Point']['pos']
        long, lat = map(float, coordinates_str.split())
        return long, lat
    except Exception as e:
        return 0.0, 0.0


def get_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Функция, находящая расстояние между двумя точками на карте

    :param p1: координаты первой точки (долгота, широта)
    :param p2: координаты второй точки (долгота, широта)
    :return: расстояние, км
    """
    radius = 6373.0

    lon1 = math.radians(p1[0])
    lat1 = math.radians(p1[1])
    lon2 = math.radians(p2[0])
    lat2 = math.radians(p2[1])

    d_lon = lon2 - lon1
    d_lat = lat2 - lat1

    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(a ** 0.5, (1 - a) ** 0.5)

    distance = radius * c
    return distance


def get_nearest_city(city: str) -> Optional[str]:
    """
    Нахождение ближайшего города к введенному

    :param city: название города
    :return: название ближайшего города
    """
    cities = list(get_filial_cities())
    if not cities:
        return
    distances = [get_distance(
        get_coordinates(s), get_coordinates(city)
    ) for s in cities]
    min_distance = min(distances)
    nearest_city = cities[distances.index(min_distance)]

    print(nearest_city, min_distance)
    if min_distance < config.MAX_DISTANCE:
        return nearest_city
