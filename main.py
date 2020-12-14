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
