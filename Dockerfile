FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CLIANY_HEADLESS=true

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ src/

RUN pip install --no-cache-dir -e .

RUN mkdir -p /root/.cliany-site/adapters /root/.cliany-site/sessions

ENTRYPOINT ["cliany-site"]
CMD ["doctor", "--json"]
