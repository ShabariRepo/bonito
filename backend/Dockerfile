# ── Development (default) ──────────────────────────────────────
FROM python:3.12-slim AS dev

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev pkg-config libxmlsec1-dev libxmlsec1-openssl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production (multi-stage) ──────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

# libpq5: postgres driver runtime
# libxmlsec1-openssl: xmlsec runtime (python3-saml / SAML SSO)
# gcc, libpq-dev, pkg-config, libxmlsec1-dev: build-time deps for pip install
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libpq-dev pkg-config \
        libxmlsec1-dev libxmlsec1-openssl \
    && rm -rf /var/lib/apt/lists/* && \
    addgroup --system app && adduser --system --group app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge 2>/dev/null || true

# Pre-download sentence-transformers model so it's cached in the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" 2>/dev/null || true

# Remove build-only deps to keep image slim
RUN apt-get update && apt-get remove -y gcc libpq-dev pkg-config libxmlsec1-dev && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY . .

# Writable dirs for app user: HF cache, memwright data
RUN mkdir -p /app/data/memwright /app/.cache && \
    chmod +x entrypoint.sh && chown -R app:app /app
USER app

ENV HOME=/app
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/api/health'); r.raise_for_status()"

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
