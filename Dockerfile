# ===============================
#  Frontend build (npm أو pnpm)
# ===============================
FROM node:20-alpine AS fe
WORKDIR /fe

# لو المشروع يستخدم pnpm فعلناه عبر corepack
RUN corepack enable

# ننسخ مجلد الواجهة بالكامل ثم نثبّت الاعتمادات ونبني
COPY rfah-frontend/ ./

# تثبيت الاعتمادات: pnpm إن وُجد lockfile، وإلا npm ci، وإن لم يوجد package-lock.json نستخدم npm install
RUN if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; else npm install; fi

# البناء (يدعم pnpm أو npm)
RUN if [ -f pnpm-lock.yaml ]; then pnpm run build; else npm run build; fi

# نجمع ناتج البناء (dist أو build) في مجلد واحد
RUN mkdir -p /bundle-static && \
    if [ -d dist ]; then cp -r dist/* /bundle-static/; \
    elif [ -d build ]; then cp -r build/* /bundle-static/; \
    else echo "No dist/ or build/ directory found after frontend build" && ls -la && exit 1; fi


# ===============================
#  Python backend (Flask +
