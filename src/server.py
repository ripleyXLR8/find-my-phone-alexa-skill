import logging
import os
import subprocess
import sys
import json
import shutil
import threading
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, Response
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
 📱 ALEXA - FIND MY PHONE (V3.0.0 - WEB UI EDITION)
===================================================================
 👤 Author      : Richard Perez (ripleyXLR8)
 📦 Version     : 3.0.0
 ⚙️  Mode        : Subprocess (Stability Optimized) + Web UI
 🔒 Security    : Amazon Signature Verification Enabled & Basic Auth
 🚀 Status      : GoogleTools Build-time Bundled
===================================================================
    """
    print(banner, flush=True)

show_startup_banner()

# --- CONFIGURATION ---
BASE_DIR = os.getenv("BASE_DIR", "/config")
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
SOURCE_TOOLS = "/app/google_tools" 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AlexaSkill")

app = Flask(__name__)

# ---------------------------------------------------------
# GESTION DES UTILISATEURS (Remplace l'ancienne approche)
# ---------------------------------------------------------
def load_users():
    """Charge la liste des utilisateurs depuis le fichier JSON persistant."""
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users_data):
    """Sauvegarde les utilisateurs et met à jour la liste globale."""
    with open(USERS_FILE, "w") as f:
        json.dump(users_data, f, indent=4)
    
    global USERS_LIST
    USERS_LIST = list(users_data.keys())

def setup_user_environment(user, data):
    """Crée le dossier et les scripts pour un utilisateur spécifique."""
    user_dir = os.path.join(BASE_DIR, f"google-{user}")
    auth_dir = os.path.join(user_dir, "Auth")
    
    if not os.path.exists(user_dir):
        logger.info(f"📁 Initialisation des outils pour {user}...")
        shutil.copytree(SOURCE_TOOLS, user_dir)
    
    os.makedirs(auth_dir, exist_ok=True)
    
    if "secret" in data:
        with open(os.path.join(auth_dir, "secrets.json"), "w") as f:
            f.write(data["secret"])
            
    if "device_id" in data:
        try:
            with open("/app/ring_my_phone.py", "r") as f:
                content = f.read()
            custom_content = content.replace('TARGET_DEVICE_ID = "REPLACE_ME_DEVICE_ID"', f'TARGET_DEVICE_ID = "{data["device_id"]}"')
            with open(os.path.join(user_dir, "ring_my_phone.py"), "w") as f:
                f.write(custom_content)
            logger.info(f"📱 Script ring_my_phone.py généré pour {user}")
        except Exception as e:
            logger.error(f"❌ Erreur génération script pour {user}: {e}")

# Initialisation au démarrage
USERS_DATA = load_users()
USERS_LIST = list(USERS_DATA.keys())
for user_name, user_data in USERS_DATA.items():
    setup_user_environment(user_name, user_data)

# ---------------------------------------------------------
# SÉCURITÉ DE L'INTERFACE WEB
# ---------------------------------------------------------
def check_auth(username, password):
    return username == 'admin' and password == ADMIN_PASSWORD

def authenticate():
    return Response(
    'Accès refusé. Veuillez vous connecter avec le compte admin.', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------------
# ROUTES DE L'INTERFACE WEB
# ---------------------------------------------------------
@app.route("/admin", methods=['GET'])
@requires_auth
def admin_dashboard():
    users = load_users()
    return render_template("admin.html", users=users)

@app.route("/admin/add", methods=['POST'])
@requires_auth
def add_user():
    username = request.form.get("username").strip().lower()
    device_id = request.form.get("device_id").strip()
    secret_json = request.form.get("secret_json").strip()
    
    try:
        json.loads(secret_json)
    except ValueError:
        return "Erreur : Le Secret n'est pas un JSON valide.", 400

    users = load_users()
    users[username] = {
        "device_id": device_id,
        "secret": secret_json
    }
    
    save_users(users)
    setup_user_environment(username, users[username])
    
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<username>", methods=['POST'])
@requires_auth
def delete_user(username):
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        user_dir = os.path.join(BASE_DIR, f"google-{username}")
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            
    return redirect(url_for("admin_dashboard"))

# ---------------------------------------------------------
# ALEXA SKILL LOGIC
# ---------------------------------------------------------
def run_ring_script(user_dir, user):
    """Exécute le script en subprocess pour garantir l'isolation."""
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
        
        global USERS_LIST
        # Prend le nom ciblé, ou le premier disponible s'il n'y a pas de slot
        target_key = owner_slot.value.lower() if (owner_slot and owner_slot.value) else (USERS_LIST[0] if USERS_LIST else None)
        
        if target_key:
            user_dir = os.path.join(BASE_DIR, f"google-{target_key}")

            if target_key in USERS_LIST and os.path.exists(user_dir):
                threading.Thread(target=run_ring_script, args=(user_dir, target_key)).start()
                speak_output = get_msg(handler_input, "success", target_key=target_key.capitalize())
            else:
                speak_output = get_msg(handler_input, "not_configured", target_key=target_key.capitalize())
        else:
            speak_output = get_msg(handler_input, "not_configured", target_key="inconnu")
            
        return handler_input.response_builder.speak(speak_output).response

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    def handle(self, handler_input):
        global USERS_LIST
        if USERS_LIST:
            or_word = get_msg(handler_input, "or_word")
            names_str = or_word.join([name.capitalize() for name in USERS_LIST])
            txt = get_msg(handler_input, "welcome", names=names_str)
        else:
            txt = "Bienvenue. Aucun utilisateur n'est configuré. Veuillez vous rendre sur l'interface d'administration."
            
        return handler_input.response_builder.speak(txt).ask(txt).response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception): return True
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak(get_msg(handler_input, "error")).response

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
