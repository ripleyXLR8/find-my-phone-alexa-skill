# Utilisation d'une image Python stable et légère
FROM python:3.11-slim

# Éviter la génération de fichiers .pyc et forcer l'affichage des logs en temps réel
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BASE_DIR="/config"
# Chemin interne où l'outil est pré-installé
ENV PYTHONPATH="/app/google_tools"

# Définition du répertoire de travail
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
    # 🚀 FIX SENIOR : Clonage et verrouillage du commit au moment du build
    && git clone https://github.com/leonboe1/GoogleFindMyTools.git /app/google_tools \
    && cd /app/google_tools && git checkout 0003116 \
    && apt-get remove -y build-essential libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copie du code source du middleware et du template
COPY src/server.py .
COPY src/ring_my_phone.py ./ring_my_phone.py.template

# Création du point de montage pour la persistance Unraid
RUN mkdir /config

# Exposition du port
EXPOSE 3000

# 🩺 Healthcheck Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Utilisation de Tini
ENTRYPOINT ["/usr/bin/tini", "--"]

# Commande de lancement
CMD ["python", "server.py"]
