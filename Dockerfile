# ====== Frontend build ======
FROM node:20-alpine AS fe
WORKDIR /fe
COPY rfah-frontend/ ./

# يدعم pnpm أو npm
RUN corepack enable
RUN if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; else npm install; fi

RUN if [ -f pnpm-lock.yaml ]; then pnpm run build; else npm run build; fi


# ====== Backend (Flask) ======
FROM python:3.12-slim AS app
WORKDIR /app

# أدوات خفيفة + tini
RUN apt-get update && apt-get install -y --no-install-recommends \
      tini curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# تثبيت المتطلبات
COPY qer-backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# نسخ كود الباك
COPY qer-backend/src/ /app/src/

# تهيئة مجلد قاعدة البيانات (SQLite)
ENV INSTANCE_DIR=/app/instance
RUN mkdir -p ${INSTANCE_DIR} && chmod -R 777 ${INSTANCE_DIR}

# نسخ بناء الفرونت إلى مجلد ثابت تقرأه Flask
# (يتوافق مع main.py الذي يقرأ FRONTEND_DIR)
RUN mkdir -p /app/src/static
COPY --from=fe /fe/dist/ /app/src/static/

# متغيرات بيئة مفيدة
ENV PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PYTHONPATH=/app \
    FRONTEND_DIR=/app/src/static \
    SQLALCHEMY_DATABASE_URI=sqlite:////app/instance/app.db

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini","--"]
# اربط على PORT القادم من Koyeb، ومن دون --preload
CMD ["gunicorn","-w","2","-b","0.0.0.0:${PORT:-8000}","src.main:app","--timeout","120"]
