import os
import json

import requests
from dotenv import load_dotenv


def get_access_token():
    response = requests.get('https://api.moltin.com/oauth/access_token', data={
        'client_id': os.getenv('MOTLIN_CLIENT_ID'),
        'grant_type': 'implicit'
    })
    return json.loads(response.text)['access_token']


def get_items(access_token):
    response = requests.get('https://api.moltin.com/v2/products', headers={
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    })
    return json.loads(response.text)['data']


def add_to_cart(access_token):
    headers = {
        'Authorization': 'Bearer XXXX',
        'Content-Type': 'application/json',
        }
    item_id = get_items(access_token)[0]['id']
    data = {"data": {"id": item_id,
                     "type": "cart_item", "quantity": 1}}
    headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            }

    response = requests.post(
        'https://api.moltin.com/v2/carts/:reference/items', headers=headers,
        data=json.dumps(data))


if __name__ == "__main__":
    load_dotenv()
    access_token = get_access_token()
    add_to_cart(access_token)
