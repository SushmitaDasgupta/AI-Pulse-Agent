FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps for common Python wheels / SSL
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src

RUN pip install -r requirements.txt \
    && pip install .

COPY config.yaml ./
COPY prompts ./prompts
COPY data ./data

RUN mkdir -p out data/raw data/interim data/processed

# Full weekly pipeline; Railway cron / custom startCommand can override.
CMD ["pulsator", "run"]
