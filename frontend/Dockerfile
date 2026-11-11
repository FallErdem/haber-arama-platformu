# React frontend imajı. Derleme bağlamı, API imajında olduğu gibi deponun köküdür:
#
#   docker build -f frontend/Dockerfile -t <imaj adı> .

# ---- 1. aşama: derleme (Node ve node_modules burada kalır, son imaja girmez) ----
FROM node:26.12.1-alpine AS build
WORKDIR /workspace/frontend

# Önce yalnızca paket listesi kopyalanır: kod değişse de paketler değişmediyse
# Docker bu adımı önbellekten kullanır. "npm ci" kilit dosyasındaki sürümleri birebir kurar.
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY frontend/index.html frontend/vite.config.ts ./
COPY frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json ./
COPY frontend/src src
RUN npm run build

# ---- 2. aşama: çalışma (yalnızca nginx ve derlenmiş dosyalar) ----
# nginx-unprivileged: root olmayan kullanıcıyla ve 8080 portunda çalışan resmi nginx imajı.
FROM nginxinc/nginx-unprivileged:1.30.6-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/frontend/dist /usr/share/nginx/html

EXPOSE 8080
