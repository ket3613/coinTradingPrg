# Step 1: 베이스 이미지 설정 (Python 3.9 사용)
FROM python:3.9-slim

# Step 2: 작업 디렉토리 생성
WORKDIR /app

# Step 3: 필요한 파일 복사
# requirements.txt와 프로젝트 파일 복사
COPY requirements.txt .
COPY . .

# Step 4: 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: FastAPI 앱 실행을 위한 포트 설정
EXPOSE 8000

# Step 6: 실행 명령어 설정 (uvicorn으로 FastAPI 실행)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
