import logging
import os
import subprocess
import sys
import shutil
from flask import Flask, request
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model import RequestEnvelope
from ask_sdk_core.serialize import DefaultSerializer

# --- CONFIGURATION DYNAMIQUE ---
# BASE_DIR pointe vers /config, mappé au dossier appdata d'Unraid
BASE_DIR = os.getenv("BASE_DIR", "/config")
# On récupère la liste des utilisateurs via une variable d'env (ex: "richard,lea")
USERS_ENV = os.getenv("USERS", "richard,lea")
USERS_LIST = [u.strip().lower() for u in USERS_ENV.split(",")]

PATHS = {}

# CONFIGURATION LOGGING
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AlexaSkill")
logger.setLevel(logging.DEBUG)

def initialize_folders():
    """Crée les dossiers et l'arborescence Auth pour chaque utilisateur."""
    for user in USERS_LIST:
        user_dir = os.path.join(BASE_DIR, f"google-{user}")
        auth_dir = os.path.join(user_dir, "Auth")
        
        # Création des répertoires s'ils n'existent pas
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)
            logger.info(f"Dossier utilisateur créé : {user_dir}")
        
        if not os.path.exists(auth_dir):
            os.makedirs(auth_dir, exist_ok=True)
            logger.info(f"Dossier Auth créé pour {user}")

        PATHS[user] = {
            "cwd": user_dir,
            "script": "ring_my_phone.py"
        }

# Initialisation au démarrage
initialize_folders()

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input):
        logger.debug("--- LaunchRequest reçue ---")
        # Alexa énumère les noms configurés dynamiquement
        names_str = " ou ".join([name.capitalize() for name in USERS_LIST])
        txt = f"Bienvenue dans Find My Phone. Qui voulez-vous localiser ? {names_str} ?"
        return handler_input.response_builder.speak(txt).ask(txt).response

class FindPhoneIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("FindPhoneIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.debug("--- FindPhoneIntent reçue ---")
        
        slots = handler_input.request_envelope.request.intent.slots
        owner_slot = slots.get("Owner")
        target_key = None
        
        # Tentative de résolution du nom via les slots Alexa
        if owner_slot and owner_slot.resolutions and owner_slot.resolutions.resolutions_per_authority:
            if owner_slot.resolutions.resolutions_per_authority[0].status.code == "ER_SUCCESS_MATCH":
                target_key = owner_slot.resolutions.resolutions_per_authority[0].values[0].value.name.lower()
        
        # Fallback sur la valeur brute ou le premier utilisateur par défaut
        if not target_key:
            target_key = owner_slot.value.lower() if (owner_slot and owner_slot.value) else USERS_LIST[0]

        logger.info(f"Cible identifiée : {target_key}")
        
        if target_key in PATHS:
            config = PATHS[target_key]
            script_full_path = os.path.join(config["cwd"], config["script"])
            
            if not os.path.exists(script_full_path):
                logger.error(f"Script introuvable : {script_full_path}")
                return handler_input.response_builder.speak(
                    f"Le script de localisation pour {target_key} n'est pas encore présent dans le dossier de configuration."
                ).response
            
            try:
                # Exécution du script GoogleFindMyTools
                process = subprocess.run(
                    [sys.executable, config["script"]], 
                    cwd=config["cwd"],
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                
                if process.returncode == 0:
                    speak_output = f"C'est fait, le téléphone de {target_key} sonne."
                    logger.info(f"Succès pour {target_key}")
                else:
                    logger.error(f"Erreur script : {process.stderr}")
                    speak_output = f"Le script a rencontré une erreur pour {target_key}. Vérifiez les logs."
            except Exception as e:
                logger.exception("Exception durant l'exécution")
                speak_output = "Le NAS n'a pas pu exécuter la commande de localisation."
        else:
            speak_output = f"Désolé, je ne connais pas l'utilisateur {target_key}."
            
        return handler_input.response_builder.speak(speak_output).response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True
    
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak("Désolé, une erreur interne est survenue sur votre serveur.").response

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
    # Écoute sur le port 3000 (standard pour notre Docker)
    app.run(host='0.0.0.0', port=3000, debug=False)
