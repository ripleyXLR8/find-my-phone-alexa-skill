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
# On copie le fichier requirements.txt [cite: 1]
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source du middleware (votre serveur Flask)
# On suppose que server.py est dans un dossier local 'src/'
COPY src/server.py .

# Création du point de montage pour la persistance Unraid
# C'est ici que les dossiers utilisateurs et les secrets seront créés
RUN mkdir /config

# Exposition du port utilisé par Flask pour la skill Alexa
EXPOSE 3000

# Commande de lancement
CMD ["python", "server.py"]
