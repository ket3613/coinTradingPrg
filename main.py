from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pandas as pd
from exchenge_api import ExchangeApi

app = FastAPI()

globals_my_account = ExchangeApi.get_my_account(1)
print(globals_my_account)

ExchangeApi.get_doge_data(200)
# 작업을 수행할 함수
def scheduled_task():
    # 데이터 가져오기
    doge_data = ExchangeApi.get_doge_data(200)
    doge_data['candle_date_time_utc'] = pd.to_datetime(doge_data['candle_date_time_utc'])
    doge_data.set_index('candle_date_time_utc', inplace=True)
    doge_data.sort_index(inplace=True)

    doge_data['short_ma'] = doge_data['trade_price'].rolling(window=5).mean()
    doge_data['long_ma'] = doge_data['trade_price'].rolling(window=20).mean()

    # 매수 신호 찾기: 단기선이 장기선을 상향 돌파할 때 매수
    doge_data['buy_signal'] = (doge_data['short_ma'] > doge_data['long_ma']) & (doge_data['short_ma'].shift(1) <= doge_data['long_ma'].shift(1))

    # 매수 신호 시점 출력
    buy_points = doge_data[doge_data['buy_signal']]
    print("========================================1")
    print(buy_points)
    print("========================================2")
    print(buy_points[['trade_price', 'short_ma', 'long_ma']])
    print("========================================3")
    #print(doge_data[['opening_price']].head())

    # 종가와 날짜 출력
    # print(doge_data[['candle_date_time_kst']].head())
    # print(doge_data[['opening_price']].head())
    # print(doge_data[['high_price']].head())
    # print(doge_data[['low_price']].head())
    # print("작업 실행:", time.strftime("%Y-%m-%d %H:%M:%S"))

# 스케줄러 설정
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, 'interval', seconds=5)
scheduler.start()







####################################
@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
