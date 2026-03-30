# Utilisation d'une image Python stable et légère
FROM python:3.11-slim

# Éviter la génération de fichiers .pyc et forcer l'affichage des logs en temps réel
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BASE_DIR="/config"

# Installation des dépendances système
# - git : pour cloner le dépôt GoogleFindMyTools
# - chromium/chromium-driver : pour l'automatisation Selenium
# - build-essential/libffi-dev : pour compiler certaines dépendances Python (ex: Frida, Cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Définition du répertoire de travail
WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source du middleware
# Note : server.py est à la racine de votre dépôt GitHub
COPY src/server.py .

# Préparation du template pour la personnalisation automatique des scripts utilisateurs
COPY src/ring_my_phone.py ./ring_my_phone.py.template

# Création du point de montage pour la persistance Unraid
RUN mkdir /config

# Exposition du port utilisé par Flask pour la skill Alexa
EXPOSE 3000

# Commande de lancement
CMD ["python", "server.py"]
