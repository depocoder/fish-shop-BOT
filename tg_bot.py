import os
import logging
import textwrap

from validate_email import validate_email
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, MessageHandler, CallbackContext)
import redis

from motlin_api import (
    get_products, get_access_token, get_element_by_id,
    get_image_link, add_to_cart, get_cart, delete_from_cart, create_customer)


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
    fish_names = []
    fish_ids = []
    for fish in cart['data']:
        filtred_cart.append({
            'name': fish['name'],
            "description": fish['description'],
            'price_per_kg': fish['meta']['display_price']['without_tax']['unit']['formatted'],
            'total': fish['meta']['display_price']['without_tax']['value']['formatted'],
            'quantity': fish['quantity']

        })
        fish_names.append(fish["name"])
        fish_ids.append(fish["id"])
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
    return textwrap.dedent(text_message), fish_names, fish_ids


def start(update: Update, context: CallbackContext):
    keyboard = []
    access_token = get_access_token(redis_conn)
    keyboard_product = [
        [InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in get_products(access_token)]
    keyboard += keyboard_product
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='Корзина')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        text='Пожалуйста выберите: ', chat_id=update.effective_user.id,
        reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_cart(update: Update, context: CallbackContext):
    access_token = get_access_token(redis_conn)
    chat_id = update.effective_user.id
    cart = get_cart(access_token, chat_id)
    keyboard = []
    keyboard.append([InlineKeyboardButton('В меню', callback_data='В меню')])
    if cart['data']:
        text_message, fish_names, fish_ids = format_cart(cart)
        for name_fish, id_fish in zip(fish_names, fish_ids):
            keyboard.append(
                [InlineKeyboardButton(
                    f'Убрать из корзины {name_fish}',
                    callback_data=f'Убрать|{id_fish}')])
        keyboard.append([InlineKeyboardButton(
            'Оплатить', callback_data='Оплатить')])

    else:
        text_message = 'Ваша корзина пуста :C'
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        text=text_message, chat_id=chat_id, reply_markup=reply_markup)
    return "HANDLE_DESCRIPTION"


def handle_description(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    access_token = get_access_token(redis_conn)
    chat_id = update.effective_user.id
    if query.data == 'В меню':
        start(update, context)
        query.message.delete()
        return 'HANDLE_MENU'
    elif query.data == 'Корзина':
        handle_cart(update, context)
        query.message.delete()
        return "HANDLE_DESCRIPTION"
    elif query.data == 'Оплатить':
        query.message.delete()
        context.bot.send_message(
            text='Пожалуйста укажите ваш email пример "myemail@gmail.com"',
            chat_id=chat_id)
        return "WAITING_EMAIL"
    elif 'Убрать' in query.data:
        item_id = query.data.split("|")[1]
        delete_from_cart(access_token, item_id, chat_id)
        handle_cart(update, context)
        query.message.delete()
        return "HANDLE_DESCRIPTION"
    quantity, item_id = query.data.split('|')
    add_to_cart(access_token, int(quantity), item_id, chat_id)
    context.bot.send_message(
        text='added', chat_id=chat_id)
    return 'HANDLE_DESCRIPTION'


def handle_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.message.delete()
    if query.data == 'Корзина':
        handle_cart(update, context)
        return "HANDLE_DESCRIPTION"
    access_token = get_access_token(redis_conn)
    product_info = get_element_by_id(access_token, query.data)
    image_id = product_info['relationships']['main_image']['data']['id']
    text_mess = format_description(product_info)
    image_link = get_image_link(access_token, image_id)['data']['link']['href']
    keyboard = [
        [InlineKeyboardButton('В меню', callback_data='В меню')],
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


def waiting_email(update: Update, context: CallbackContext):
    users_reply = update.message.text
    is_valid = validate_email(users_reply)
    if is_valid:
        access_token = get_access_token(redis_conn)
        update.message.reply_text(
            f"Вы прислали мне эту почту - {users_reply}. Мы скоро свяжемся.")
        create_customer(
            access_token, str(update.effective_user.id), users_reply)
        start(update, context)
        return "HANDLE_DESCRIPTION"
    update.message.reply_text(f"Ошибка! неверный email - '{users_reply}'")
    return "WAITING_EMAIL"


def handle_users_reply(update: Update, context: CallbackContext):
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
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email,
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    context.user_data.update({"state": next_state})


def error_handler(update: Update, context: CallbackContext):
    logger.error(
        msg="Exception while handling an update:", exc_info=context.error)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    load_dotenv()
    redis_conn = redis.Redis(
        host=os.getenv('REDIS_HOST'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), db=0, decode_responses=True)
    updater = Updater(token=os.getenv("TG_TOKEN"), use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(error_handler)
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_menu))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
