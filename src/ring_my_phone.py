import sys
from NovaApi.ExecuteAction.PlaySound.start_sound_request import start_sound_request
from NovaApi.nova_request import nova_request
from NovaApi.scopes import NOVA_ACTION_API_SCOPE
from Auth.fcm_receiver import FcmReceiver

TARGET_DEVICE_ID = "REPLACE_ME_DEVICE_ID" 

def ring():
    fcm = FcmReceiver()
    if fcm.credentials is None:
        fcm.get_android_id()
    gcm_id = fcm.credentials['fcm']['registration']['token']
    hex_payload = start_sound_request(TARGET_DEVICE_ID, gcm_id)
    nova_request(NOVA_ACTION_API_SCOPE, hex_payload)

if __name__ == '__main__':
    try:
        ring()
    except Exception as e:
        sys.exit(1)
