import uvicorn
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from exchenge_api import ExchangeApi

app = FastAPI()
exchange_api = ExchangeApi()

def run_trading_logic():
    exchange_api.lstm_trading_logic()

scheduler = BackgroundScheduler()
scheduler.add_job(run_trading_logic, 'interval', seconds=5)
scheduler.start()

@app.get("/")
def read_root():
    return {"message": "AI-based Coin Trading Bot is running on KRW-DOGE!"}

@app.get("/health")
def health_check():
    return {"status": "running", "scheduler": scheduler.running}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
