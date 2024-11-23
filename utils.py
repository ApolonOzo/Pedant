import os
import logging
from functools import wraps, lru_cache
from typing import List, Optional
import smtplib

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from jinja2 import Template

import config

logger = logging.getLogger(__name__)


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
        location = geolocator.geocode(user_input, exactly_one=True)
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
        text = (header + text).format(email, config.SMTP_LOGIN).encode('utf-8')
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