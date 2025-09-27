import time
import os
from picamera2 import Picamera2

def setup_camera():
    """Inicializa y configura el objeto de la cámara."""
    try:
        picam2 = Picamera2()
        # Configuración para tener una previsualización si es necesario (no se muestra en este script)
        preview_config = picam2.create_preview_configuration()
        picam2.configure(preview_config)
        picam2.start()
        
        # Activar enfoque automático continuo, crucial para fotos nítidas
        picam2.set_controls({"AfMode": 2, "AfTrigger": 0})
        print("Cámara inicializada con autoenfoque continuo.")
        # Damos un momento para que la cámara se estabilice
        time.sleep(2)
        return picam2
    except Exception as e:
        print(f"Error al inicializar la cámara: {e}")
        return None

def take_photo(picam2, folder="images"):
    """
    Toma una fotografía con autoenfoque y la guarda en la carpeta especificada.
    
    Args:
        picam2: El objeto de la cámara ya inicializado.
        folder: La carpeta donde se guardarán las imágenes.
    """
    if not picam2:
        print("La cámara no está disponible.")
        return

    try:
        # 1. Asegurarse de que la carpeta de imágenes exista
        os.makedirs(folder, exist_ok=True)

        # 2. Generar un nombre de archivo único con la fecha y hora
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(folder, f"captura_{timestamp}.png")

        print("Enfocando y preparando para la captura...")
        
        # 3. Cambiar a configuración de alta resolución para la captura
        capture_config = picam2.create_still_configuration()
        picam2.switch_mode(capture_config)
        
        # 4. Esperar 1 segundo para que el autoenfoque se ajuste bien
        time.sleep(1)

        # 5. Tomar y guardar la foto en formato PNG
        picam2.capture_file(filepath)
        print(f"¡Foto guardada exitosamente en: {filepath}!")

    except Exception as e:
        print(f"Ocurrió un error al tomar la foto: {e}")
