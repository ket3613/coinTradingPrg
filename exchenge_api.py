import jwt
import hashlib
import uuid
import requests
import pandas as pd
import os
from urllib.parse import urlencode, unquote
from config import load_config

pd.set_option('display.max_columns', None)

# 환경변수에서 API 키와 URL 가져오기
config = load_config('config.yml')
access_key = config['api']['access_key']
secret_key = config['api']['secret_key']
server_url = config['api']['server_url']
market = 'KRW-SHIB'

class ExchangeApi:
    # 잔고 조회 메서드 (전체 잔고)
    def get_my_account(self):
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = f'Bearer {jwt_token}'
        headers = {'Authorization': authorization}

        res = requests.get(f"{server_url}/v1/accounts", headers=headers)
        data = res.json()
        return float(data[0]['balance'])

    # 특정 코인 (KRW-SHIB) 잔고 조회 메서드
    def get_my_account2(self):
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = f'Bearer {jwt_token}'
        headers = {'Authorization': authorization}

        res = requests.get(f"{server_url}/v1/accounts", headers=headers)
        data = res.json()

        # 예시로 KRW-SHIB 잔고를 가져옴
        for coin in data:
            if coin['currency'] == 'SHIB':  # 원하는 코인(SHIB)을 조회
                return float(coin['balance'])  # 잔고 반환

        return 0.0  # 해당 코인이 없으면 0 반환

    # 1분 봉 캔들 데이터 조회 메서드
    def get_data(self, count=30):
        params = {
            'market': market,
            'count': count,
        }
        headers = {"accept": "application/json"}
        response = requests.get(f"{server_url}/v1/candles/minutes/1", params=params, headers=headers)

        data = response.json()
        return pd.DataFrame(data)

    #주문 대기중인 정보 가져오기
    def get_open_orders(self, market, states=['wait', 'watch']):
        params = {
            'market': market,
            'states[]': states
        }

        # 쿼리 문자열 생성 및 해시화
        query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        # JWT payload
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        # JWT 토큰 생성
        jwt_token = jwt.encode(payload, secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {
            'Authorization': authorization,
        }

        # 요청 보내기
        res = requests.get(f"{server_url}/v1/orders/open", params=params, headers=headers)

        # 응답 반환
        data = res.json()
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
        authorization = f'Bearer {jwt_token}'
        headers = {'Authorization': authorization}

        res = requests.post(f"{server_url}/v1/orders", json=payload, headers=headers)
        return res.json()  # 주문 결과 반환

    def cancel_order(self, order_uuid):
        # 주문 취소에 필요한 매개변수 설정
        params = {
            'uuid': order_uuid
        }
        query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")

        # 쿼리 해시 생성
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        # JWT 토큰 생성
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorization = f'Bearer {jwt_token}'
        headers = {
            'Authorization': authorization,
        }

        # 주문 취소 요청
        res = requests.delete(f"{server_url}/v1/order", params=params, headers=headers)

        # 응답 JSON 반환
        return res.json()

    # 볼린저 밴드 전략 메서드 (변경된 부분 포함)
    def bollinger_strategy(self):
        # 데이터 가져오기 및 볼린저 밴드 계산
        doge_data = self.get_data()
        doge_data = self.calculate_bollinger_bands(doge_data)

        # 최신 가격 데이터
        latest_data = doge_data.iloc[0]

        # 보유량 확인
        coin_balance = self.get_my_account2()

        orderDate = self.get_open_orders(market,'wait')

        if not orderDate.empty:
            df = orderDate
            df['created_at'] = pd.to_datetime(df['created_at'])

            # 생성 시간을 기준으로 내림차순 정렬하여 최신 주문이 맨 위로 오도록 정렬
            df_sorted = df.sort_values(by='created_at', ascending=False)

            # bid와 ask 각각 최신 주문 한 개를 제외한 나머지 주문을 추출
            df_bid_remaining = df_sorted[df_sorted['side'] == 'bid'].iloc[1:]
            df_ask_remaining = df_sorted[df_sorted['side'] == 'ask'].iloc[1:]

            if len(df_bid_remaining) >= 2:
                for _, row in df_bid_remaining.iterrows():
                    order_uuid = row['uuid']
                    cancel_response = self.cancel_order(order_uuid)
                    print(f"Bid 주문 취소 결과: {cancel_response}")

            if len(df_ask_remaining) >= 2:
                for _, row in df_ask_remaining.iterrows():
                    order_uuid = row['uuid']
                    cancel_response = self.cancel_order(order_uuid)
                    print(f"Ask 주문 취소 결과: {cancel_response}")

        # 매도 조건 - 상단 밴드 터치 시 (보유량이 있는 경우에만 매도)
        if latest_data['trade_price'] >= latest_data['Upper'] and coin_balance > 0:
            print("상단 밴드 터치 - 매도 신호 발생")
            print(f"보유량 = {coin_balance}")
            print(f"현재 가격 = {latest_data['trade_price']}")
            print(f"상단 밴드 = {latest_data['Upper']}")
            sell_volume = coin_balance  # 보유한 모든 코인 매도
            self.place_order(market=market, side="ask", price=latest_data['trade_price'], volume=sell_volume)

        # 매수 조건 - 하단 밴드 터치 시
        elif latest_data['trade_price'] <= latest_data['Lower']:
            print("하단 밴드 터치 - 매수 신호 발생")
            print(f"현재 가격 = {latest_data['trade_price']}")
            print(f"하단 밴드 = {latest_data['Lower']}")
            tradable_balance = self.get_my_account()
            buy_volume = tradable_balance / latest_data['trade_price']
            if buy_volume >= 1:
                self.place_order(market=market, side="bid", price=latest_data['trade_price'], volume=buy_volume)
