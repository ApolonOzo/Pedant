import schedule  # Импорт библиотеки для планирования задач
import time  # Импорт библиотеки для работы со временем

from googleapiclient.discovery import build  # Импорт для построения Google API сервиса
from googleapiclient.errors import HttpError  # Импорт для обработки ошибок API
import pandas as pd  # Импорт библиотеки pandas для работы с данными в табличном формате

from utils import get_credits, get_correct_city_name, get_item, get_post, send_email  # Импорт пользовательских утилит
import config  # Импорт конфигурационного файла для хранения настроек


def main():
    print('Запускаем скрипт...')  # Сообщение о запуске скрипта
    creds = get_credits()  # Получение учетных данных для доступа к API Google
    try:
        # Подключение к сервису Google Sheets
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()  # Создание объекта для работы с таблицей

        # Получение данных из таблицы по указанному диапазону
        result = (
            sheet.values()
            .get(spreadsheetId=config.SPREADSHEET_ID, range=config.LIST_NAME + "!A2:J")
            .execute()
        )
        values = result.get("values", [])  # Извлечение значений из ответа API
        if not values:
            print("No data found.")  # Если данных нет, выводим сообщение
            return

        data = []  # Список для хранения обработанных данных
        for row_id, row in enumerate(values, 2):  # Перебор строк таблицы (начиная со 2-й строки)
            status = get_item(row, 9) or False  # Проверяем статус заявки
            if status:
                # Если заявка уже обработана, переходим к следующей
                continue

            # Извлечение данных из строки
            creation_data = get_item(row, 0)
            name = get_item(row, 1)
            city = get_item(row, 2)
            email = get_item(row, 3)
            phone = get_item(row, 4)
            skill_repair = get_item(row, 5)
            skill_clients = get_item(row, 6)
            salary = get_item(row, 7)

            # Добавление обработанных данных в список
            data.append([name, city, get_correct_city_name(city), status])
            dest_email = config.DEFAULT_EMAIL  # Установка адреса получателя
            post_text = get_post(locals())  # Генерация текста сообщения
            send_email(dest_email, post_text)  # Отправка email

            # Отметка записи как обработанной
            result = (
                sheet.values()
                .update(
                    spreadsheetId=config.SPREADSHEET_ID,
                    range=config.LIST_NAME + f"!J{row_id}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[f"Отправлен email на {dest_email}"]]}
                )
                .execute()
            )

        # Если есть обработанные данные, выводим их в виде DataFrame
        if data:
            data = pd.DataFrame(data)
            print(data)  # Печать обработанных данных
        else:
            print('Нет новых заявок')  # Сообщение, если нет новых заявок

    except HttpError as err:  # Обработка ошибок API
        print(err)
    print()  # Печать пустой строки для форматирования вывода


if __name__ == '__main__':
    # Настройка планировщика для вызова функции main каждые 1 минуту
    schedule.every(1).minutes.do(main)
    while True:  # Бесконечный цикл для выполнения запланированных задач
        schedule.run_pending()  # Выполнение всех запланированных задач
        time.sleep(1)  # Заказ на паузу в 1 секунду
