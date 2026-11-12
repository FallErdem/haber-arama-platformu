# Python işçisi imajı. Derleme bağlamı, diğer imajlarda olduğu gibi deponun köküdür:
#
#   docker build -f worker/Dockerfile -t <imaj adı> .

# ---- 1. aşama: bağımlılıkların kurulması (uv burada kalır, son imaja girmez) ----
FROM python:3.14.9-slim-trixie AS build

# uv'nin tek dosyalık programı kendi resmi imajından kopyalanır; sürümü geliştirme ortamındakiyle aynıdır.
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv

WORKDIR /app
# COMPILE_BYTECODE: .pyc dosyaları derleme sırasında üretilir, işçi daha hızlı açılır.
# LINK_MODE=copy: paketler önbellekten bağlantıyla değil kopyalanarak kurulur (önbellek imajda kalmaz).
# PYTHON_DOWNLOADS=never: uv başka bir Python indirmez; imajdaki Python kullanılır.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Önce yalnızca paket listesi: kod değişse de paketler değişmediyse Docker bu adımı önbellekten kullanır.
# --locked: uv.lock ile pyproject.toml uyuşmuyorsa derleme durur. --no-dev: test araçları kurulmaz.
COPY worker/pyproject.toml worker/uv.lock worker/.python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY worker/src src
# --no-editable: işçinin kendi kodu da sanal ortama kopyalanır; son imajda src klasörü gerekmez.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---- 2. aşama: çalışma (yalnızca Python ve kurulu paketler) ----
FROM python:3.14.9-slim-trixie
WORKDIR /app

COPY --from=build /app/.venv /app/.venv

# Sanal ortamdaki komutlar (news-worker) yolda bulunur.
# PYTHONUNBUFFERED: log satırları bekletilmeden yazılır; kubectl logs gecikmesiz görür.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# İşçi root olarak çalışmaz.
USER 1000:1000
EXPOSE 8080
ENTRYPOINT ["news-worker"]
