# ------------ FE: Build ------------
FROM node:20-alpine AS fe
WORKDIR /fe
COPY rfah-frontend/ ./
# يشتغل سواء عندك pnpm-lock أو package-lock أو لا
RUN corepack enable \
 && if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; else npm install; fi
RUN if [ -f pnpm-lock.yaml ]; then pnpm run build; else npm run build; fi

# نجمع ناتج البناء dist/ أو build/ في مجلد موحّد
RUN mkdir -p /bundle-static \
 && if [ -d dist ]; then cp -r dist/* /bundle-static/; \
    elif [ -d build ]; then cp -r build/* /bundle-static/; \
    else echo "No dist/ or build/ directory found after frontend build" && ls -la && exit 1; fi

# ------------ PY: Runtime ------------
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    FLASK_ENV=production \
    SECRET_KEY=change-me-please

WORKDIR /app

# باكدجات النظام الخفيفة + مجلد instance لقاعدة البيانات
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tini && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /app/instance && chmod -R 777 /app/instance

# متطلبات بايثون
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# كود الباك
COPY src/ /app/src/

# ملفات الواجهة الجاهزة تُنسخ إلى static التي يقرؤها Flask
COPY --from=fe /bundle-static/ /app/src/static/

# صحّة بسيطة
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/healthz || exit 1

EXPOSE ${PORT}
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["gunicorn","-k","gthread","-w","2","-b","0.0.0.0:8000","src.main:app","--timeout","120"]
