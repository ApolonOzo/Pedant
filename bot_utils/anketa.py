from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from gspread import Worksheet

from .user_status import UserStatus


@dataclass
class Anketa:
    fio: Optional[str] = None
    city: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    repair_skill: Optional[bool] = None
    clients_skill: Optional[bool] = None
    salary: Optional[int] = None
    status: Optional[UserStatus] = UserStatus.NEW_USER

    def send(self, sheet: Worksheet, username: str):
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        sheet.append_row(
            [
                current_time,
                self.fio,
                self.city,
                self.email,
                self.phone,
                self.repair_skill,
                self.clients_skill,
                self.salary,
                username],
            table_range='A1'
        )