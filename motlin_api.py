import os
import json

import redis
import requests
from dotenv import load_dotenv


def get_access_token(redis_conn):
    access_token = redis_conn.get('access_token')
    if not access_token:
        data = {'client_id': os.getenv('MOTLIN_CLIENT_ID'),
                'grant_type': 'implicit'}
        response = requests.get('https://api.moltin.com/oauth/access_token',
                                data=data)
        response.raise_for_status()
        decoded_response = json.loads(response.text)
        time_to_expire_s = decoded_response['expires_in']
        access_token = decoded_response['access_token']
        redis_conn.set('access_token', access_token, ex=time_to_expire_s)
    return access_token


def get_element_by_id(access_token, id):
    response = requests.get(
        f'https://api.moltin.com/v2/products/{id}',
        headers={
            'Authorization': f'Bearer {access_token}',
        })
    response.raise_for_status()
    return json.loads(response.text)['data']


def get_products(access_token):
    response = requests.get('https://api.moltin.com/v2/products', headers={
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    })
    response.raise_for_status()
    return json.loads(response.text)['data']


def add_to_cart(access_token):
    headers = {
        'Authorization': 'Bearer XXXX',
        'Content-Type': 'application/json',
        }
    item_id = get_products(access_token)[0]['id']
    data = {"data": {"id": item_id,
                     "type": "cart_item", "quantity": 1}}
    headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            }

    response = requests.post(
        'https://api.moltin.com/v2/carts/:reference/items', headers=headers,
        data=json.dumps(data))
    response.raise_for_status()
    return response.text


def download_image_by_id(access_token, image_id):
    response = requests.get(
        f'https://api.moltin.com/v2/files/{image_id}',
        headers={
            'Authorization': f'Bearer {access_token}'})
    response.raise_for_status()


if __name__ == "__main__":
    load_dotenv()
    redis_conn = redis.Redis(
        host=os.getenv('REDIS_HOST'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), db=0, decode_responses=True)
