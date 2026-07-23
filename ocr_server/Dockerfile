FROM python:3.11-slim

WORKDIR /app

# apt-get 설치 도중 사용자 입력을 대기하여 멈추는 현상 방지
ENV DEBIAN_FRONTEND=noninteractive

# libgl1-mesa-glx -> libgl1 으로 대체
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]