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

# 🚀 FIX SENIOR : Import direct du module ring_my_phone (pas de subprocess)
from ring_my_phone import send_ring_command

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
    msg = I18N.get(lang, I18N["fr"]).get(key, "")
    return msg.format(**kwargs) if kwargs else msg

# --- BANNIÈRE DE DÉMARRAGE (Restaurée et Upgradée) ---
def show_startup_banner():
    banner = """
===================================================================
 📱 ALEXA - FIND MY PHONE (V2.0.0 SENIOR EDITION)
===================================================================
 👤 Author      : Richard Perez (ripleyXLR8)
 📦 Version     : 2.0.0 - Production Ready
 ⚙️  Mode        : Native Python Module (No Subprocess)
 🔒 Security    : Amazon Signature Verification Enabled
 🩺 Health      : Active
 🚀 Status      : GoogleTools Build-time Bundled
===================================================================
    """
    print(banner, flush=True)

show_startup_banner()

# --- CONFIGURATION DYNAMIQUE ---
BASE_DIR = os.getenv("BASE_DIR", "/config")
USERS_ENV = os.getenv("USERS", "richard,lea")
USERS_LIST = [u.strip().lower() for u in USERS_ENV.split(",")]
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID")
SOURCE_TOOLS = "/app/google_tools" 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AlexaSkill")

def initialize_environment():
    """Initialise les dossiers et les secrets au démarrage."""
    for user in USERS_LIST:
        user_dir = os.path.join(BASE_DIR, f"google-{user}")
        auth_dir = os.path.join(user_dir, "Auth")
        
        # Copie de la source interne (Build-time) vers le dossier persistant
        if not os.path.exists(user_dir):
            logger.info(f"📁 Initialisation des outils pour {user}...")
            shutil.copytree(SOURCE_TOOLS, user_dir)
        
        os.makedirs(auth_dir, exist_ok=True)
        
        # Injection du secret depuis la variable d'env
        secret_content = os.getenv(f"SECRET_{user.upper()}")
        if secret_content:
            try:
                json.loads(secret_content) # Vérification format JSON
                with open(os.path.join(auth_dir, "secrets.json"), "w") as f:
                    f.write(secret_content)
                logger.info(f"🔑 Secret injecté pour {user}")
            except Exception as e:
                logger.error(f"❌ Erreur format secret pour {user}: {e}")

initialize_environment()

# --- LOGIQUE DE SONNERIE ---
def async_ring(user, device_id):
    """Exécute la sonnerie nativement dans un thread séparé."""
    user_dir = os.path.join(BASE_DIR, f"google-{user}")
    original_cwd = os.getcwd()
    
    try:
        # 🚀 FIX SENIOR : On change de répertoire pour que le module trouve ses secrets locaux
        os.chdir(user_dir)
        logger.info(f"▶️ Appel natif du module Google pour {user}")
        if send_ring_command(device_id):
            logger.info(f"✅ Succès pour {user}")
        else:
            logger.error(f"❌ Échec de la commande pour {user}")
    except Exception as e:
        logger.error(f"💥 Erreur lors de l'exécution pour {user}: {e}")
    finally:
        os.chdir(original_cwd)

# --- HANDLERS ALEXA ---
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
        target_key = owner_slot.value.lower() if (owner_slot and owner_slot.value) else USERS_LIST[0]
        
        device_id = os.getenv(f"DEVICEID_{target_key.upper()}")

        if target_key in USERS_LIST and device_id:
            # 🚀 FIX SENIOR : Lancement du thread direct sans subprocess
            threading.Thread(target=async_ring, args=(target_key, device_id)).start()
            speak_output = get_msg(handler_input, "success", target_key=target_key.capitalize())
        else:
            speak_output = get_msg(handler_input, "not_configured", target_key=target_key.capitalize())
            
        return handler_input.response_builder.speak(speak_output).response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception): return True
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak(get_msg(handler_input, "error")).response

# --- APP FLASK ---
app = Flask(__name__)
skill_builder = SkillBuilder()
skill_builder.add_request_handler(LaunchRequestHandler())
skill_builder.add_request_handler(FindPhoneIntentHandler())
skill_builder.add_exception_handler(CatchAllExceptionHandler())

skill_adapter = SkillAdapter(skill=skill_builder.create(), skill_id=ALEXA_SKILL_ID, app=app)

@app.route("/", methods=['POST'])
def invoke_skill():
    return skill_adapter.dispatch_request()

@app.route("/health", methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
