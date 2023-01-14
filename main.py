import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ParseMode, ContentType
from aiogram.dispatcher import FSMContext, filters
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.markdown import hcode

from config import token, sql

logging.basicConfig(level=logging.DEBUG)
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())


class FindGroup(StatesGroup):
    selecting = State()
    writing = State()


class Nickname(StatesGroup):
    setnick = State()


async def cancel_state(state: FSMContext):
    state_ = await state.get_state()
    if state_ is not None:
        await state.finish()


@dp.message_handler(commands='start', state='*')
async def start_message(message: Message, state: FSMContext):
    await cancel_state(state)
    await sql.add_user(user_id=message.from_user.id, username=message.from_user.username,
                       user_name=message.from_user.first_name, user_surname=message.from_user.last_name)
    await message.answer('Hi!')


@dp.message_handler(commands='cancel', state='*')
async def cancel(message: Message, state: FSMContext):
    await cancel_state(state)
    await message.answer('Действие отменено!')


@dp.message_handler(commands='nickname', state='*')
async def set_nickname(message: Message, state: FSMContext):
    await cancel_state(state)
    old_nick = await sql.get_data(message.from_user.id, 'nickname')
    try:
        command, nick = message.text.split(' ', 1)
        await sql.update_data(message.from_user.id, 'nickname', nick)
        await message.answer(f"Ник успешно обновлен с '{hcode(old_nick)}' на '{hcode(nick)}'",
                             parse_mode=ParseMode.HTML)
    except ValueError:
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton('Отмена', callback_data='cancel')
        set_to_none_button = InlineKeyboardButton('Удалить', callback_data='remove_nickname')
        markup.row(cancel_button)
        if await sql.get_data(message.from_user.id, 'nickname') is not None:
            markup.row(set_to_none_button)
        await message.answer(
            text=f"""Введите новый ник: \n{f"Текущий: '{hcode(old_nick)}'" if old_nick is not None else ''}""",
            reply_markup=markup, parse_mode=ParseMode.HTML)
        await Nickname.setnick.set()
        await state.update_data(old_nick=old_nick)


@dp.message_handler(commands=['find'], state='*')
async def find_group(message: Message, state: FSMContext):
    await cancel_state(state)
    list_markup = InlineKeyboardMarkup()
    users = await sql.get_users()
    anonymous = await sql.get_users(only_anonymous=True)
    for user in users:
        if user[0] == message.from_user.id or user[0] in anonymous:
            continue
        button = InlineKeyboardButton(text=f'{user[2]} {f"({user[4]})" if user[4] is not None else ""}',
                                      callback_data=f'{user[0]}')
        list_markup.row(button)
    await message.answer('Список:', reply_markup=list_markup)
    await FindGroup.selecting.set()


@dp.message_handler(state=Nickname.setnick)
async def state_Nickname_setnick(message: Message, state: FSMContext):
    data = await state.get_data()
    old_nick = data['old_nick']
    await sql.update_data(message.from_user.id, 'nickname', message.text)
    await message.answer(f"Ник успешно обновлен с '{hcode(old_nick)}' на '{hcode(message.text)}'",
                         parse_mode=ParseMode.HTML)


@dp.callback_query_handler(state=FindGroup.selecting)
async def state_FindGroup_select(call: CallbackQuery, state: FSMContext):
    await state.update_data(receiver=call.data, sender=call.from_user.id)
    user_name = await sql.get_data(call.data, 'user_name')
    markup = InlineKeyboardMarkup()
    templates = ['Пошли играть!']
    for template in templates:
        markup.row(InlineKeyboardButton(text=template, callback_data=template))
    await call.message.answer(
        f'Введите сообщение для <a href="tg://user?id={call.data}">{user_name}</a> или выберите готовое ниже:',
        reply_markup=markup, parse_mode=ParseMode.HTML)
    await FindGroup.writing.set()


@dp.callback_query_handler(state=FindGroup.writing)
async def state_FindGroup_writing_call(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    receiver = data['receiver']
    sender = data['sender']
    sender_name = await sql.get_data(sender, 'user_name')
    sender_nick = await sql.get_data(sender, 'nickname')
    user_name = await sql.get_data(receiver, 'user_name')
    nickname = await sql.get_data(receiver, 'nickname')
    await bot.send_message(receiver, call.data)
    await bot.send_message(receiver,
                           f'Вам пришло сообщение от <a href="tg://user?id={sender}">{sender_name} {f"(<i>{sender_nick}</i>)" if sender_nick is not None else ""}</a>',
                           parse_mode=ParseMode.HTML, disable_notification=True)
    await call.message.answer(
        f'''Повестка: '<code>{call.data}</code>' была успешно отправлена <a href="tg://user?id={receiver}">{user_name} {f"<i>({nickname})</i>" if nickname is not None else ""}</a>''',
        parse_mode=ParseMode.HTML, disable_notification=True)
    await state.finish()


@dp.message_handler(state=FindGroup.writing, content_types=ContentType.ANY)
async def state_FindGroup_writing_message(message: Message, state: FSMContext):
    data = await state.get_data()
    receiver = data['receiver']
    sender = data['sender']
    sender_name = await sql.get_data(sender, 'user_name')
    sender_nick = await sql.get_data(sender, 'nickname')
    user_name = await sql.get_data(receiver, 'user_name')
    nickname = await sql.get_data(receiver, 'nickname')
    await message.copy_to(receiver)
    await bot.send_message(receiver,
                           f'Вам пришло сообщение от <a href="tg://user?id={sender}">{sender_name} {f"<i>({sender_nick})</i>" if sender_nick is not None else ""}</a>',
                           parse_mode=ParseMode.HTML, disable_notification=True)
    await message.answer(
        f'''Повестка: '<code>{message.text}</code>' была успешно отправлена <a href="tg://user?id={receiver}">{user_name} {f"<i>({nickname})</i>" if nickname is not None else ""}</a>''',
        parse_mode=ParseMode.HTML, disable_notification=True)
    await state.finish()


@dp.callback_query_handler(state='*')
async def callback(call: CallbackQuery, state: FSMContext):
    if call.data == 'cancel':
        if await state.get_state() is not None:
            await state.finish()
            await call.message.answer('Действие отменено!')
    elif call.data == 'remove_nickname':
        await sql.update_non_text_data(call.from_user.id, 'nickname', 'NULL')
        await call.message.answer('Ник успешно удален!')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
