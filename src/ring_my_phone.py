import os
import logging

# On importe les composants de l'outil Google (pré-installé dans l'image)
from NovaApi.ExecuteAction.PlaySound.start_sound_request import start_sound_request
from NovaApi.nova_request import nova_request
from NovaApi.scopes import NOVA_ACTION_API_SCOPE
from Auth.fcm_receiver import FcmReceiver

logger = logging.getLogger("AlexaSkill.RingModule")

def send_ring_command(device_id):
    """
    Logique native pour déclencher la sonnerie.
    L'appelant doit s'assurer d'être dans le bon répertoire pour trouver secrets.json.
    """
    try:
        fcm = FcmReceiver()
        
        # Initialisation des identifiants Google
        if fcm.credentials is None:
            fcm.get_android_id()
            
        gcm_id = fcm.credentials['fcm']['registration']['token']

        # Préparation et envoi de la requête
        hex_payload = start_sound_request(device_id, gcm_id)
        nova_request(NOVA_ACTION_API_SCOPE, hex_payload)
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à l'API Google : {e}")
        return False
