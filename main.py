from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pandas as pd
from datetime import datetime
from exchenge_api import ExchangeApi
import pyupbit
app = FastAPI()

# 작업을 수행할 함수
def scheduled_task():
    # 볼린저 밴드 전략 실행
    exchange_api = ExchangeApi()
    exchange_api.bollinger_strategy()  # 매수/매도 신호 체크 및 실행

def check_scheduler_status():
    doge_data = ExchangeApi.get_data()
    result_doge_data = ExchangeApi.calculate_bollinger_bands(doge_data)
    latest_data = result_doge_data.iloc[0]
    upper_volume = round(latest_data['Upper'], 6)
    lower_volume = round(latest_data['Lower'], 6)
    trade_price = pyupbit.get_current_price('KRW-SHIB')
    print("프로그램 동작 확인:" + str(datetime.now()))
    print("upper_volume" + str(upper_volume))
    print("lower_volume" + str(lower_volume))
    print("trade_price" + str(trade_price))

# 스케줄러 설정
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, 'interval', seconds=5)
scheduler.add_job(check_scheduler_status, 'interval', minutes=1)
scheduler.start()

####################################
@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
