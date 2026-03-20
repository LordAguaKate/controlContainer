import requests
import logging
from typing import Tuple, Optional
from config import settings

logger = logging.getLogger(__name__)

def validate_token(token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Valida el token contra la API remota.
    Retorna una tupla (user_id, user_name) si es válido, o (None, None) si falla.
    """
    if not token:
        return None, None

    try:
        logger.info(f"Validando token con la API...")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Usamos la URL segura desde nuestro settings (.env)
        response = requests.post(settings.API_AUTH_URL, headers=headers, timeout=20)

        if response.status_code == 200:
            data = response.json()
            user = data.get("data", {}).get("user", {})
            user_id = user.get("id")
            user_name = user.get("name")
            
            if user_id and user_name:
                logger.info(f"Usuario validado correctamente: {user_name}")
                return user_id, user_name
            else:
                logger.warning("La API respondió 200 OK pero faltan datos del usuario.")
                return None, None
        else:
            logger.warning(f"Error de validación. HTTP {response.status_code}")
            return None, None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión con API de validación: {e}")
        return None, None