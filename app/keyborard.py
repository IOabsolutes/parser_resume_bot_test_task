from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardButton, InlineKeyboardMarkup)
from schemas import EmploymentType, ExperienceLevel

main = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔍 Search for a job"),
            KeyboardButton(text="Filters"),
            KeyboardButton(text="Filter info"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Select an option",
)

filter_catalog = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Position", callback_data="position"),
            InlineKeyboardButton(text="Experience level", callback_data="experience_level"),
            InlineKeyboardButton(text="Skills", callback_data="skills"),
            InlineKeyboardButton(text="Location", callback_data="location"),
            InlineKeyboardButton(text="Salary", callback_data="salary"),
            InlineKeyboardButton(text="Employment type", callback_data="employment_type"),
        ],
    ],
)

experience_level = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="без досвіду", callback_data=ExperienceLevel.NO_EXPERIENCE.value),
            InlineKeyboardButton(text="до 1 року", callback_data=ExperienceLevel.LESS_THAN_1.value),
            InlineKeyboardButton(text="від 1 до 2 років", callback_data=ExperienceLevel.ONE_TO_TWO.value),
            InlineKeyboardButton(text="від 2 до 5 років", callback_data=ExperienceLevel.TWO_TO_FIVE.value),
            InlineKeyboardButton(text="від 5 до 10 років", callback_data=ExperienceLevel.FIVE_TO_TEN.value),
            InlineKeyboardButton(text="більше 10 років", callback_data=ExperienceLevel.MORE_THAN_TEN.value),
        ],
    ],
)

employment_type = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Повний робочий день", callback_data=EmploymentType.FULL_TIME.value),
            InlineKeyboardButton(text="Частиний робочий день", callback_data=EmploymentType.PART_TIME.value),
            InlineKeyboardButton(text="Віддалений", callback_data=EmploymentType.REMOTE.value),
        ],
    ],
)

nav_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Next", callback_data="next page"),
        ],
    ],
)
