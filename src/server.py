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

# --- DICTIONNAIRE I18N ---
I18N = {
    "fr": {
        "welcome": "Bienvenue. Qui voulez-vous faire sonner ? {names} ?",
        "success": "C'est fait, je lance la recherche du téléphone de {target_key}.",
        "not_configured": "L'utilisateur {target_key} n'est pas configuré.",
        "error": "Une erreur système est survenue.",
        "or_word": " ou "
    },
    "en": {
        "welcome": "Welcome. Whose phone do you want to ring? {names}?",
        "success": "Done, I am ringing {target_key}'s phone.",
        "not_configured": "User {target_key} is not configured.",
        "error": "A system error has occurred.",
        "or_word": " or "
    }
}

def get_msg(handler_input, key, **kwargs):
    locale = handler_input.request_envelope.request.locale
    lang = locale.split('-')[0] if locale else "fr"
    msg = I18N.get(lang, I18N["fr"]).get(key, "")
    return msg.format(**kwargs) if kwargs else msg

# --- BANNIÈRE ---
def show_startup_banner():
    banner = """
===================================================================
 📱 ALEXA - FIND MY PHONE (V2.0.1 - STABLE EDITION)
===================================================================
 👤 Author      : Richard Perez (ripleyXLR8)
 📦 Version     : 2.0.1
 ⚙️  Mode        : Subprocess (Stability Optimized)
 🔒 Security    : Amazon Signature Verification Enabled
 🚀 Status      : GoogleTools Build-time Bundled
===================================================================
    """
    print(banner, flush=True)

show_startup_banner()

# --- CONFIGURATION ---
BASE_DIR = os.getenv("BASE_DIR", "/config")
USERS_LIST = [u.strip().lower() for u in os.getenv("USERS", "richard,lea").split(",")]
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID")
SOURCE_TOOLS = "/app/google_tools" 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AlexaSkill")

def initialize_environment():
    """Initialise les dossiers et les secrets au démarrage."""
    for user in USERS_LIST:
        user_dir = os.path.join(BASE_DIR, f"google-{user}")
        auth_dir = os.path.join(user_dir, "Auth")
        
        if not os.path.exists(user_dir):
            logger.info(f"📁 Initialisation des outils pour {user}...")
            shutil.copytree(SOURCE_TOOLS, user_dir)
        
        os.makedirs(auth_dir, exist_ok=True)
        
        secret_content = os.getenv(f"SECRET_{user.upper()}")
        if secret_content:
            try:
                json.loads(secret_content)
                with open(os.path.join(auth_dir, "secrets.json"), "w") as f:
                    f.write(secret_content)
                logger.info(f"🔑 Secret injecté pour {user}")
            except Exception as e:
                logger.error(f"❌ Erreur format secret pour {user}: {e}")

        # On génère le script local pour l'utilisateur
        device_id = os.getenv(f"DEVICEID_{user.upper()}")
        if device_id:
            try:
                with open("/app/ring_my_phone.py", "r") as f:
                    content = f.read()
                custom_content = content.replace('TARGET_DEVICE_ID = "REPLACE_ME_DEVICE_ID"', f'TARGET_DEVICE_ID = "{device_id}"')
                with open(os.path.join(user_dir, "ring_my_phone.py"), "w") as f:
                    f.write(custom_content)
                logger.info(f"📱 Script ring_my_phone.py généré pour {user}")
            except Exception as e:
                logger.error(f"❌ Erreur génération script pour {user}: {e}")

initialize_environment()

def run_ring_script(user_dir, user):
    """Exécute le script en subprocess pour garantir l'isolation de l'outil Google."""
    logger.info(f"▶️ Exécution du script pour {user}")
    try:
        process = subprocess.run(
            [sys.executable, "ring_my_phone.py"], 
            cwd=user_dir, capture_output=True, text=True, timeout=45
        )
        if process.returncode == 0:
            logger.info(f"✅ Succès pour {user}.")
        else:
            logger.error(f"❌ Erreur script ({user}) : {process.stderr}")
    except Exception as e:
        logger.error(f"💥 Erreur lors de l'exécution pour {user}: {e}")

class FindPhoneIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("FindPhoneIntent")(handler_input)
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        owner_slot = slots.get("Owner")
        target_key = owner_slot.value.lower() if (owner_slot and owner_slot.value) else USERS_LIST[0]
        
        user_dir = os.path.join(BASE_DIR, f"google-{target_key}")

        if target_key in USERS_LIST and os.path.exists(user_dir):
            threading.Thread(target=run_ring_script, args=(user_dir, target_key)).start()
            speak_output = get_msg(handler_input, "success", target_key=target_key.capitalize())
        else:
            speak_output = get_msg(handler_input, "not_configured", target_key=target_key.capitalize())
            
        return handler_input.response_builder.speak(speak_output).response

# ... (LaunchRequestHandler et CatchAllExceptionHandler identiques) ...

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    def handle(self, handler_input):
        or_word = get_msg(handler_input, "or_word")
        names_str = or_word.join([name.capitalize() for name in USERS_LIST])
        txt = get_msg(handler_input, "welcome", names=names_str)
        return handler_input.response_builder.speak(txt).ask(txt).response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception): return True
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak(get_msg(handler_input, "error")).response

app = Flask(__name__)
skill_builder = SkillBuilder()
skill_builder.add_request_handler(LaunchRequestHandler())
skill_builder.add_request_handler(FindPhoneIntentHandler())
skill_builder.add_exception_handler(CatchAllExceptionHandler())
skill_adapter = SkillAdapter(skill=skill_builder.create(), skill_id=ALEXA_SKILL_ID, app=app)

@app.route("/", methods=['POST'])
def invoke_skill(): return skill_adapter.dispatch_request()

@app.route("/health", methods=['GET'])
def health(): return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
