import asyncio, random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, input_text_message_content

import sql as SQL
from coinmarketcap import CMC
from config import *


CMC = CMC(api_key=API_KEY, base_url=BASE_URL)

bot = Bot(token=BOT_TOKEN)
app = Dispatcher()
user_next_step = {}


# update coin quotes
async def update_quotes():
    '''
    Update coin quotes every 61 seconds
    '''
    await SQL.create_database()
    while True:
        await asyncio.sleep(61)
        coins = await SQL.get_distinct_coins_id()
        if not coins:
            continue
        coin_quotes = CMC.get_coin_quotes(coins=coins)
        if not coin_quotes:
            continue
        for coin_id, data in coin_quotes.items():
            users_id = await SQL.get_users_follow_coin(coin_id=coin_id, coin_value=data['quote']['USD']['price'])
            if not users_id:
                continue
            title = f"Поймали <b>{data['name']} за {data['quote']['USD']['price']} USD!</b>"
            for user_id in users_id:
                min = f"\n📉 {data['symbol']} дешевле чем {user_id['mi']} USD" if user_id['mi'] else ''
                max = f"📈 {data['symbol']} дороже чем {user_id['ma']} USD" if user_id['ma'] else ''
                msg = f'{title}\n{min}\n{max}'
                await bot.send_message(chat_id=user_id['tlg_id'], text=msg, parse_mode='html')


# is digit
def is_number_repl_isdigit(s: str):
    '''Returns True if string is a number'''
    return s.replace('.', '', 1).isdigit()


# scroll inlines
async def scroll_inline(prev: int=PREV, next: int=NEXT, follows: list=[], start_row: list=[]):
    '''
    Generate scrollable inline keyboard with follow coins
    '''
    prev_text = "🤚🏻 Назад"
    next_text = "Далее ✋🏻"
    cb_data_prev = cb_data_next = 'empty'
    rows = []

    if prev > 0:
        cb_data_prev = f"prev_{prev}"
        prev_text = "⬅️ Назад"  
    if len(follows) > NEXT:
        follows = follows[:-1]
        cb_data_next = f"next_{next}"
        next_text = "Далее ➡️"

    for follow in follows:
        cb_text = f"{follow['coin_name']} < {follow['min_value']}" if follow['min_value'] else f"{follow['coin_name']} > {follow['max_value']}"
        rows.append([InlineKeyboardButton(text=f"{cb_text}", callback_data=f"empty"), InlineKeyboardButton(text=f"🗑", callback_data=f"del_{follow['id']}")])

    inlineboard = InlineKeyboardMarkup(inline_keyboard=[
            start_row,
            *rows, 
            [
                InlineKeyboardButton(text=prev_text, callback_data=cb_data_prev),
                InlineKeyboardButton(text=next_text, callback_data=cb_data_next)                   
            ]
        ]
    )
    return inlineboard


# command start
@app.message(Command('start'))
async def cmd_start(message: types.Message):
    '''
    Init command. Set bot commands and greet
    '''
    await message.answer('Привет!\nЭтот бот поможет тебе отслеживать курс криптовалют!\n')
    await cmd_help(message)
    # await cmd_my_follow(message)
 

# command help
@app.message(Command('help'))
async def cmd_help(message: types.Message):
    '''
    Help command. Show available commands
    '''
    text = '''Отправь команду /my_follow, чтобы посмотреть список отслеживаемых монет
        \nЧтобы начать отслеживать монету, воспользуйся с 🔍. Затем напиши полное или сокращенное название монеты и выбери ее из списка. После чего, укажи пороговое значение
        \nНажми на значок корзины 🗑, чтобы перестать отслеживать монету
        \nP.S. курс обновляется раз в минуту'''
    await message.answer(text)


# command my_follow
@app.message(Command('my_follow'))
async def cmd_my_follow(message: types.Message, edit_id: int=0):
    '''
    Show user followed coins
    '''
    text = '<b>Держим руку на пульсе и контролируем 👇🏻</b>\n\n'
    find = [InlineKeyboardButton(text="🔍 Найти и взять под контроль", switch_inline_query_current_chat="")]
    user_follows = await SQL.get_user_follows(tlg_id=message.from_user.id)
    if not user_follows:
        # user have no follows
        text += 'Упс.. пока ничего не контролируем. Начнем? ⤵️'
        inlineboard = InlineKeyboardMarkup(inline_keyboard=[find])
    else:
        # user have some follows
        inlineboard = await scroll_inline(follows=user_follows, start_row=find)
    if edit_id:
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=edit_id, text=text, reply_markup=inlineboard, parse_mode='html')
        return
    await message.answer(text, reply_markup=inlineboard, parse_mode='html')


# inline find coin
@app.inline_query()
async def inline_handler(query: InlineQuery):
    '''
    Find coin by name or symbol
    '''
    user_query = query.query.lower()
    result = {}
    # find coin
    for key, value in CMC.coins.items():
        if len(result) > 9:
            break
        if key.lower().startswith(user_query) or value['symbol'].lower().startswith(user_query):
            result[key] = value
    # not found
    if len(result) == 0:
        helper_find = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔍 Поиск", switch_inline_query_current_chat="")]]) 
        helper = types.InlineQueryResultArticle(
            id="wtf", 
            title="Поиск монеты", 
            description="Например: BTC или bitcoin, или ethereum...", 
            hide_url=True,
            input_message_content=input_text_message_content.InputTextMessageContent(message_text=f"Нужно выбрать из списка..."),
            reply_markup=helper_find
        )
        return await query.answer([helper], cache_time=30, is_personal=True)
    # some found
    else:
        coins = []
        for key in result:
            but_min = InlineKeyboardButton(text=f"{result[key]['symbol']}  <  USD", callback_data=f"min_{result[key]['id']}_{key}")
            but_max = InlineKeyboardButton(text=f"USD  <  {result[key]['symbol']}", callback_data=f"max_{result[key]['id']}_{key}")
            but_sign = InlineKeyboardMarkup(inline_keyboard=[[but_min, but_max]]) 
            coin = types.InlineQueryResultArticle(
                id=str(result[key]['id']),
                title=key,
                description=result[key]['symbol'],
                hide_url=True,
                input_message_content=input_text_message_content.InputTextMessageContent(
                    message_text=(f"<b>{key}</b>\nТеперь выбери условие ⤵️"),
                    parse_mode='html'
                ),
                reply_markup=but_sign
            )
            coins.append(coin)
        await query.answer(coins, cache_time=30, is_personal=True)


# callback sign min/max
@app.callback_query(F.data.startswith('min') | F.data.startswith('max'))
async def cb_sign(call: CallbackQuery):
    '''
    Callback for sign buttons
    '''
    await call.answer()
    sign, coin_id, coin_name = call.data.split("_")
    user_next_step[call.from_user.id] = {'coin_id': coin_id, 'coin_name': coin_name, 'sign': sign, 'value': 0}
    rand_int = random.randint(43210, 98765)
    rand_float = round(random.uniform(43210, 98765), 3)
    sign = '&lt;' if sign == 'min' else '&gt;'
    await bot.send_message(chat_id=call.from_user.id, text=f'<b>{coin_name} {sign} USD</b>\nИ теперь отправь пороговое значение. Например: {rand_int} или {rand_float}', parse_mode='html')


# callback empty
@app.callback_query(F.data.startswith('empty'))
async def cb_empty(call: CallbackQuery):
    '''Callback for follow coin button'''
    await call.answer()


# callback next/prev
@app.callback_query(F.data.startswith('prev') | F.data.startswith('next'))
async def cb_next_prev(call: CallbackQuery):
    await call.answer()
    direction, step = call.data.split("_")
    prev = PREV
    next = NEXT
    if direction == 'next':
        prev = int(step)
        next += prev
    else:
        next = int(step)
        prev = next - NEXT
    user_follows = await SQL.get_user_follows(tlg_id=call.from_user.id, offset=prev)
    find = [InlineKeyboardButton(text="🔍 Найти и взять под контроль", switch_inline_query_current_chat="")]
    inlineboard = await scroll_inline(prev=prev, next=next, follows=user_follows, start_row=find)
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text='<b>Держим руку на пульсе и контролируем 👇🏻</b>\n\n', reply_markup=inlineboard, parse_mode='html')


# callback del
@app.callback_query(F.data.startswith('del'))
async def cb_del(call: CallbackQuery):
    '''Callback for del follow coin'''
    await call.answer()
    row_id = call.data.split("_")[1]
    await SQL.delete_row(row_id=row_id)
    await cmd_my_follow(message=call, edit_id=call.message.message_id)


# other messages
@app.message()
async def catch_all(message: types.Message):
    '''
    Catch user messages
    '''
    user_id = message.from_user.id
    # if user just send msg
    if not message.via_bot and user_id not in user_next_step:
        text = 'Не знаешь куда податься? Лови менюшку!'
        await message.answer(text)
        await cmd_my_follow(message)
        return
    
    # if user send inline query
    if message.via_bot:
        return
    
    # if user send string instead of int/float
    value = message.text
    if not is_number_repl_isdigit(value):
        await message.answer('Нужно отправить число, например, 43210 или 98764.80918')
        return
    
    # if pretty user send int/float 
    user_next_step[user_id]['value'] = float(value)
    await SQL.insert_row(
        tlg_id=user_id,
        coin_id=user_next_step[user_id]['coin_id'],
        coin_name=user_next_step[user_id]['coin_name'],
        value=user_next_step[user_id]['value'],
        value_type=f"{user_next_step[user_id]['sign']}_value",
    )
    await message.answer(text=f'<b>{user_next_step[user_id]["coin_name"]}</b> взят под контроль', parse_mode='html') 
    del user_next_step[user_id]


# main loop
async def main():
    asyncio.create_task(update_quotes())
    await app.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
