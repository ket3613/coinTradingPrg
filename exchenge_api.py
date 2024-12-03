import json
import os
import pickle

import numpy as np
import pandas as pd
import pyupbit
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.models import Sequential, load_model

# PyUpbit API 설정
market = "KRW-DOGE"

class ExchangeApi:
    def __init__(self):
        self.model_file = "lstm_model.h5"
        self.scaler_file = "scaler.pkl"
        self.candle_file = "pretrained_candle_data.csv"
        self.trading_file = "trading_data.json"

        # 모델, 스케일러, 데이터 복원
        self.lstm_model = self.load_lstm_model()
        self.scaler = self.load_scaler()
        self.candle_data = self.load_candle_data()
        self.trading_data = self.load_trading_data()

        # 학습된 모델이 없을 경우 새로 학습
        if self.lstm_model is None or self.scaler is None:
            self.train_lstm_model()

    def fetch_longterm_data(self, market="KRW-DOGE", interval="minute30", days=90):
        """긴 기간의 캔들 데이터를 수집."""
        all_data = []
        for i in range(days):
            to_date = pd.Timestamp.now() - pd.Timedelta(days=i)
            data = pyupbit.get_ohlcv(market, interval=interval, to=to_date)
            if data is not None:
                all_data.append(data)

        # 데이터 합치기 및 정렬
        result = pd.concat(all_data).sort_index()
        return result

    def save_candle_data(self, data):
        """수집한 캔들 데이터를 파일로 저장."""
        data.to_csv(self.candle_file, index=True)
        print(f"캔들 데이터 저장 완료: {self.candle_file}")

    def load_candle_data(self):
        """저장된 캔들 데이터를 불러옴."""
        try:
            data = pd.read_csv(self.candle_file, index_col=0)
            print(f"캔들 데이터 복원 완료: {self.candle_file}")
            return data
        except FileNotFoundError:
            print(f"{self.candle_file} 파일이 없습니다. 데이터를 새로 수집해야 합니다.")
            return None

    def update_candle_data(self, market="KRW-DOGE"):
        """기존 데이터에 새로운 캔들 데이터를 추가."""
        existing_data = self.load_candle_data()
        latest_data = self.fetch_longterm_data(market=market, interval="minute30", days=1)

        if existing_data is not None and latest_data is not None:
            updated_data = pd.concat([existing_data, latest_data]).drop_duplicates().sort_index()
            self.save_candle_data(updated_data)
            print("캔들 데이터 업데이트 완료.")
        else:
            print("데이터 업데이트 실패.")

    def prepare_training_data(self, data, window_size=30):
        """LSTM 학습 데이터를 준비."""
        scaled_data = self.scaler.fit_transform(data[['open', 'high', 'low', 'close', 'volume']])

        X, y = [], []
        for i in range(len(scaled_data) - window_size):
            X.append(scaled_data[i:i + window_size])
            future_price = scaled_data[i + window_size, 3]  # 종가
            current_price = scaled_data[i + window_size - 1, 3]
            if future_price >= current_price * 1.05:
                y.append(1)  # 익절 신호
            elif future_price <= current_price * 0.8:
                y.append(-1)  # 손절 신호
            else:
                y.append(0)  # 보유 신호

        return np.array(X), np.array(y)

    def train_lstm_model(self):
        """LSTM 모델 학습 및 저장."""
        data = self.load_candle_data()
        if data is None:
            print("캔들 데이터를 먼저 수집해야 합니다.")
            return

        X, y = self.prepare_training_data(data)

        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(X.shape[1], X.shape[2])),
            LSTM(50),
            Dense(1, activation='tanh')
        ])
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        model.fit(X, y, epochs=10, batch_size=32, validation_split=0.2)

        self.lstm_model = model
        self.save_lstm_model()
        self.save_scaler()
        print("LSTM 모델 학습 및 저장 완료.")

    def predict_signal(self, live_data):
        """실시간 데이터를 통한 매매 신호 예측."""
        live_data_scaled = self.scaler.transform(live_data[['open', 'high', 'low', 'close', 'volume']])
        input_data = np.expand_dims(live_data_scaled[-30:], axis=0)
        prediction = self.lstm_model.predict(input_data)
        return int(np.round(prediction[0][0]))

    def lstm_trading_logic(self):
        """LSTM 기반 매매 로직."""
        upbit = pyupbit.Upbit("ACCESS_KEY", "SECRET_KEY")

        # 실시간 데이터 가져오기
        live_data = self.fetch_longterm_data(market=market, interval="minute30", days=1)
        signal = self.predict_signal(live_data)

        # 매매 로직
        trade_price = pyupbit.get_current_price(market)
        krw_balance = upbit.get_balance("KRW")
        coin_balance = upbit.get_balance(market)

        if signal == 1:  # 익절 신호
            if coin_balance > 0:
                upbit.sell_market_order(market, coin_balance)
                print("익절 매도")
        elif signal == -1:  # 손절 신호
            if coin_balance > 0:
                upbit.sell_market_order(market, coin_balance)
                print("손절 매도")
        elif signal == 0:  # 보유 신호
            if krw_balance >= 200000:  # 여유 금액이 20만 원 이상인 경우 매수
                volume = 200000 / trade_price
                upbit.buy_market_order(market, 200000)
                print("매수 완료")

    # 저장 및 복원
    def save_lstm_model(self):
        self.lstm_model.save(self.model_file)
        print(f"LSTM 모델 저장 완료: {self.model_file}")

    def load_lstm_model(self):
        if os.path.exists(self.model_file):
            print(f"LSTM 모델 복원 완료: {self.model_file}")
            return load_model(self.model_file)
        print("LSTM 모델 파일이 없습니다.")
        return None

    def save_scaler(self):
        with open(self.scaler_file, "wb") as f:
            pickle.dump(self.scaler, f)
        print(f"스케일러 저장 완료: {self.scaler_file}")

    def load_scaler(self):
        if os.path.exists(self.scaler_file):
            with open(self.scaler_file, "rb") as f:
                scaler = pickle.load(f)
            print(f"스케일러 복원 완료: {self.scaler_file}")
            return scaler
        print("스케일러 파일이 없습니다.")
        return MinMaxScaler()

    def save_trading_data(self):
        with open(self.trading_file, "w") as f:
            json.dump(self.trading_data, f)
        print(f"트레이딩 데이터 저장 완료: {self.trading_file}")

    def load_trading_data(self):
        if os.path.exists(self.trading_file):
            with open(self.trading_file, "r") as f:
                data = json.load(f)
            print(f"트레이딩 데이터 복원 완료: {self.trading_file}")
            return data
        print("트레이딩 데이터 파일이 없습니다.")
        return {"balance": 100000, "avg_buy_price": 0, "trades": []}
