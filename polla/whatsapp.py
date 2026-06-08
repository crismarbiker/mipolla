import re
import secrets
import string
import requests
from django.conf import settings


def _cfg(key, default=''):
    return getattr(settings, key, default)


def generar_password() -> str:
    """Generate a 6-char password: uppercase letters + digits. Example: A7K2P9"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))


def normalizar_telefono(telefono: str) -> str:
    """Strip non-digits. Input should already include country code."""
    return re.sub(r'\D', '', telefono)


def enviar_credenciales_whatsapp(
    telefono: str,
    nombre: str,
    username: str,
    password: str,
) -> tuple[bool, str]:
    """
    Send login credentials via WhatsApp using Evolution API.
    Returns (success: bool, detail_message: str).
    """
    api_url  = _cfg('EVOLUTION_API_URL',  'http://elcarguero_evolution:8080')
    api_key  = _cfg('EVOLUTION_API_KEY',  '')
    instance = _cfg('EVOLUTION_INSTANCE', 'elcarguero')
    app_url  = _cfg('APP_URL', 'https://www.elcarguero.com/MiPolla/')

    if not api_key:
        return False, 'EVOLUTION_API_KEY no configurada en el servidor.'

    numero = normalizar_telefono(telefono)
    if not numero or len(numero) < 8:
        return False, f'Número de teléfono inválido: "{telefono}".'

    # Load tournament name dynamically
    try:
        from .models import TorneoConfig
        torneo = TorneoConfig.get()
        torneo_nombre = f"{torneo.nombre} {torneo.temporada}".strip()
    except Exception:
        torneo_nombre = 'Mi Polla'

    jid = f"{numero}@s.whatsapp.net"
    mensaje = (
        f"⚽ *{torneo_nombre}* — ¡Bienvenido!\n\n"
        f"Hola {nombre}! 👋 Ya estás adentro de la polla, que empiece el show 🎉\n\n"
        f"Aquí tus datos pa entrar:\n"
        f"🔗 {app_url}\n"
        f"📱 *Usuario:* `{username}`\n"
        f"🔑 *Clave:* `{password}`\n\n"
        f"Si olvidás tu clave, ingresá a la plataforma y usá la opción *\"Olvidé mi contraseña\"* 🔑\n\n"
        f"¡Mucha suerte y que gane el mejor! 🏆⚽"
    )

    try:
        resp = requests.post(
            f"{api_url}/message/sendText/{instance}",
            json={"number": jid, "text": mensaje},
            headers={"apikey": api_key},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True, f'WhatsApp enviado a +{numero}.'
        return False, f'Evolution API respondió HTTP {resp.status_code}: {resp.text[:150]}'
    except requests.exceptions.ConnectionError:
        return False, f'No se pudo conectar a Evolution API ({api_url}).'
    except requests.exceptions.Timeout:
        return False, 'Timeout al conectar con Evolution API (10 s).'
    except Exception as e:
        return False, f'Error inesperado: {e}'


def enviar_nueva_clave_whatsapp(telefono: str, nombre: str, password: str) -> None:
    """Send a password recovery message — friendlier, shorter tone."""
    api_url  = _cfg('EVOLUTION_API_URL',  '')
    api_key  = _cfg('EVOLUTION_API_KEY',  '')
    instance = _cfg('EVOLUTION_INSTANCE', '')
    app_url  = _cfg('APP_URL', 'https://www.elcarguero.com/MiPolla/')

    if not api_key:
        return

    numero = normalizar_telefono(telefono)
    if not numero:
        return

    try:
        from .models import TorneoConfig
        torneo_nombre = str(TorneoConfig.get())
    except Exception:
        torneo_nombre = 'Mi Polla'

    mensaje = (
        f"🔑 *{torneo_nombre}* — Nueva clave\n\n"
        f"Hola {nombre}! 👋 Aquí va:\n\n"
        f"📱 *Usuario:* `{numero}`\n"
        f"🔑 *Clave:* `{password}`\n\n"
        f"🔗 {app_url}\n\n"
        f"¡Entra antes de que empiece el próximo partido! ⏰"
    )
    try:
        requests.post(
            f"{api_url}/message/sendText/{instance}",
            json={"number": f"{numero}@s.whatsapp.net", "text": mensaje},
            headers={"apikey": api_key},
            timeout=8,
        )
    except Exception:
        pass


def registrar_webhook(webhook_url: str) -> tuple[bool, str]:
    """Register the webhook URL in Evolution API for MESSAGES_UPSERT events."""
    api_url  = _cfg('EVOLUTION_API_URL',  '')
    api_key  = _cfg('EVOLUTION_API_KEY',  '')
    instance = _cfg('EVOLUTION_INSTANCE', '')

    if not api_key:
        return False, 'EVOLUTION_API_KEY no configurada.'

    try:
        # Evolution API v2.2.3 format: body wrapped in "webhook" key
        resp = requests.post(
            f"{api_url}/webhook/set/{instance}",
            json={
                "webhook": {
                    "url": webhook_url,
                    "events": ["MESSAGES_UPSERT"],
                    "enabled": True,
                }
            },
            headers={"apikey": api_key},
            timeout=8,
        )
        if resp.status_code in (200, 201):
            return True, f'Webhook registrado en {instance}: {webhook_url}'
        return False, f'API respondió {resp.status_code}: {resp.text[:120]}'
    except Exception as e:
        return False, f'Error: {e}'


def verificar_conexion() -> tuple[bool, str]:
    """Check if Evolution API instance is online. Used by admin UI."""
    api_url  = _cfg('EVOLUTION_API_URL',  '')
    api_key  = _cfg('EVOLUTION_API_KEY',  '')
    instance = _cfg('EVOLUTION_INSTANCE', '')

    if not api_key:
        return False, 'EVOLUTION_API_KEY no configurada.'

    try:
        resp = requests.get(
            f"{api_url}/instance/connectionState/{instance}",
            headers={"apikey": api_key},
            timeout=6,
        )
        if resp.status_code == 200:
            data = resp.json()
            state = data.get('instance', {}).get('state', '?')
            ok = state == 'open'
            return ok, f'Estado WhatsApp: *{state}*' + (' ✅' if ok else ' ❌ (desconectado)')
        return False, f'API respondió {resp.status_code}'
    except Exception as e:
        return False, f'Error: {e}'
