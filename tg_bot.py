import os
import logging
from functools import partial
import textwrap
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext)
import redis

from motlin_api import (
    get_products, get_access_token, get_element_by_id,
    get_link_image, add_to_cart, get_cart, delete_from_cart)


logger = logging.getLogger(__name__)


def format_description(product_info):
    name = product_info['name']
    description = product_info['description']
    price = product_info['meta']['display_price']['with_tax']['formatted']
    weight = product_info['weight']['kg']
    text_mess = (
        f'''\
        {name}

        {price} price per kg
        {weight}kg on stock

        {description}
        ''')
    return textwrap.dedent(text_mess)


def format_cart(cart):
    filtred_cart = []
    fish_names_and_ids = []
    for fish in cart['data']:
        filtred_cart.append({
            'name': fish['name'],
            "description": fish['description'],
            'price_per_kg': fish['meta']['display_price']['without_tax']['unit']['formatted'],
            'total': fish['meta']['display_price']['without_tax']['value']['formatted'],
            'quantity': fish['quantity']

        })
        fish_names_and_ids.append([fish["name"], fish["id"]])
    total_to_pay = cart['meta']['display_price']['without_tax']['formatted']
    text_message = ''
    for fish in filtred_cart:
        text_message += (
            f'''\

            {fish["name"]}
            {fish['description']}
            {fish['price_per_kg']} price per kg
            {fish['quantity']}kg in cart for {fish['total']}
            ''')
    text_message += f'{total_to_pay}'
    return textwrap.dedent(text_message), fish_names_and_ids


def start(redis_conn, update: Update, context: CallbackContext):
    keyboard = []
    access_token = get_access_token(redis_conn)
    for product in get_products(access_token):
        keyboard.append([InlineKeyboardButton(
            product['name'], callback_data=product['id'])])
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='Корзина')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        text='Please choose:', chat_id=update.effective_user.id,
        reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_cart(redis_conn, update: Update, context: CallbackContext):
    access_token = get_access_token(redis_conn)
    chat_id = update.effective_user.id
    cart = get_cart(access_token, chat_id)
    keyboard = []
    if cart['data']:
        text_message, fish_names_and_ids = format_cart(cart)
        for fish in fish_names_and_ids:
            keyboard.append(
                [InlineKeyboardButton(
                    f'Убрать из корзины {fish[0]}',
                    callback_data=f'Убрать|{fish[1]}')])
    else:
        text_message = 'Ваша корзина пуста :C'
    keyboard.append([InlineKeyboardButton('Назад', callback_data='Назад')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        text=text_message, chat_id=chat_id, reply_markup=reply_markup)
    return "HANDLE_DESCRIPTION"


def handle_description(redis_conn, update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    access_token = get_access_token(redis_conn)
    chat_id = update.effective_user.id
    if query.data == 'Назад':
        start(redis_conn, update, context)
        query.message.delete()
        return 'HANDLE_MENU'
    elif query.data == 'Корзина':
        handle_cart(redis_conn, update, context)
        query.message.delete()
        return "HANDLE_DESCRIPTION"
    elif 'Убрать' in query.data:
        item_id = query.data.split("|")[1]
        delete_from_cart(access_token, item_id, chat_id)
        handle_cart(redis_conn, update, context)
        query.message.delete()
        return "HANDLE_DESCRIPTION"
    quantity, item_id = query.data.split('|')
    add_to_cart(access_token, int(quantity), item_id, chat_id)
    context.bot.send_message(
        text='added', chat_id=chat_id)
    return 'HANDLE_DESCRIPTION'


def handle_menu(redis_conn, update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.message.delete()
    if query.data == 'Корзина':
        handle_cart(redis_conn, update, context)
        return "HANDLE_DESCRIPTION"
    access_token = get_access_token(redis_conn)
    product_info = get_element_by_id(access_token, query.data)
    image_id = product_info['relationships']['main_image']['data']['id']
    text_mess = format_description(product_info)
    image_link = get_link_image(access_token, image_id)['data']['link']['href']
    keyboard = [
        [InlineKeyboardButton('Назад', callback_data='Назад')],
        [
            InlineKeyboardButton('1 кг', callback_data=f'1|{query.data}'),
            InlineKeyboardButton('5 кг', callback_data=f'5|{query.data}'),
            InlineKeyboardButton('10 кг', callback_data=f'10|{query.data}')
            ],
        [InlineKeyboardButton('Корзина', callback_data='Корзина')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_photo(
        chat_id=update.effective_user.id, photo=image_link,
        caption=text_mess, reply_markup=reply_markup)['message_id']
    return "HANDLE_DESCRIPTION"


def echo(update: Update, context: CallbackContext):
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def handle_users_reply(redis_conn, update: Update, context: CallbackContext):
    p_start = partial(start, redis_conn)
    p_handle_menu = partial(handle_menu, redis_conn)
    p_handle_description = partial(handle_description, redis_conn)
    p_handle_cart = partial(handle_cart, redis_conn)
    if update.message:
        user_reply = update.message.text
    elif update.callback_query:
        user_reply = update.callback_query.data
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = context.user_data.get('state')

    states_functions = {
        'START': p_start,
        'ECHO': echo,
        'HANDLE_MENU': p_handle_menu,
        'HANDLE_DESCRIPTION': p_handle_description,
        'HANDLE_CART': p_handle_cart,
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(update, context)
        context.user_data.update({"state": next_state})
    except Exception as err:
        print(err)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    load_dotenv()
    redis_conn = redis.Redis(
        host=os.getenv('REDIS_HOST'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), db=0, decode_responses=True)
    p_handle_users_reply = partial(handle_users_reply, redis_conn)
    p_handle_menu = partial(handle_menu, redis_conn)
    updater = Updater(token=os.getenv("TG_TOKEN"), use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(p_handle_users_reply))
    updater.dispatcher.add_handler(CallbackQueryHandler(p_handle_menu))
    dispatcher.add_handler(MessageHandler(Filters.text, p_handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', p_handle_users_reply))
    updater.start_polling()
