# ---- Build frontend ----
FROM node:20-alpine AS fe
WORKDIR /fe
COPY rfah-frontend/ ./
RUN corepack enable && \
    if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; else npm install; fi && \
    npm run build

# ---- Python runtime ----
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# أدوات بناء خفيفة (احذفها لاحقًا إذا ما تحتاجها)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc && rm -rf /var/lib/apt/lists/*

# باكدج الباك-إند
COPY qer-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn

# كود الباك-إند
COPY qer-backend/ ./

# نسخ ناتج الواجهة إلى static داخل التطبيق
COPY --from=fe /fe/dist/ /app/src/static/
# لو الناتج عندك اسمه build بدل dist:
# COPY --from=fe /fe/build/ /app/src/static/

# تشغيل السيرفر
ENV PORT=8000 GUNICORN_WORKERS=1
EXPOSE 8000
CMD ["bash","-lc","exec gunicorn -w ${GUNICORN_WORKERS} -b 0.0.0.0:${PORT} src.main:app"]
