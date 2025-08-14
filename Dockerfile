# ====== Frontend build ======
FROM node:20-alpine AS fe
WORKDIR /fe
COPY rfah-frontend/ ./

# استخدم pnpm إن كان lock موجود، وإلا npm
RUN corepack enable
RUN if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; else npm install; fi

RUN if [ -f pnpm-lock.yaml ]; then pnpm run build; else npm run build; fi

# ====== Backend (Flask) ======
FROM python:3.12-slim AS app
WORKDIR /app

# متطلبات تشغيل بسيطة
RUN apt-get update && apt-get install -y --no-install-recommends tini && \
    rm -rf /var/lib/apt/lists/*

# نسخ متطلبات الباك وتثبيتها
COPY qer-backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# نسخ كود الباك
COPY qer-backend/src/ /app/src/

# تهيئة مجلد instance لقاعدة البيانات (SQLite)
ENV INSTANCE_DIR=/app/instance
RUN mkdir -p ${INSTANCE_DIR} && chmod -R 777 ${INSTANCE_DIR}

# نسخ مخرجات الفرونت إلى static التي يقرأها Flask
RUN mkdir -p /app/src/static
COPY --from=fe /fe/dist/ /app/src/static/

# إعدادات التشغيل
ENV PORT=8000
ENV STATIC_DIR=/app/src/static
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","src.main:app"]
