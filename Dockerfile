# PayPilot backend (FastAPI). The Next.js frontend is deployed separately (Vercel) and proxies /api to this service.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY deployments.json .
# State is held in memory, so run exactly ONE instance. Set PAYPILOT_DATABASE_URL for durable users/passkeys.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001} --proxy-headers --forwarded-allow-ips='*'"]
