import jwt
import hashlib
import datetime
import requests
import uuid
import pandas as pd
from urllib.parse import urlencode, unquote
from config import load_config

config = load_config('config.yml')
global_access_key = config['api']['access_key']
global_secret_key = config['api']['secret_key']
global_server_url = config['api']['server_url']

class ExchangeApi:
    def get_my_account(self):
        payload = {
            'access_key': global_access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, global_secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {
          'Authorization': authorization,
        }
        params = {}

        res = requests.get(global_server_url + '/v1/accounts', params=params, headers=headers)
        data = res.json()
        return data[0]['balance']

    def get_doge_data(count=200):
        params = {
            'market': 'KRW-DOGE',
            'count': 200,
        }
        headers = {"accept": "application/json"}
        response = requests.get(global_server_url + '/v1/candles/minutes/1', params=params, headers=headers)

        data = response.json()
        return pd.DataFrame(data)

