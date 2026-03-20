import os
import time
import logging
from typing import Optional
from picamera2 import Picamera2

# Importamos las rutas seguras que creamos en el paso anterior
from config import settings

# Configuramos el logger para este módulo
logger = logging.getLogger(__name__)

def setup_camera() -> Optional[Picamera2]:
    """Inicializa y configura la cámara con autoenfoque."""
    try:
        picam2 = Picamera2()
        preview_config = picam2.create_preview_configuration()
        picam2.configure(preview_config)
        picam2.start()
        
        picam2.set_controls({"AfMode": 2, "AfTrigger": 0})
        logger.info("Cámara inicializada con autoenfoque continuo.")
        time.sleep(2)
        return picam2
    except Exception as e:
        logger.critical(f"No se pudo inicializar la cámara. Detalle: {e}")
        return None

def take_photo(picam2: Picamera2) -> Optional[str]:
    """Toma una fotografía, la guarda en la ruta configurada y retorna el path."""
    if not picam2:
        logger.error("Intento de captura sin cámara disponible.")
        return None

    try:
        os.makedirs(settings.IMAGES_DIR, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(settings.IMAGES_DIR, f"captura_{timestamp}.jpg")

        logger.info("Enfocando y preparando para la captura...")
        capture_config = picam2.create_still_configuration(main={"size": (1280, 720)})
        picam2.switch_mode(capture_config)
        time.sleep(1)

        picam2.capture_file(filepath)
        logger.info(f"Foto guardada exitosamente en: {filepath}")
        
        return filepath
    except Exception as e:
        logger.error(f"Fallo al tomar la foto: {e}")
        return None