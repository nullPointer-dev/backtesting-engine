FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 8000

# Bring the schema up to date, then serve. Market data is loaded separately:
#   docker compose run --rm api python main.py --symbols RELIANCE.NS --timeframes 1d
CMD ["sh", "-c", "python main.py --migrate-only && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
