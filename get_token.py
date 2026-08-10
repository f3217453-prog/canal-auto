"""
Script para regenerar YOUTUBE_REFRESH_TOKEN
Ejecutar UNA VEZ en tu computadora local, no en GitHub Actions.

Requisitos:
    pip install google-auth-oauthlib

Pasos:
    1. Ejecuta este script: python get_token.py
    2. Se abre el navegador con la pantalla de Google
    3. Inicia sesion con la cuenta del canal de YouTube
    4. Acepta los permisos
    5. Copia el REFRESH TOKEN que aparece en la terminal
    6. Ve a GitHub → Settings → Secrets → Actions
    7. Actualiza el secret YOUTUBE_REFRESH_TOKEN con el nuevo valor
"""

from google_auth_oauthlib.flow import InstalledAppFlow

# Pega aqui tus credenciales de Google Cloud Console
# (las mismas que tienes en los secrets de GitHub)
CLIENT_ID = "PEGA_AQUI_TU_YOUTUBE_CLIENT_ID"
CLIENT_SECRET = "PEGA_AQUI_TU_YOUTUBE_CLIENT_SECRET"

CLIENT_CONFIG = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
creds = flow.run_local_server(port=0)

print("\n" + "="*60)
print("COPIA ESTE REFRESH TOKEN Y PONLO EN TUS SECRETS DE GITHUB:")
print("="*60)
print(creds.refresh_token)
print("="*60 + "\n")
