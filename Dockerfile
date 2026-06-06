# Ad Spy Agent - production image (Flask + patchright Chromium + Gemini)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HEADLESS=true \
    PORT=4000

WORKDIR /app

# Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Chromium + all OS libraries patchright needs (runs apt under the hood)
RUN patchright install --with-deps chromium

# Copy the app in as an importable package named `ad_spy_agent`
# (the repo folder name has a hyphen, which isn't a valid module name).
COPY . /app/ad_spy_agent/

EXPOSE 4000

# One worker: the in-memory job store must be shared within a single process.
# Multiple threads handle concurrent requests; --timeout 0 ensures long-running
# background scrape threads are never killed by the worker timeout.
CMD ["gunicorn", "--bind", "0.0.0.0:4000", "--workers", "1", "--threads", "8", "--timeout", "0", "ad_spy_agent.server:app"]
