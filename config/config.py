import re
import json

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"] # ["https://www.googleapis.com/auth/spreadsheets.readonly"]

URL = 'https://docs.google.com/spreadsheets/d/1k-QRsmuIz6USKoRuVTb7J4gO0s0XEnnaQNOxaXAmZAg/edit?resourcekey=&gid=1115161138#gid=1115161138'
LIST_NAME = 'Ответы на форму (1)'

TOKEN_FILE = 'config/config.json'
CREDENTIALS_FILE = 'config/credentials.json'

pattern = r'/d/([A-Za-z0-9-]*)'
SPREADSHEET_ID = re.findall(pattern, URL)[0]

# Максимальное расстояние в километрах
MAX_DISTANCE = 100

DEFAULT_EMAIL = 'ozodbekhh2007@gmail.com'

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
with open('config/mail.json', encoding='utf-8') as mail_file:
    mail_data = json.load(mail_file)
    SMTP_LOGIN = mail_data['login']
    SMTP_PASSWORD = mail_data['password']
