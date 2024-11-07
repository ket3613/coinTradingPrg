import jwt
import hashlib
import uuid
import requests
import pandas as pd
import os
from urllib.parse import urlencode, unquote
from config import load_config

# 환경변수에서 API 키와 URL 가져오기
config = load_config('config.yml')
access_key = config['api']['access_key']
secret_key = config['api']['secret_key']
server_url = config['api']['server_url']
market = 'KRW-SHIB'

class ExchangeApi:
    # 잔고 조회 메서드
    def get_my_account(self):
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {
            'Authorization': authorization,
        }
        params = {}

        res = requests.get(server_url + '/v1/accounts', params=params, headers=headers)
        data = res.json()
        return float(data[0]['balance'])

    def get_my_account2(self):
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {'Authorization': authorization}

        res = requests.get(server_url + '/v1/accounts', headers=headers)
        data = res.json()

        # 예시로 KRW-SHIB 잔고를 가져옴
        for coin in data:
            if coin['currency'] == 'SHIB':  # 원하는 코인(SHIB)을 조회
                return float(coin['balance'])  # 잔고 반환

        return 0.0  # 해당 코인이 없으면 0 반환

    # 데이터 조회 메서드 (1분 봉 캔들 데이터)
    def get_data(self, count=30):
        params = {
            'market': market,
            'count': count,
        }
        headers = {"accept": "application/json"}
        response = requests.get(server_url + '/v1/candles/minutes/1', params=params, headers=headers)

        data = response.json()
        return pd.DataFrame(data)

    # 볼린저 밴드 계산 메서드
    @staticmethod
    def calculate_bollinger_bands(data, window=20):
        data['MA20'] = data['trade_price'].rolling(window=window).mean()
        data['STD'] = data['trade_price'].rolling(window=window).std()

        data['Upper'] = data['MA20'] + (data['STD'] * 2)
        data['Lower'] = data['MA20'] - (data['STD'] * 2)
        data = data.dropna(subset=['MA20', 'STD', 'Upper', 'Lower'])
        return data

    # 주문 요청 메서드
    def place_order(self, market, side, price, volume, ord_type="limit"):
        params = {
            'market': market,
            'side': side,
            'ord_type': ord_type,
            'price': str(price),
            'volume': str(volume),
        }
        query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {'Authorization': authorization}

        response = requests.post(server_url + '/v1/orders', json=params, headers=headers)
        return response.json()

    # 볼린저 밴드 전략 메서드
    def bollinger_strategy(self):
        # 데이터 가져오기 및 볼린저 밴드 계산
        doge_data = self.get_data()
        doge_data = self.calculate_bollinger_bands(doge_data)

        # 최신 가격 데이터
        latest_data = doge_data.iloc[0]

        # 보유량 확인
        coin_balance = self.get_my_account2()
        #print("보유량 = " + str(coin_balance))

        # 매도 조건 - 상단 밴드 터치 시 (보유량이 있는 경우에만 매도)
        if latest_data['trade_price'] >= latest_data['Upper'] and coin_balance > 0:
            print("상단 밴드 터치 - 매도 신호 발생")
            print("보유량 = " + str(coin_balance))
            print(latest_data['trade_price'])
            print(latest_data['Upper'])
            sell_volume = coin_balance  # 보유한 모든 코인 매도
            self.place_order(market=market, side="ask", price=latest_data['trade_price'], volume=sell_volume)

        # 매수 조건 - 하단 밴드 터치 시
        elif latest_data['trade_price'] <= latest_data['Lower']:
            print("하단 밴드 터치 - 매수 신호 발생")
            print(latest_data['trade_price'])
            print(latest_data['Lower'])
            tradable_balance = self.get_my_account() * 0.7
            buy_volume = tradable_balance / latest_data['trade_price']
            if buy_volume >= 1:
                self.place_order(market=market, side="bid", price=latest_data['trade_price'], volume=buy_volume)
            else:
                print("매수할 수 있는 최소 수량 미달로 매수하지 않음.")
