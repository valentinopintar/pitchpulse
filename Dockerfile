# PitchPulse AI — single container: React studio + FastAPI (HF Spaces / Render friendly)
# UI at /  ·  API at /api  ·  default port 7860

FROM node:20-bookworm-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ENV VITE_API_URL=/api
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY data ./data
COPY --from=web /app/web/dist ./web/dist

RUN pip install --no-cache-dir -e ".[api]"

ENV PYTHONPATH=src
ENV PITCHPULSE_STATIC=/app/web/dist
ENV PORT=7860

EXPOSE 7860

CMD ["sh", "-c", "uvicorn pitchpulse.api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
