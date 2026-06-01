import re
import secrets
import string
import requests
from django.conf import settings


EVOLUTION_URL = getattr(settings, 'EVOLUTION_API_URL', 'http://localhost:8080')
EVOLUTION_KEY = getattr(settings, 'EVOLUTION_API_KEY', 'superapikey')
EVOLUTION_INSTANCE = getattr(settings, 'EVOLUTION_INSTANCE', 'elcarguero')


def generar_password():
    """Generate a memorable, secure password like Polla2026#A7k2."""
    chars = string.ascii_letters + string.digits
    aleatorio = ''.join(secrets.choice(chars) for _ in range(6))
    return f"Polla2026#{aleatorio}"


def normalizar_telefono(telefono: str) -> str:
    """Return only digits. Assumes international format (e.g. 59171234567)."""
    return re.sub(r'\D', '', telefono)


def enviar_credenciales_whatsapp(telefono: str, nombre: str, username: str, password: str) -> tuple[bool, str]:
    """
    Send login credentials via WhatsApp using Evolution API.
    Returns (success: bool, message: str).
    """
    numero = normalizar_telefono(telefono)
    if not numero:
        return False, 'Número de teléfono inválido.'

    # WhatsApp JID format
    jid = f"{numero}@s.whatsapp.net"

    mensaje = (
        f"⚽ *Mi Polla Mundial 2026*\n\n"
        f"Hola {nombre}, ya tienes acceso a la polla.\n\n"
        f"🔗 *Enlace:* https://www.elcarguero.com/MiPolla/\n"
        f"👤 *Usuario:* `{username}`\n"
        f"🔑 *Contraseña:* `{password}`\n\n"
        f"_Ingresa y cambia tu contraseña. ¡Buena suerte!_ 🏆"
    )

    try:
        resp = requests.post(
            f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}",
            json={"number": jid, "text": mensaje},
            headers={"apikey": EVOLUTION_KEY},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True, f'Credenciales enviadas por WhatsApp a {numero}.'
        return False, f'Evolution API respondió {resp.status_code}: {resp.text[:120]}'
    except requests.exceptions.ConnectionError:
        return False, 'No se pudo conectar con Evolution API.'
    except requests.exceptions.Timeout:
        return False, 'Timeout al conectar con Evolution API.'
    except Exception as e:
        return False, f'Error inesperado: {e}'
