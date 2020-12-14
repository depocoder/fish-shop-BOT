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


def get_id_item(access_token):
    response = requests.get('https://api.moltin.com/v2/products', headers={
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    })
    return json.loads(response.text)['data'][0]['id']
