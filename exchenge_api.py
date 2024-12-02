import jwt
import hashlib
import uuid
import requests
import pandas as pd
import math
import os
from urllib.parse import urlencode, unquote
import pyupbit
from config import load_config

pd.set_option('display.max_columns', None)

# 환경변수에서 API 키와 URL 가져오기
config = load_config('config.yml')
access_key = config['services']['coin-trading-bot']['environment']['ACCESS_KEY']
secret_key = config['services']['coin-trading-bot']['environment']['SECRET_KEY']
server_url = config['services']['coin-trading-bot']['environment']['SERVER_URL']
market = 'KRW-DOGE'

class ExchangeApi:

    # 30분 봉 캔들 데이터 조회 메서드
    def get_data(self, count=30):
        params = {
            'market': market,
            'count': count,
        }
        headers = {"accept": "application/json"}
        response = requests.get(f"{server_url}/v1/candles/minutes/30", params=params, headers=headers)

        data = response.json()
        return pd.DataFrame(data)

    # 볼린저 밴드 계산 메서드
    @staticmethod
    def calculate_bollinger_bands(data, window=20):
        data['MA20'] = data['trade_price'].rolling(window=window).mean()
        data['STD'] = data['trade_price'].rolling(window=window).std()

        data['Upper'] = data['MA20'] + (data['STD'] * 2.2)
        data['Lower'] = data['MA20'] - (data['STD'] * 2.0)
        data = data.dropna(subset=['MA20', 'STD', 'Upper', 'Lower'])
        return data

    # 볼린저 밴드 전략 메서드 (변경된 부분 포함)
    def bollinger_strategy(self):
        doge_data = self.get_data()
        result_doge_data = self.calculate_bollinger_bands(doge_data)
        latest_data = result_doge_data.iloc[0]
        upper_volume = round(latest_data['Upper'], 6)
        lower_volume = round(latest_data['Lower'], 6)

        # 코인 현재 가격 가져오기
        trade_price = pyupbit.get_current_price(market)

        # PyUpbit 객체 생성
        upbit = pyupbit.Upbit(access_key, secret_key)

        if lower_volume >= trade_price:
            print("===하단 터치===")
            print("lower_volume = " + str(lower_volume) + "  |   trade_price = " + str(trade_price))
            balance = float(int(float(upbit.get_balance("KRW"))))
            if balance > 5100.0:
                print("잔고 5100 이상 ")
                usable_balance = balance * (1 - 0.01)
                volume = usable_balance / trade_price
                volume = "{:.4f}".format(volume)
                ret = upbit.buy_limit_order(market, trade_price, volume)
                print(ret)

        elif upper_volume <= trade_price:
            print("===상단 터치===")
            print("upper_volume = " + str(upper_volume) + "  |   trade_price = " + str(trade_price))
            coin_balance = upbit.get_balance(market)
            if coin_balance >= 1.0:
                # 매수 평균가 가져오기
                avg_buy_price = float(upbit.get_avg_buy_price(market))
                # 현재 가격이 매수 평균가보다 높을 때만 매도
                if trade_price > avg_buy_price:
                    ret = upbit.sell_limit_order(market, round(upper_volume, 4), round(coin_balance, 8))
                    print("매도 주문 결과: ", ret)
                else:
                    print("손해 방지: 매도하지 않습니다.")
