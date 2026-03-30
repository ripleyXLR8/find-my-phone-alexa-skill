import logging
import os
import subprocess
import sys
import json
import shutil
import threading
from flask import Flask
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_flask.adapter import SkillAdapter

# --- BANNIÈRE DE DÉMARRAGE ---
def show_startup_banner():
    banner = """
===================================================================
 📱 ALEXA - FIND MY PHONE MIDDLEWARE
===================================================================
 👤 Author      : Richard Perez (ripleyXLR8)
 ✉️  Email       : richard@perez-mail.fr
 🌐 GitHub      : https://github.com/ripleyXLR8/find-my-phone-alexa-skill
 📦 Version     : 1.1.0
 ⚙️  Environment : Unraid / Docker (Stateless)
 🔒 Security    : Amazon Signature Verification Enabled
 🚀 Port        : 3000
===================================================================
    """
    print(banner, flush=True)

show_startup_banner()

# --- CONFIGURATION DYNAMIQUE ---
BASE_DIR = os.getenv("BASE_DIR", "/config")
USERS_ENV = os.getenv("USERS", "richard,lea")
USERS_LIST = [u.strip().lower() for u in USERS_ENV.split(",")]
TOOLS_VERSION = os.getenv("TOOLS_VERSION", "main")
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID") # NOUVEAU : Sécurité de la Skill
REPO_URL = "https://github.com/leonboe1/GoogleFindMyTools.git"

PATHS = {}

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AlexaSkill")
logger.setLevel(logging.DEBUG)

def initialize_environment():
    template_path = "/app/ring_my_phone.py.template"

    if not ALEXA_SKILL_ID:
        logger.warning("⚠️ ATTENTION: ALEXA_SKILL_ID n'est pas défini. La vérification stricte de l'ID est désactivée (mais la signature Amazon reste vérifiée).")

    for user in USERS_LIST:
        user_dir = os.path.join(BASE_DIR, f"google-{user}")
        auth_dir = os.path.join(user_dir, "Auth")
        
        if not os.path.exists(os.path.join(user_dir, ".git")):
            logger.info(f"📥 Téléchargement de GoogleFindMyTools pour {user}...")
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)
            try:
                subprocess.run(["git", "clone", REPO_URL, user_dir], check=True)
                subprocess.run(["git", "checkout", TOOLS_VERSION], cwd=user_dir, check=True)
                logger.info(f"✅ Outil installé en version '{TOOLS_VERSION}' pour {user}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Erreur lors de la récupération Git pour {user}: {e}")

        os.makedirs(auth_dir, exist_ok=True)

        secret_env_name = f"SECRET_{user.upper()}"
        secret_content = os.getenv(secret_env_name)
        
        if secret_content:
            try:
                json_data = json.loads(secret_content)
                secret_file_path = os.path.join(auth_dir, "secrets.json")
                with open(secret_file_path, "w") as f:
                    json.dump(json_data, f)
                logger.info(f"🔑 Secret injecté avec succès pour {user}")
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'écriture du secret pour {user}: {e}")

        device_id = os.getenv(f"DEVICEID_{user.upper()}")
        script_dest = os.path.join(user_dir, "ring_my_phone.py")
        
        if device_id and os.path.exists(template_path):
            try:
                with open(template_path, "r") as t:
                    content = t.read()
                custom_content = content.replace('TARGET_DEVICE_ID = "REPLACE_ME_DEVICE_ID"', f'TARGET_DEVICE_ID = "{device_id}"')
                with open(script_dest, "w") as f:
                    f.write(custom_content)
                logger.info(f"📱 Script personnalisé avec l'ID {device_id} pour {user}")
            except Exception as e:
                logger.error(f"❌ Erreur personnalisation script pour {user}: {e}")
        elif not device_id:
            logger.warning(f"⚠️ Variable DEVICEID_{user.upper()} manquante.")

        PATHS[user] = {"cwd": user_dir, "script": "ring_my_phone.py"}

initialize_environment()

def run_ring_script(config, target_key):
    logger.info(f"▶️ Début de la tâche en arrière-plan pour {target_key}")
    try:
        process = subprocess.run(
            [sys.executable, config["script"]], 
            cwd=config["cwd"], capture_output=True, text=True, timeout=45
        )
        if process.returncode == 0:
            logger.info(f"✅ Tâche terminée avec succès pour {target_key}.")
            logger.debug(f"Sortie script : {process.stdout}")
        else:
            logger.error(f"❌ Erreur script ({target_key}) : {process.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ Le script pour {target_key} a dépassé le délai de 45 secondes.")
    except Exception as e:
        logger.exception(f"💥 Erreur critique du sous-processus pour {target_key}")

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    def handle(self, handler_input):
        names_str = " ou ".join([name.capitalize() for name in USERS_LIST])
        txt = f"Bienvenue dans la localisation de téléphone. Qui voulez-vous faire sonner ? {names_str} ?"
        return handler_input.response_builder.speak(txt).ask(txt).response

class FindPhoneIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("FindPhoneIntent")(handler_input)
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        owner_slot = slots.get("Owner")
        target_key = None
        
        if owner_slot and owner_slot.resolutions and owner_slot.resolutions.resolutions_per_authority:
            if owner_slot.resolutions.resolutions_per_authority[0].status.code == "ER_SUCCESS_MATCH":
                target_key = owner_slot.resolutions.resolutions_per_authority[0].values[0].value.name.lower()
        
        if not target_key:
            target_key = owner_slot.value.lower() if (owner_slot and owner_slot.value) else USERS_LIST[0]

        logger.info(f"Cible identifiée : {target_key}")
        
        if target_key in PATHS:
            config = PATHS[target_key]
            if not os.path.exists(os.path.join(config["cwd"], config["script"])):
                return handler_input.response_builder.speak(f"Erreur : le script est absent pour {target_key}.").response
            
            threading.Thread(target=run_ring_script, args=(config, target_key)).start()
            speak_output = f"C'est fait, je lance la recherche du téléphone de {target_key}."
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

# --- NOUVEAU : Remplacement du routage manuel par l'Adapter Amazon ---
# Le SkillAdapter s'occupe de la vérification du certificat, du timestamp, et de l'ID de la skill.
skill_adapter = SkillAdapter(skill=skill, skill_id=ALEXA_SKILL_ID, app=app)

@app.route("/", methods=['POST'])
def invoke_skill():
    return skill_adapter.dispatch_request()

@app.route("/health", methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
