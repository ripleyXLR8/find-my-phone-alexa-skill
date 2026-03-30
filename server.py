import logging
import os
import subprocess
import sys
from flask import Flask, request
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model import RequestEnvelope
from ask_sdk_core.serialize import DefaultSerializer

# --- CONFIGURATION DOCKER ---
BASE_DIR = "/app"

PATHS = {
    "richard": {
        "cwd": os.path.join(BASE_DIR, "google-richard"),
        "script": "ring_my_phone.py"
    },
    "lea": {
        "cwd": os.path.join(BASE_DIR, "google-lea"),
        "script": "ring_my_phone.py"
    }
}

# CONFIGURATION LOGGING (Plus verbeux)
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AlexaSkill")
# On force le niveau DEBUG pour ce logger spécifique
logger.setLevel(logging.DEBUG)

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input):
        logger.debug("--- LaunchRequest reçue ---")
        txt = "Bienvenue. Qui voulez-vous localiser ? Richard ou Lea ?"
        return handler_input.response_builder.speak(txt).ask(txt).response

class FindPhoneIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("FindPhoneIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.debug("--- FindPhoneIntent reçue ---")
        
        # Log des slots bruts pour voir ce qu'Alexa a compris
        slots = handler_input.request_envelope.request.intent.slots
        logger.debug(f"Slots bruts : {slots}")

        owner_slot = slots.get("Owner")
        target_key = "richard" # Valeur par défaut
        
        if owner_slot and owner_slot.resolutions and owner_slot.resolutions.resolutions_per_authority:
            if owner_slot.resolutions.resolutions_per_authority[0].status.code == "ER_SUCCESS_MATCH":
                target_key = owner_slot.resolutions.resolutions_per_authority[0].values[0].value.name.lower()
                logger.debug(f"Slot résolu avec succès : {target_key}")
            else:
                logger.warning("Slot non résolu (pas de match dans la liste), utilisation du défaut.")
        else:
            logger.debug("Pas de résolution de slot trouvée.")

        logger.info(f"Cible finale identifiée : {target_key}")
        speak_output = ""
        
        if target_key in PATHS:
            config = PATHS[target_key]
            if not os.path.exists(config["cwd"]):
                logger.error(f"Dossier introuvable : {config['cwd']}")
                return handler_input.response_builder.speak(f"Erreur dossier {target_key}").response
            
            try:
                cmd = [sys.executable, config["script"]]
                logger.debug(f"Lancement commande : {cmd} dans {config['cwd']}")
                
                process = subprocess.run(
                    cmd, 
                    cwd=config["cwd"],
                    capture_output=True,
                    text=True,
                    timeout=40
                )
                
                logger.debug(f"Code retour script : {process.returncode}")
                if process.stdout:
                    logger.debug(f"STDOUT Script : {process.stdout.strip()}")
                
                if process.returncode == 0:
                    speak_output = f"C'est fait, le téléphone de {target_key} sonne."
                    logger.info("Script exécuté avec succès.")
                else:
                    logger.error(f"STDERR Script : {process.stderr}")
                    speak_output = "J'ai rencontré une erreur technique."
            except Exception as e:
                logger.exception("Exception Python durant l'exécution du sous-processus")
                speak_output = "Le service ne répond pas."
        else:
            logger.warning(f"Clé cible '{target_key}' inconnue dans la config PATHS.")
            speak_output = f"Je ne connais pas {target_key}."
            
        return handler_input.response_builder.speak(speak_output).response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True
    
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak("Erreur critique.").response

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
        # Log de la requête entrante (attention, ça peut être verbeux)
        logger.debug(f"REQUÊTE ENTRANTE : {payload}")
        
        request_envelope = serializer.deserialize(payload, RequestEnvelope)
        response_envelope = skill.invoke(request_envelope, None)
        
        json_response = serializer.serialize(response_envelope)
        logger.debug(f"RÉPONSE SORTANTE : {json_response}")
        
        return json_response
    except Exception as e:
        logger.error(f"Erreur skill : {e}", exc_info=True)
        return "Erreur", 500

@app.route("/health", methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    # On active aussi le mode debug de Flask
    app.run(host='0.0.0.0', port=3000, debug=False)