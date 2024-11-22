# 베이스 이미지 선택
FROM python:3.8-slim

# 작업 디렉토리 설정
WORKDIR /app

# 프로그램 파일 복사
COPY . /app

# 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 프로그램 실행 명령어 설정
CMD ["python", "main.py"]
