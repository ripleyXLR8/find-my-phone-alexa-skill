import logging
import os
import subprocess
import sys
import json
from flask import Flask, request
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model import RequestEnvelope
from ask_sdk_core.serialize import DefaultSerializer

# --- CONFIGURATION DYNAMIQUE ---
# BASE_DIR pointe vers /config, mappé au dossier appdata d'Unraid
BASE_DIR = os.getenv("BASE_DIR", "/config")
# Liste des utilisateurs (ex: "richard,lea")
USERS_ENV = os.getenv("USERS", "richard,lea")
USERS_LIST = [u.strip().lower() for u in USERS_ENV.split(",")]
# Version de l'outil (branche, tag ou commit SHA)
TOOLS_VERSION = os.getenv("TOOLS_VERSION", "main")
REPO_URL = "https://github.com/leonboe1/GoogleFindMyTools.git"

# Dictionnaire global pour stocker les chemins d'exécution
PATHS = {}

# CONFIGURATION LOGGING
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AlexaSkill")
logger.setLevel(logging.DEBUG)

def initialize_environment():
    """Initialise les dossiers, télécharge les outils et injecte les secrets."""
    for user in USERS_LIST:
        user_dir = os.path.join(BASE_DIR, f"google-{user}")
        auth_dir = os.path.join(user_dir, "Auth")
        
        # 1. Création des répertoires de base
        os.makedirs(auth_dir, exist_ok=True)
        
        # 2. Récupération automatique de l'outil GoogleFindMyTools
        if not os.path.exists(os.path.join(user_dir, ".git")):
            logger.info(f"📥 Téléchargement de GoogleFindMyTools pour {user}...")
            try:
                # Clone du dépôt
                subprocess.run(["git", "clone", REPO_URL, user_dir], check=True)
                # Passage à la version spécifique (TOOLS_VERSION)
                subprocess.run(["git", "checkout", TOOLS_VERSION], cwd=user_dir, check=True)
                logger.info(f"✅ Outil installé en version '{TOOLS_VERSION}' pour {user}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Erreur lors de la récupération Git pour {user}: {e}")

        # 3. Injection du secret depuis la variable d'environnement (ex: SECRET_RICHARD)
        secret_env_name = f"SECRET_{user.upper()}"
        secret_content = os.getenv(secret_env_name)
        
        if secret_content:
            try:
                # Validation et écriture du JSON
                json_data = json.loads(secret_content)
                secret_file_path = os.path.join(auth_dir, "secrets.json")
                with open(secret_file_path, "w") as f:
                    json.dump(json_data, f)
                logger.info(f"🔑 Secret injecté avec succès pour {user}")
            except json.JSONDecodeError:
                logger.error(f"❌ La variable {secret_env_name} contient un JSON invalide.")
        else:
            logger.warning(f"⚠️ Variable {secret_env_name} manquante.")

        # Enregistrement du chemin pour Alexa
        PATHS[user] = {
            "cwd": user_dir,
            "script": "ring_my_phone.py"
        }

# Lancement de l'initialisation au chargement du script
initialize_environment()

class LaunchRequestHandler(AbstractRequestHandler):
    """Accueil de la skill : énumère les utilisateurs configurés."""
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input):
        logger.debug("--- LaunchRequest reçue ---")
        names_str = " ou ".join([name.capitalize() for name in USERS_LIST])
        txt = f"Bienvenue dans la localisation de téléphone. Qui voulez-vous faire sonner ? {names_str} ?"
        return handler_input.response_builder.speak(txt).ask(txt).response

class FindPhoneIntentHandler(AbstractRequestHandler):
    """Gestion de l'intention de localisation."""
    def can_handle(self, handler_input):
        return is_intent_name("FindPhoneIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.debug("--- FindPhoneIntent reçue ---")
        
        slots = handler_input.request_envelope.request.intent.slots
        owner_slot = slots.get("Owner")
        target_key = None
        
        # Résolution du nom via les slots Alexa
        if owner_slot and owner_slot.resolutions and owner_slot.resolutions.resolutions_per_authority:
            if owner_slot.resolutions.resolutions_per_authority[0].status.code == "ER_SUCCESS_MATCH":
                target_key = owner_slot.resolutions.resolutions_per_authority[0].values[0].value.name.lower()
        
        # Fallback sur la valeur brute ou le premier utilisateur
        if not target_key:
            target_key = owner_slot.value.lower() if (owner_slot and owner_slot.value) else USERS_LIST[0]

        logger.info(f"Cible identifiée : {target_key}")
        
        if target_key in PATHS:
            config = PATHS[target_key]
            script_path = os.path.join(config["cwd"], config["script"])
            
            if not os.path.exists(script_path):
                return handler_input.response_builder.speak(
                    f"Erreur : le script ring_my_phone.py est absent pour {target_key}."
                ).response
            
            try:
                # Exécution du script de localisation
                process = subprocess.run(
                    [sys.executable, config["script"]], 
                    cwd=config["cwd"],
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                
                if process.returncode == 0:
                    speak_output = f"C'est fait, le téléphone de {target_key} sonne."
                else:
                    logger.error(f"Erreur script ({target_key}) : {process.stderr}")
                    speak_output = f"Le script a rencontré une erreur technique pour {target_key}."
            except Exception as e:
                logger.exception("Erreur lors de l'exécution du sous-processus")
                speak_output = "Désolé, je n'ai pas pu lancer la commande sur le serveur."
        else:
            speak_output = f"Désolé, l'utilisateur {target_key} n'est pas configuré sur ce serveur."
            
        return handler_input.response_builder.speak(speak_output).response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True
    
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak("Une erreur système est survenue.").response

app = Flask(__name__)
skill_builder = SkillBuilder()
skill_builder.add_request_handler(LaunchRequestHandler())
skill_builder.add_request_handler(FindPhoneIntentHandler())
skill_builder.add_exception_handler(CatchAllExceptionHandler())
skill = skill_builder.create()
serializer = DefaultSerializer()

@app.route("/", methods=['POST'])
def invoke_skill():
    try:
        payload = request.data.decode("utf-8")
        request_envelope = serializer.deserialize(payload, RequestEnvelope)
        response_envelope = skill.invoke(request_envelope, None)
        return serializer.serialize(response_envelope)
    except Exception as e:
        logger.error(f"Erreur skill : {e}", exc_info=True)
        return "Erreur", 500

@app.route("/health", methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
