# =========================
# 1) Build Frontend (Vite/React) باستخدام npm أو pnpm
# =========================
FROM node:20-alpine AS fe
WORKDIR /fe

# انسخ مشروع الواجهة
COPY rfah-frontend/ ./

# فعّل corepack (لـ pnpm عند وجود pnpm-lock.yaml) وثبّت الاعتمادات ثم ابنِ
RUN corepack enable && \
    if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; else npm install; fi && \
    npm run build

# وحّد ناتج البناء (dist أو build) في مجلد واحد
RUN mkdir -p /bundle-static && \
    if [ -d dist ]; then cp -r dist/* /bundle-static/; \
    elif [ -d build ]; then cp -r build/* /bundle-static/; \
    else echo "No dist/ or build/ directory found after frontend build" && ls -la && exit 1; fi


# =========================
# 2) Backend Runtime (Python + Gunicorn)
# =========================
FROM python:3.12-slim AS run
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# أدوات بناء خفيفة لبعض الحزم (يمكن حذفها لاحقًا إن لم تُستخدم)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && rm -rf /var/lib/apt/lists/*

# ثبّت متطلبات الباكند
COPY qer-backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# انسخ كود الباكند
COPY qer-backend/ ./

# انسخ ملفات الواجهة المبنية إلى static داخل تطبيق Flask
COPY --from=fe /bundle-static/ /app/src/static/

# المنفذ وعدد العمال (قلّل العمال لتناسب الخطة المجانية)
ENV PORT=8000 \
    GUNICORN_WORKERS=1

EXPOSE 8000

# أنشئ مجلد قاعدة البيانات (SQLite) قبل الإقلاع ثم شغّل Gunicorn
# ملاحظة: يُستحسن ضبط DATABASE_URL في متغيرات البيئة (مثلاً sqlite:////app/src/instance/app.db)
CMD ["bash","-lc","mkdir -p /app/data && exec gunicorn -w ${GUNICORN_WORKERS:-1} -b 0.0.0.0:${PORT} src.main:app"]

