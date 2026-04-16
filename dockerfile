FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BASE_DIR="/config"

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini git wget gnupg unzip curl chromium chromium-driver build-essential libffi-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && git clone https://github.com/leonboe1/GoogleFindMyTools.git /app/google_tools \
    && cd /app/google_tools \
    && git checkout 0003116 \
    && cd /app \
    && apt-get remove -y build-essential libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY src/server.py .
COPY src/ring_my_phone.py .
COPY src/templates ./templates
RUN mkdir /config
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "server.py"]
