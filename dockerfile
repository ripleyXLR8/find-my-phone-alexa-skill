# Utilisation d'une image Python stable et légère
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BASE_DIR="/config"
# 🚀 FIX SENIOR : On définit le chemin des outils pour les imports
ENV PYTHONPATH="/app:/app/google_tools"

WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .

# Installation des paquets système et clonage de l'outil au BUILD
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    git \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    build-essential \
    libffi-dev \
    && pip install --no-cache-dir -r requirements.txt \
    # 🚀 FIX SENIOR : Clonage au moment du build pour l'autonomie
    && git clone https://github.com/leonboe1/GoogleFindMyTools.git /app/google_tools \
    && cd /app/google_tools && git checkout 0003116 \
    && apt-get remove -y build-essential libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copie du code source du middleware
COPY src/server.py .
# 🚀 FIX SENIOR : On copie le fichier SANS le renommer en .template pour permettre l'import
COPY src/ring_my_phone.py .

RUN mkdir /config

EXPOSE 3000

# 🩺 Healthcheck Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "server.py"]
