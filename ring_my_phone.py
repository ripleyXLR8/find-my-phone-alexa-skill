# Fichier: ring_my_phone.py
import sys
import asyncio
from NovaApi.ExecuteAction.PlaySound.start_sound_request import start_sound_request
from NovaApi.nova_request import nova_request
from NovaApi.scopes import NOVA_ACTION_API_SCOPE
from Auth.fcm_receiver import FcmReceiver

# Ce marqueur sera remplacé par le serveur au démarrage via la variable DEVICEID_[USER]
TARGET_DEVICE_ID = "REPLACE_ME_DEVICE_ID" 

def ring():
    """Déclenche la sonnerie sur l'appareil Google cible."""
    print(f"Tentative de sonnerie sur : {TARGET_DEVICE_ID}")
    
    # Initialisation du récepteur FCM pour récupérer les jetons d'authentification
    fcm = FcmReceiver()
    
    # Chargement forcé des identifiants s'ils ne sont pas présents
    if fcm.credentials is None:
        fcm.get_android_id()
        
    # Extraction du jeton d'enregistrement GCM nécessaire pour la requête Google
    gcm_id = fcm.credentials['fcm']['registration']['token']

    # Construction de la charge utile (payload) pour la requête de sonnerie
    hex_payload = start_sound_request(TARGET_DEVICE_ID, gcm_id)
    
    # Envoi de la commande de sonnerie via l'API Nova de Google
    nova_request(NOVA_ACTION_API_SCOPE, hex_payload)
    print("Commande envoyée avec succès.")

if __name__ == '__main__':
    try:
        ring()
    except Exception as e:
        print(f"Erreur lors de l'exécution du script de sonnerie : {e}")
        sys.exit(1)
