# 1) بناء الواجهة الأمامية
FROM node:20-alpine AS fe
WORKDIR /fe
COPY rfah-frontend/package*.json ./
RUN npm ci
COPY rfah-frontend/ .
RUN npm run build

# 2) تشغيل الواجهة الخلفية
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY qer-backend/ /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn

RUN mkdir -p /app/src/static && rm -rf /app/src/static/* || true
# إذا كان ناتج React هو build بدل dist بدّل المسار في السطر التالي إلى /fe/build/
COPY --from=fe /fe/dist/ /app/src/static/

ENV PORT=8080
EXPOSE 8080
CMD ["bash","-lc","exec gunicorn -w 3 -b 0.0.0.0:${PORT} src.main:app"]
