# 교통 소요시간 수집 서비스 (EKS)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY src/ ./src/
COPY run_once.py run_scheduler.py run_hourly.py ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# -u: stdout/stderr 무버퍼 (Docker에서 출력 즉시 표시)
CMD ["python", "-u", "run_hourly.py"]
