import os
import logging

# On importe les composants de l'outil Google (pré-installés dans l'image via PYTHONPATH)
try:
    from NovaApi.ExecuteAction.PlaySound.start_sound_request import start_sound_request
    from NovaApi.nova_request import nova_request
    from NovaApi.scopes import NOVA_ACTION_API_SCOPE
    from Auth.fcm_receiver import FcmReceiver
except ImportError:
    # Fallback pour le développement local
    pass

logger = logging.getLogger("AlexaSkill.RingModule")

def send_ring_command(device_id):
    """
    Déclenche la sonnerie en utilisant directement les classes Python de GoogleTools.
    L'appelant (server.py) doit s'être déplacé dans le répertoire contenant secrets.json.
    """
    try:
        fcm = FcmReceiver()
        
        # Initialisation automatique des identifiants Google via les fichiers locaux
        if fcm.credentials is None:
            fcm.get_android_id()
            
        gcm_id = fcm.credentials['fcm']['registration']['token']

        # Préparation et envoi de la requête à l'API Google
        hex_payload = start_sound_request(device_id, gcm_id)
        nova_request(NOVA_ACTION_API_SCOPE, hex_payload)
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à l'API Google : {e}")
        return False
