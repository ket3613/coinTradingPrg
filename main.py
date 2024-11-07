from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pandas as pd
from exchenge_api import ExchangeApi

app = FastAPI()

# 작업을 수행할 함수
def scheduled_task():
    # 볼린저 밴드 전략 실행
    exchange_api = ExchangeApi()
    exchange_api.bollinger_strategy()  # 매수/매도 신호 체크 및 실행


# 스케줄러 설정
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, 'interval', seconds=10)
scheduler.start()







####################################
@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
