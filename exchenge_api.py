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

    # 활성화된 주문 조회 메서드
    def get_active_orders(self):
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {
            'Authorization': authorization,
        }
        params = {
            'market': market,
            'state': 'wait',  # 'wait'는 대기 중인 주문을 의미
        }

        res = requests.get(server_url + '/v1/orders', params=params, headers=headers)
        return res.json()  # 대기 중인 주문 리스트 반환

    def remove_duplicate_buy_orders(self):
        active_orders = self.get_active_orders()

        # 매수 주문만 필터링
        buy_orders = [order for order in active_orders if order['side'] == 'bid']

        if buy_orders:
            # 가장 최근 주문을 찾기 (최신 주문 = 가장 큰 created_at)
            latest_order = max(buy_orders, key=lambda order: order['created_at'])

            # 가장 최근 주문을 제외한 나머지 주문 취소
            for order in buy_orders:
                if order['uuid'] != latest_order['uuid']:
                    print(f"취소 주문 ID: {order['uuid']}, 가격: {order['price']}")
                    self.cancel_order(order['uuid'])

            print(f"최신 매수 주문 유지: 주문 ID: {latest_order['uuid']}, 가격: {latest_order['price']}")

    # 매도 주문도 중복 제거
    def remove_duplicate_sell_orders(self):
        active_orders = self.get_active_orders()

        # 매도 주문만 필터링
        sell_orders = [order for order in active_orders if order['side'] == 'ask']

        if sell_orders:
            # 가장 최근 매도 주문을 찾기
            latest_order = max(sell_orders, key=lambda order: order['created_at'])

            # 가장 최근 매도 주문을 제외한 나머지 주문 취소
            for order in sell_orders:
                if order['uuid'] != latest_order['uuid']:
                    print(f"취소 매도 주문 ID: {order['uuid']}, 가격: {order['price']}")
                    self.cancel_order(order['uuid'])

            print(f"최신 매도 주문 유지: 주문 ID: {latest_order['uuid']}, 가격: {latest_order['price']}")

    # 주문 취소 메서드
    def cancel_order(self, order_id):
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {
            'Authorization': authorization,
        }
        params = {
            'uuid': order_id,
        }

        res = requests.delete(server_url + '/v1/order', params=params, headers=headers)
        return res.json()  # 주문 취소 결과 반환

    # 주문 실행 메서드
    def place_order(self, market, side, price, volume):
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'market': market,
            'side': side,  # 'bid' for buy, 'ask' for sell
            'price': str(price),
            'volume': str(volume),
            'ord_type': 'limit',  # 'limit' or 'market'
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {
            'Authorization': authorization,
        }

        res = requests.post(server_url + '/v1/orders', json=payload, headers=headers)
        return res.json()  # 주문 결과 반환

    # 볼린저 밴드 전략 메서드
    def bollinger_strategy(self):
        # 데이터 가져오기 및 볼린저 밴드 계산
        doge_data = self.get_data()
        doge_data = self.calculate_bollinger_bands(doge_data)

        # 최신 가격 데이터
        latest_data = doge_data.iloc[0]

        # 보유량 확인
        coin_balance = self.get_my_account2()

        # 매도 조건 - 상단 밴드 터치 시 (보유량이 있는 경우에만 매도)
        if latest_data['trade_price'] >= latest_data['Upper'] and coin_balance > 0:
            print("상단 밴드 터치 - 매도 신호 발생")
            print("보유량 = " + str(coin_balance))
            print(latest_data['trade_price'])
            print(latest_data['Upper'])
            sell_volume = coin_balance  # 보유한 모든 코인 매도
            self.place_order(market=market, side="ask", price=latest_data['trade_price'], volume=sell_volume)
            self.remove_duplicate_sell_orders()  # 매도 주문 중복 제거

        # 매수 조건 - 하단 밴드 터치 시
        elif latest_data['trade_price'] <= latest_data['Lower']:
            print("하단 밴드 터치 - 매수 신호 발생")
            print(latest_data['trade_price'])
            print(latest_data['Lower'])
            tradable_balance = self.get_my_account() * 0.7  # 70%만 사용
            buy_volume = tradable_balance / latest_data['trade_price']
            if buy_volume >= 1:
                self.place_order(market=market, side="bid", price=latest_data['trade_price'], volume=buy_volume)
                self.remove_duplicate_buy_orders()  # 매수 주문 중복 제거
            else:
                print("매수할 수 있는 최소 수량 미달로 매수하지 않음.")
