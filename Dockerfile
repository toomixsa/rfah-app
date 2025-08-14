# ====== Frontend build ======
FROM node:20-alpine AS fe
WORKDIR /fe
COPY rfah-frontend/ ./

RUN corepack enable
RUN if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; else npm install; fi

RUN if [ -f pnpm-lock.yaml ]; then pnpm run build; else npm run build; fi

# ====== Backend (Flask) ======
FROM python:3.12-slim AS app
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends tini curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install backend requirements
COPY qer-backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code
COPY qer-backend/src/ /app/src/

# Prepare instance dir for SQLite
ENV INSTANCE_DIR=/app/instance
RUN mkdir -p ${INSTANCE_DIR} && chmod -R 777 ${INSTANCE_DIR}

# Copy FE build into Flask static
RUN mkdir -p /app/src/static
COPY --from=fe /fe/dist/ /app/src/static/

ENV PORT=8000
ENV STATIC_DIR=/app/src/static
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["gunicorn","--preload","-w","1","-b","0.0.0.0:8000","src.main:app","--timeout","120"]
