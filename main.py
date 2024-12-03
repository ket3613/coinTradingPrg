import uvicorn
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from exchenge_api import ExchangeApi
from fastapi.responses import HTMLResponse
from collections import deque
import logging

# FastAPI 앱 초기화
app = FastAPI()
exchange_api = ExchangeApi()

# 최근 로그 저장 (최대 50개)
log_queue = deque(maxlen=50)


# FastAPI 로그 핸들러
class FastAPILogHandler(logging.Handler):
    def emit(self, record):
        log_queue.append(self.format(record))


# 로거 설정
log_handler = FastAPILogHandler()
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler.setFormatter(log_formatter)

logger = logging.getLogger("fastapi")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)


# 거래 로직 실행 함수
def run_trading_logic():
    try:
        exchange_api.lstm_trading_logic()
        logger.info("거래 로직 실행 성공")
    except Exception as e:
        logger.error(f"거래 로직 실행 중 오류 발생: {e}")


# 백그라운드 스케줄러 설정
scheduler = BackgroundScheduler()
scheduler.add_job(run_trading_logic, "interval", seconds=5)
scheduler.start()


# 기본 라우트
@app.get("/")
def read_root():
    return {"message": "AI-based Coin Trading Bot is running on KRW-DOGE!"}


# 헬스 체크 라우트
@app.get("/health")
def health_check():
    return {"status": "running", "scheduler": scheduler.running}


# 로그 데이터 제공 라우트
@app.get("/logs")
async def get_logs():
    return list(log_queue)


# HTML 로그 뷰어 제공
@app.get("/log-viewer", response_class=HTMLResponse)
async def serve_log_viewer():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>실시간 로그 뷰어</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            #log-container { max-height: 500px; overflow-y: scroll; background: #f9f9f9; border: 1px solid #ccc; padding: 10px; }
            .log-line { margin: 0; font-size: 14px; }
        </style>
    </head>
    <body>
        <h1>실시간 로그 뷰어</h1>
        <div id="log-container"></div>
        <script>
            const logContainer = document.getElementById('log-container');

            async function fetchLogs() {
                try {
                    const response = await fetch('/logs');
                    const logs = await response.json();
                    logContainer.innerHTML = logs.map(log => `<p class="log-line">${log}</p>`).join('');
                } catch (error) {
                    console.error('로그를 가져오는 중 오류 발생:', error);
                }
            }

            // 2초마다 로그 갱신
            setInterval(fetchLogs, 2000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# FastAPI 종료 이벤트
@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()


# FastAPI 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
