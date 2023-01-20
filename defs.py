import string

from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from emoji import emojize

from config import available_groups, sql


async def cancel_state(state: FSMContext):
    state_ = await state.get_state()
    if state_ is not None:
        await state.finish()


async def transform_into_user_groups():
    users_in_groups = await sql.get_all('gay_groups')
    users_id = await sql.get_from_all('user_id')
    user_groups = {}
    for group in users_in_groups:
        for user_id in users_id:
            if user_id not in user_groups.keys():
                user_groups[user_id] = []
            if user_id in group[1]:
                user_groups[user_id] += [group[0]]
    return user_groups


async def get_name_and_nickname(user_id):
    user_name = await sql.get_data(user_id, 'user_name')
    nickname = await sql.get_data(user_id, 'nickname')
    return f'''<a href="tg://user?id={user_id}">{f"<i>{nickname}</i>" if nickname is not None else f"{user_name}"}</a>'''
