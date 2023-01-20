import logging
import string

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ParseMode, ContentType
from aiogram.dispatcher import FSMContext, filters
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.markdown import hcode
from config import token, sql, ping_templates, available_groups
from defs import cancel_state, transform_into_user_groups, get_name_and_nickname
from keyboards import groups_markup, menu_markup
logging.basicConfig(level=logging.DEBUG)
bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())


class Ping(StatesGroup):
    selecting = State()
    writing = State()


class Nickname(StatesGroup):
    setnick = State()


class Group(StatesGroup):
    setgroup = State()


@dp.message_handler(commands='start', state='*')
async def start_message(message: Message, state: FSMContext):
    await cancel_state(state)
    await sql.add_user(user_id=message.from_user.id, username=message.from_user.username,
                       user_name=message.from_user.first_name, user_surname=message.from_user.last_name)
    await message.answer_sticker('CAACAgIAAxkBAAEcFGJjxZDZ2jGLg3QHetNgksZBBnha8QACSQEAAntOKhDSitDV6aV93y0E', reply_markup=await menu_markup())


@dp.message_handler(commands='cancel', state='*')
async def cancel(message: Message, state: FSMContext):
    await cancel_state(state)
    await message.answer('Действие отменено!')


@dp.message_handler(commands='nickname', state='*')
async def set_nickname(message: Message, state: FSMContext):
    await cancel_state(state)
    old_nick = await sql.get_data(message.from_user.id, 'nickname')
    markup = InlineKeyboardMarkup()
    cancel_button = InlineKeyboardButton('Отмена', callback_data='cancel')
    set_to_none_button = InlineKeyboardButton('Удалить', callback_data='remove_nickname')
    markup.row(cancel_button)
    if await sql.get_data(message.from_user.id, 'nickname') is not None:
        markup.row(set_to_none_button)
    await message.answer(
        text=f"""Введите новый ник: \n{f"Текущий: '{hcode(old_nick)}'" if old_nick is not None else ''}""",
        reply_markup=markup, parse_mode=ParseMode.HTML)
    await state.update_data(old_nick=old_nick)
    await Nickname.setnick.set()


@dp.message_handler(commands=['ping'], state='*')
async def ping(message: Message, state: FSMContext):
    await cancel_state(state)
    markup = InlineKeyboardMarkup()
    groups = await sql.get_all('gay_groups')
    lines = []
    for group in groups:
        if (len(group[1]) < 1) or (len(group[1]) == 1 and message.from_user.id in group[1]):
            continue
        button = InlineKeyboardButton(string.capwords(group[0]), callback_data=group[0])
        markup.row(button)
        line = f"""<u>{string.capwords(group[0])}</u>:  """
        for user in group[1]:
            if user == message.from_user.id:
                continue
            line = line + f'{await get_name_and_nickname(user)}, '
        line = line[:-2] + '\n'
        lines.append(line)
    await message.answer(text='<b>Пользователи в группах:</b>\n' + '\n'.join(lines) + '\n<b>Доступные группы для пинга:</b>', reply_markup=markup, parse_mode=ParseMode.HTML)
    await Ping.selecting.set()


@dp.message_handler(commands=['group'], state='*')
async def group(message: Message, state: FSMContext):
    await cancel_state(state)
    await message.answer('Доступные группы: ', reply_markup=await groups_markup(message.from_user.id))
    await Group.setgroup.set()


@dp.message_handler(state=Nickname.setnick)
async def state_Nickname_setnick(message: Message, state: FSMContext):
    if message.text == 'Изменить ник☢️':
        await set_nickname(message, state)
        return
    elif message.text == 'Пинг | Созыв☎️':
        await ping(message, state)
        return
    elif message.text == 'Выбор группы👨‍👨‍👧‍👦':
        await group(message, state)
        return
    if len(message.text) > 18:
        await message.answer(f'Длина ника не может превышать 18 символов! У вас --> {len(message.text)}')
        return
    data = await state.get_data()
    old_nick = data['old_nick']
    await sql.update_data(message.from_user.id, 'nickname', message.text)
    await message.answer(f"""Ник успешно обновлен с '{hcode(old_nick) if old_nick is not None else ''}' на '{hcode(message.text)}'\nТеперь вы: {await get_name_and_nickname(message.from_user.id)}""",
                         parse_mode=ParseMode.HTML)
    await state.finish()


@dp.callback_query_handler(state=Group.setgroup)
async def state_Group_setgroup(call: CallbackQuery):
    users_in_group = await sql.get_group_users(call.data)
    if call.from_user.id in users_in_group:
        await sql.remove_user_from_group(call.data, call.from_user.id)
    elif call.from_user.id not in users_in_group:
        await sql.add_user_to_group(call.data, call.from_user.id)
    await call.message.edit_reply_markup(await groups_markup(call.from_user.id))


@dp.callback_query_handler(state=Ping.selecting)
async def state_Ping_selecting(call: CallbackQuery, state: FSMContext):
    receiver_group = call.data
    await state.update_data(receiver_group=receiver_group)
    await state.update_data(sender=call.from_user.id)
    markup = InlineKeyboardMarkup()
    for template in ping_templates:
        markup.row(InlineKeyboardButton(template, callback_data=template))
    await call.message.answer(f"Введите сообшение для группы <i>'{string.capwords(receiver_group)}'</i> или выберите готовое <b>ниже</b>:", reply_markup=markup, parse_mode=ParseMode.HTML)
    await Ping.writing.set()


@dp.callback_query_handler(state=Ping.writing)
async def state_Ping_writing_call(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    receiver_group = data['receiver_group']
    receiver_group_users = await sql.get_group_users(receiver_group)
    sender = data['sender']
    for receiver_user in receiver_group_users:
        if receiver_user == call.from_user.id:
            continue
        await bot.send_message(receiver_user, call.data)
        await bot.send_message(receiver_user,
                               f'<i>{string.capwords(receiver_group)}</i>. Вам пришло сообщение от {await get_name_and_nickname(sender)}',
                               parse_mode=ParseMode.HTML, disable_notification=True)
    await call.message.answer(
        f'''Повестка: '<code>{call.data}</code>' была успешно отправлена группе '<i>{string.capwords(receiver_group)}</i>' ''',
        parse_mode=ParseMode.HTML, disable_notification=True)
    await state.finish()


@dp.message_handler(state=Ping.writing, content_types=ContentType.ANY)
async def state_Ping_writing_message(message: Message, state: FSMContext):
    data = await state.get_data()
    receiver_group = data['receiver_group']
    receiver_group_users = await sql.get_group_users(receiver_group)
    sender = data['sender']
    for receiver_user in receiver_group_users:
        if receiver_user == message.from_user.id:
            continue
        await message.copy_to(receiver_user)
        await bot.send_message(receiver_user,
                               f'<i>{string.capwords(receiver_group)}</i>. Вам пришло сообщение от {await get_name_and_nickname(sender)}',
                               parse_mode=ParseMode.HTML, disable_notification=True)
    await message.answer(
        f'''Повестка: '<code>{message.text}</code>' была успешно отправлена группе '<i>{string.capwords(receiver_group)}</i>' ''',
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


@dp.message_handler(state='*')
async def other_messages(message: Message, state: FSMContext):
    low = message.text.lower()
    # * Menu
    if 'пинг' in low:
        await ping(message, state)
    elif 'выбор группы' in low:
        await group(message, state)
    elif 'изменить ник' in low:
        await set_nickname(message, state)
    # * bad words
    elif low == 'хуй':
        await message.answer('у тебя его нет хахахаххапх(не смешно)')
    elif 'нахуй' in low:
        await message.answer_sticker('кусай')
    elif 'андре' in low:
        await message.answer('было дело..')
    elif 'чмо' in low:
        await message.answer('открой камеру, переключи на фронтальную и увидишь его')
    elif 'даун' in low:
        await message.answer('ты - солнечный мальчик🌞')
    elif 'нахуя' in low:
        await message.answer('бля я сам хз, делать нечего просто')
    elif 'конч' in low:
        await message.answer(
            '*Конч* - это безнадёжный, неисправимый, потерянный человек. Человек, который ведёт себя безнравственно и недостойно.',
            parse_mode='Markdown')
    elif 'шлюха' in low:
        await message.answer('твоя маааааааааать. про мать было лишнее')
    elif 'тварь' in low:
        await message.answer('где')
    elif 'пошел' in low:
        await message.answer('а может ты')
    elif 'гнида' in low:
        await message.answer('твой бухающий отец')
    elif 'хуила' in low:
        await message.answer('жоска')
    elif 'блять' in low:
        await message.answer('кто, ты?')
    elif 'да' in low:
        await message.answer('пизда')
    # 300
    elif low == '300' or low == 'триста':
        await message.answer('отсоси у тракториста')
    elif 'трактористом буду я' and 'отсос' and 'ты у меня' in low:
        await message.answer('трактористом ты не будешь, отсоси и будь свободен')
    elif 'годен я' and 'сомнений нет' and 'лучше сделай мне минет' in low:
        await message.answer('а сомнения есть всегда лучше нюхай 3 хуя')
    elif 'извини' and 'спина не' and 'отсосать тебе придется' in low:
        await message.answer('можешь стоя отсосать, я не буду возражать')
    # 3
    elif low == '3':
        await message.answer('жопу подотри')
    # пидора ответ
    elif low == 'нет':
        await message.answer('пидора ответ')
    elif low == 'шлюхи аргумент':
        await message.answer('аргумент не нужен, пидор обнаружен')
    elif 'пидор' and 'засекречен' and 'твой' and 'анал' and 'не' and 'вечен' in low:
        await message.answer('анал мой вечен, твой анал помечен')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
