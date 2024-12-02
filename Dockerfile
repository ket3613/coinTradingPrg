# Python 3.9 Slim 이미지 사용 (최소한의 이미지)
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY . .

# 실행 명령 설정
CMD ["python", "main.py"]
