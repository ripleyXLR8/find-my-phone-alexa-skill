import logging
import os
import json
import shutil
import threading
from flask import Flask
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from flask_ask_sdk.skill_adapter import SkillAdapter

# 🚀 FIX SENIOR : Import direct de notre propre module
from ring_my_phone import send_ring_command

# --- CONFIGURATION ET I18N ---
BASE_DIR = os.getenv("BASE_DIR", "/config")
USERS_LIST = [u.strip().lower() for u in os.getenv("USERS", "richard,lea").split(",")]
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID")
SOURCE_TOOLS = "/app/google_tools"

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AlexaSkill")

def get_msg(handler_input, key, **kwargs):
    locale = handler_input.request_envelope.request.locale
    lang = locale.split('-')[0] if locale else "fr"
    msg = I18N.get(lang, I18N["fr"]).get(key, "")
    return msg.format(**kwargs) if kwargs else msg

# --- INITIALISATION ---
def initialize_environment():
    """Prépare uniquement les secrets et les dossiers (Plus de templates !)."""
    for user in USERS_LIST:
        user_dir = os.path.join(BASE_DIR, f"google-{user}")
        auth_dir = os.path.join(user_dir, "Auth")
        
        if not os.path.exists(user_dir):
            logger.info(f"📁 Création du dossier utilisateur pour {user}...")
            shutil.copytree(SOURCE_TOOLS, user_dir)
        
        os.makedirs(auth_dir, exist_ok=True)
        secret_content = os.getenv(f"SECRET_{user.upper()}")
        if secret_content:
            with open(os.path.join(auth_dir, "secrets.json"), "w") as f:
                f.write(secret_content)
            logger.info(f"🔑 Secret synchronisé pour {user}")

initialize_environment()

# --- LOGIQUE DE SONNERIE ---
def async_ring(user, device_id):
    """Exécute la sonnerie de manière native et isolée."""
    user_dir = os.path.join(BASE_DIR, f"google-{user}")
    original_cwd = os.getcwd()
    
    try:
        # 🚀 FIX SENIOR : On se déplace dans le dossier de l'utilisateur pour que
        # la bibliothèque trouve le bon secrets.json dans ./Auth/
        os.chdir(user_dir)
        if send_ring_command(device_id):
            logger.info(f"✅ Succès pour {user}")
        else:
            logger.error(f"❌ Échec pour {user}")
    finally:
        os.chdir(original_cwd)

# --- HANDLERS ALEXA ---
class FindPhoneIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("FindPhoneIntent")(handler_input)
    
    def handle(self, handler_input):
        # Récupération simplifiée du nom
        slots = handler_input.request_envelope.request.intent.slots
        owner = slots.get("Owner").value.lower() if slots.get("Owner") else USERS_LIST[0]
        
        device_id = os.getenv(f"DEVICEID_{owner.upper()}")
        
        if owner in USERS_LIST and device_id:
            # 🚀 FIX SENIOR : On lance la fonction Python directement dans un thread
            threading.Thread(target=async_ring, args=(owner, device_id)).start()
            speak_output = get_msg(handler_input, "success", target_key=owner.capitalize())
        else:
            speak_output = get_msg(handler_input, "not_configured", target_key=owner.capitalize())
            
        return handler_input.response_builder.speak(speak_output).response

# ... (LaunchRequestHandler et CatchAllExceptionHandler identiques à v1.3) ...

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
