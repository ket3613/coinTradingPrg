import pyupbit
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import pandas_ta as ta
import requests
import os
import pickle
from transformers import pipeline
import asyncio


class ExchangeApi:
    def __init__(self, market="KRW-DOGE"):
        """1단계: 초기화 및 모델 로드"""
        self.market = market
        self.model_file = "models/lstm_model.h5"
        self.scaler_file = "models/scaler.pkl"
        self.candle_file = "data/candle_data.csv"
        self.lstm_model = None
        self.rf_model = None
        self.xgb_model = None
        self.scaler = MinMaxScaler()
        self.sentiment_pipeline = pipeline("sentiment-analysis")
        self.load_models()

    # 데이터 관련 메서드
    def fetch_latest_data(self):
        """2단계: 최근 캔들 데이터 가져오기"""
        return pyupbit.get_ohlcv(self.market, interval="minute30", count=1)

    def save_data_parquet(self, data):
        """3단계: 수집한 데이터를 Parquet 형식으로 저장"""
        file_path = self.candle_file.replace(".csv", ".parquet")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        data.to_parquet(file_path, engine="pyarrow")
        print(f"데이터 저장 완료: {file_path}")

    # 기술 지표 계산
    def calculate_indicators(self, data):
        """4단계: 기술 지표 계산 (RSI, MACD, VWAP)"""
        data["RSI"] = ta.rsi(data["close"])
        macd = ta.macd(data["close"])
        data["MACD"] = macd["MACD_12_26_9"]
        data["Signal_Line"] = macd["MACDs_12_26_9"]
        data["VWAP"] = ta.vwap(data["high"], data["low"], data["close"], data["volume"])
        return data

    # 모델 관련 메서드
    def load_models(self):
        """5단계: 저장된 모델 로드 (LSTM, Scaler)"""
        if os.path.exists(self.model_file):
            self.lstm_model = load_model(self.model_file)
            print("LSTM 모델 로드 완료")
        else:
            print("LSTM 모델이 없습니다.")

        if os.path.exists(self.scaler_file):
            with open(self.scaler_file, "rb") as f:
                self.scaler = pickle.load(f)
            print("스케일러 로드 완료")

    def predict_signal(self, live_data):
        """6단계: 앙상블 예측 신호 생성"""
        live_data_scaled = self.scaler.transform(live_data)
        input_data = np.expand_dims(live_data_scaled[-30:], axis=0)

        # LSTM 예측
        lstm_pred = int(np.round(self.lstm_model.predict(input_data)[0][0]))

        # Random Forest 예측
        rf_pred = self.rf_model.predict(live_data_scaled)

        # XGBoost 예측
        xgb_pred = self.xgb_model.predict(live_data_scaled)

        # 최종 신호 (가중 평균)
        final_signal = (lstm_pred * 0.5) + (rf_pred * 0.3) + (xgb_pred * 0.2)
        return int(np.sign(final_signal))

    # 뉴스 감성 분석
    def fetch_sentiment(self, text):
        """7단계: Transformer 기반 뉴스 감성 분석"""
        result = self.sentiment_pipeline(text)
        return result[0]["label"], result[0]["score"]

    # 매매 로직
    def execute_trade(self, signal, upbit):
        """8단계: PyUpbit API를 통한 매수/매도 실행"""
        current_price = pyupbit.get_current_price(self.market)
        if signal == 1:
            krw_balance = upbit.get_balance("KRW")
            if krw_balance > 200000:
                upbit.buy_market_order(self.market, 200000)
                print(f"매수 완료: {self.market}")
        elif signal == -1:
            coin_balance = upbit.get_balance(self.market)
            if coin_balance > 0:
                upbit.sell_market_order(self.market, coin_balance)
                print(f"매도 완료: {self.market}")
        else:
            print("보유 유지")

    # 동적 스케줄 관리
    def dynamic_schedule_interval(self, volatility):
        """9단계: 변동성에 따라 스케줄 간격 조정"""
        if volatility > 0.05:
            return 5  # 높은 변동성일 때
        else:
            return 30  # 낮은 변동성일 때

    # 조건 기반 실행
    def should_trade(self, latest_data):
        """10단계: 매매 실행 조건 확인"""
        recent_change = abs(latest_data['close'][-1] - latest_data['close'][-2])
        return recent_change / latest_data['close'][-2] > 0.01  # 1% 이상 변동 시 실행

    async def fetch_data_and_predict(self, upbit):
        """11단계: 데이터 수집과 예측을 병렬로 실행"""
        latest_data = self.fetch_latest_data()
        sentiment = await asyncio.to_thread(self.fetch_sentiment, "DOGE 뉴스")
        prediction = self.predict_signal(latest_data)
        if self.should_trade(latest_data):
            self.execute_trade(prediction, upbit)
        return sentiment, prediction
