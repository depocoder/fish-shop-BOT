import os

import requests


def get_access_token(redis_conn):
    access_token = redis_conn.get('access_token')
    if not access_token:
        data = {'client_id': os.getenv('MOTLIN_CLIENT_ID'),
                'grant_type': 'implicit'}
        response = requests.get('https://api.moltin.com/oauth/access_token',
                                data=data)
        response.raise_for_status()
        token_info = response.json()
        time_to_expire_s = token_info['expires_in']
        access_token = token_info['access_token']
        redis_conn.set('access_token', access_token, ex=time_to_expire_s)
    return access_token


def get_element_by_id(access_token, id):
    response = requests.get(
        f'https://api.moltin.com/v2/products/{id}',
        headers={
            'Authorization': f'Bearer {access_token}',
        })
    response.raise_for_status()
    return response.json()['data']


def get_products(access_token):
    response = requests.get('https://api.moltin.com/v2/products', headers={
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    })
    response.raise_for_status()
    return response.json()['data']


def add_to_cart(access_token, quantity, item_id, chat_id):
    data = {"data": {"id": item_id,
                     "type": "cart_item", "quantity": quantity}}
    headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            }

    response = requests.post(
        f'https://api.moltin.com/v2/carts/{chat_id}/items', headers=headers,
        json=data)
    response.raise_for_status()
    return response.json()


def delete_from_cart(access_token, item_id, chat_id):
    response = requests.delete(
        f'https://api.moltin.com/v2/carts/{chat_id}/items/{item_id}',
        headers={
            'Authorization': f'Bearer {access_token}',
        })
    response.raise_for_status()


def get_cart(access_token, chat_id):

    response = requests.get(
        f'https://api.moltin.com/v2/carts/{chat_id}/items',
        headers={
            'Authorization': f'Bearer {access_token}',
        })
    response.raise_for_status()
    return response.json()


def get_image_link(access_token, image_id):
    response = requests.get(
        f'https://api.moltin.com/v2/files/{image_id}',
        headers={
            'Authorization': f'Bearer {access_token}'})
    response.raise_for_status()
    return response.json()


def create_customer(access_token, chat_id, email):
    headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            }

    data = {"data": {
        "type": "customer",
        "name": chat_id,
        "email": email,
        "password": "erwedasdwqrwrqwead"}}
    response = requests.post(
        'https://api.moltin.com/v2/customers',
        headers=headers, json=data)
    response.raise_for_status()
