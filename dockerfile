# Utilisation d'une image Python stable et légère
FROM python:3.11-slim

# Éviter la génération de fichiers .pyc et forcer l'affichage des logs en temps réel
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BASE_DIR="/config"

# Définition du répertoire de travail
WORKDIR /app

# Installation des dépendances Python (Placé avant l'installation système pour optimiser le cache)
COPY requirements.txt .

# Installation des paquets système, de Tini, compilation Python, puis nettoyage immédiat
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
    && apt-get remove -y build-essential libffi-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copie du code source du middleware
COPY src/server.py .
COPY src/ring_my_phone.py ./ring_my_phone.py.template

# Création du point de montage pour la persistance Unraid
RUN mkdir /config

# Exposition du port utilisé par Flask pour la skill Alexa
EXPOSE 3000

# Utilisation de Tini comme point d'entrée pour gérer correctement les signaux d'arrêt d'Unraid
ENTRYPOINT ["/usr/bin/tini", "--"]

# Commande de lancement
CMD ["python", "server.py"]
