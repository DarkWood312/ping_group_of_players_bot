import string

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from emoji import emojize

from config import available_groups
from defs import transform_into_user_groups


async def groups_markup(self_id):
    markup = InlineKeyboardMarkup()
    user_groups = await transform_into_user_groups()
    for button in await available_groups():
        if button in user_groups[self_id]:
            display_button = button + f' {emojize(":check_mark_button:")}'
        else:
            display_button = button
        markup.row(InlineKeyboardButton(string.capwords(display_button), callback_data=button))
    return markup


async def menu_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    group_button = KeyboardButton(emojize('Выбор группы:family_man_man_girl_boy:'))
    ping_button = KeyboardButton(emojize('Пинг | Созыв:telephone:'))
    nickname_button = KeyboardButton(emojize('Изменить ник:radioactive:'))
    markup.row(ping_button).row(group_button).row(nickname_button)
    return markup