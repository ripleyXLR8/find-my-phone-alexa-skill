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
from flask_ask_sdk.skill_adapter import SkillAdapter

# --- DICTIONNAIRE MULTILINGUE (i18n) ---
I18N = {
    "fr": {
        "welcome": "Bienvenue dans la localisation de téléphone. Qui voulez-vous faire sonner ? {names} ?",
        "success": "C'est fait, je lance la recherche du téléphone de {target_key}.",
        "not_configured": "Désolé, l'utilisateur {target_key} n'est pas configuré.",
        "error": "Une erreur système est survenue.",
        "or_word": " ou "
    },
    "en": {
        "welcome": "Welcome to phone locator. Whose phone do you want to ring? {names}?",
        "success": "Done, I am ringing {target_key}'s phone.",
        "not_configured": "Sorry, user {target_key} is not configured.",
        "error": "A system error has occurred.",
        "or_word": " or "
    }
}

def get_msg(handler_input, key, **kwargs):
    """Récupère le message traduit en fonction de la locale d'Alexa."""
    locale = handler_input.request_envelope.request.locale
    lang = locale.split('-')[0] if locale else "fr"
    if lang not in I18N:
        lang = "fr"
    msg = I18N[lang].get(key, "")
    return msg.format(**kwargs) if kwargs else msg

# --- BANNIÈRE DE DÉMARRAGE ---
def show_startup_banner():
    banner = """
===================================================================
 📱 ALEXA - FIND MY PHONE (V2.0 - BUILD-TIME READY)
===================================================================
 👤 Author      : Richard Perez (ripleyXLR8)
 📦 Version     : 2.0.0 (Senior Fix Step 1)
 ⚙️  Environment : Unraid / Docker (Stateless)
 🔒 Security    : Amazon Signature Verification Enabled
 🚀 Status      : GoogleTools pre-installed in image
===================================================================
    """
    print(banner, flush=True)

show_startup_banner()

# --- CONFIGURATION DYNAMIQUE ---
BASE_DIR = os.getenv("BASE_DIR", "/config")
USERS_ENV = os.getenv("USERS", "richard,lea")
USERS_LIST = [u.strip().lower() for u in USERS_ENV.split(",")]
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID")
# Chemin de la source pré-clonée dans le Dockerfile
SOURCE_TOOLS = "/app/google_tools" 

PATHS = {}

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AlexaSkill")

def initialize_environment():
    """Initialise les dossiers en copiant la source interne (Senior Fix)."""
    template_path = "/app/ring_my_phone.py.template"

    for user in USERS_LIST:
        user_dir = os.path.join(BASE_DIR, f"google-{user}")
        auth_dir = os.path.join(user_dir, "Auth")
        
        # 🚀 FIX SENIOR : On copie depuis l'image au lieu de cloner depuis le web
        if not os.path.exists(user_dir):
            logger.info(f"📁 Initialisation des outils pour {user} depuis la source interne...")
            shutil.copytree(SOURCE_TOOLS, user_dir)
        
        os.makedirs(auth_dir, exist_ok=True)
        secret_env_name = f"SECRET_{user.upper()}"
        secret_content = os.getenv(secret_env_name)
        
        if secret_content:
            try:
                json_data = json.loads(secret_content)
                with open(os.path.join(auth_dir, "secrets.json"), "w") as f:
                    json.dump(json_data, f)
                logger.info(f"🔑 Secret injecté pour {user}")
            except Exception as e:
                logger.error(f"❌ Erreur secret pour {user}: {e}")

        device_id = os.getenv(f"DEVICEID_{user.upper()}")
        script_dest = os.path.join(user_dir, "ring_my_phone.py")
        
        if device_id and os.path.exists(template_path):
            try:
                with open(template_path, "r") as t:
                    content = t.read()
                custom_content = content.replace('TARGET_DEVICE_ID = "REPLACE_ME_DEVICE_ID"', f'TARGET_DEVICE_ID = "{device_id}"')
                with open(script_dest, "w") as f:
                    f.write(custom_content)
                logger.info(f"📱 Script personnalisé pour {user}")
            except Exception as e:
                logger.error(f"❌ Erreur script pour {user}: {e}")

        PATHS[user] = {"cwd": user_dir, "script": "ring_my_phone.py"}

initialize_environment()

def run_ring_script(config, target_key):
    """Exécute le script de localisation."""
    logger.info(f"▶️ Exécution du script pour {target_key}")
    try:
        process = subprocess.run(
            [sys.executable, config["script"]], 
            cwd=config["cwd"], capture_output=True, text=True, timeout=45
        )
        if process.returncode == 0:
            logger.info(f"✅ Succès pour {target_key}.")
        else:
            logger.error(f"❌ Erreur script ({target_key}) : {process.stderr}")
    except Exception as e:
        logger.error(f"💥 Erreur lors de l'exécution pour {target_key}: {e}")

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    def handle(self, handler_input):
        or_word = get_msg(handler_input, "or_word")
        names_str = or_word.join([name.capitalize() for name in USERS_LIST])
        txt = get_msg(handler_input, "welcome", names=names_str)
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

        if target_key in PATHS:
            config = PATHS[target_key]
            threading.Thread(target=run_ring_script, args=(config, target_key)).start()
            speak_output = get_msg(handler_input, "success", target_key=target_key.capitalize())
        else:
            speak_output = get_msg(handler_input, "not_configured", target_key=target_key.capitalize())
            
        return handler_input.response_builder.speak(speak_output).response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak_output = get_msg(handler_input, "error")
        return handler_input.response_builder.speak(speak_output).response

app = Flask(__name__)
skill_builder = SkillBuilder()
skill_builder.add_request_handler(LaunchRequestHandler())
skill_builder.add_request_handler(FindPhoneIntentHandler())
skill_builder.add_exception_handler(CatchAllExceptionHandler())
skill = skill_builder.create()

skill_adapter = SkillAdapter(skill=skill, skill_id=ALEXA_SKILL_ID, app=app)

@app.route("/", methods=['POST'])
def invoke_skill():
    return skill_adapter.dispatch_request()

@app.route("/health", methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
