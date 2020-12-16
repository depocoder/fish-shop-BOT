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
    get_products, get_access_token, get_element_by_id, get_link_image)


logger = logging.getLogger(__name__)


def format_message(product_info):
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


def start(redis_conn, update: Update, context: CallbackContext):
    keyboard = []
    access_token = get_access_token(redis_conn)
    for product in get_products(access_token):
        keyboard.append([InlineKeyboardButton(
            product['name'], callback_data=product['id'])])

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        text='Please choose:', chat_id=update.effective_user.id,
        reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_description(redis_conn, update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.message.delete()
    start(redis_conn, update, context)
    return 'HANDLE_MENU'


def handle_menu(redis_conn, update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    access_token = get_access_token(redis_conn)
    product_info = get_element_by_id(access_token, query.data)
    image_id = product_info['relationships']['main_image']['data']['id']
    text_mess = format_message(product_info)
    image_link = get_link_image(access_token, image_id)['data']['link']['href']
    keyboard = [[InlineKeyboardButton('Назад', callback_data='Назад')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_user.id
    message_id = context.bot.send_photo(
        chat_id=chat_id, photo=image_link,
        caption=text_mess, reply_markup=reply_markup)['message_id']
    query.message.delete()
    return "HANDLE_DESCRIPTION"


def echo(update: Update, context: CallbackContext):
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def handle_users_reply(redis_conn, update: Update, context: CallbackContext):
    p_start = partial(start, redis_conn)
    p_handle_menu = partial(handle_menu, redis_conn)
    p_handle_description = partial(handle_description, redis_conn)
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
