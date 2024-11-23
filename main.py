import schedule
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

from utils import get_credits, get_correct_city_name, get_item, get_post, send_email
import config



def main():
    print('Запускаем скрипт...')
    creds = get_credits()
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=config.SPREADSHEET_ID, range=config.LIST_NAME + "!A2:J")
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print("No data found.")
            return

        data = []
        for row_id, row in enumerate(values, 2):
            status = get_item(row, 9) or False
            if status:
                # Заявка уже обработана
                continue
            creation_data = get_item(row, 0)
            name = get_item(row, 1)
            city = get_item(row, 2)
            email = get_item(row, 3)
            phone = get_item(row, 4)
            skill_repair = get_item(row, 5)
            skill_clients = get_item(row, 6)
            salary = get_item(row, 7)

            data.append([name, city, get_correct_city_name(city), status])
            dest_email = config.DEFAULT_EMAIL
            post_text = get_post(locals())
            send_email(dest_email, post_text)

            # Отмечаем запись как обработанную
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

        if data:
            data = pd.DataFrame(data)
            print(data)
        else:
            print('Нет новых заявок')

    except HttpError as err:
        print(err)
    print()


if __name__ == '__main__':
    schedule.every(1).minutes.do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
