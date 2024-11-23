from enum import StrEnum


class UserStatus(StrEnum):
    NEW_USER = ""
    INPUT_NAME = 'name'
    INPUT_CITY = "city"
    INPUT_EMAIL = "email"
    INPUT_PHONE = "phone"
    INPUT_REPAIR_SKILLS = "recover"
    INPUT_CLIENT_SKILLS = "client"
    INPUT_SALARY = "salary"
    FINISHED = "finished"