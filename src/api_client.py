import requests
import os

# --- URL del Endpoint en Laravel ---
# ¡IMPORTANTE! Debes reemplazar esto con la URL real de tu API.
API_URL = "COLOCA LA URL DE TU API"

def send_image_to_server(image_path):
    """
    Envía una imagen a un servidor y procesa la respuesta JSON.

    Args:
        image_path (str): La ruta completa al archivo de imagen.

    Returns:
        dict: Un diccionario con la respuesta JSON del servidor, o None si hay un error.
    """
    if not os.path.exists(image_path):
        print(f"Error: El archivo de imagen no se encuentra en la ruta: {image_path}")
        return None

    print(f"Enviando imagen '{os.path.basename(image_path)}' al servidor...")

    try:
        # Abrimos la imagen en modo de lectura binaria ('rb')
        with open(image_path, 'rb') as image_file:
            # Preparamos el archivo para la solicitud POST multipart/form-data
            files = {
                'image': (os.path.basename(image_path), image_file, 'image/png')
            }
            
            # Hacemos la solicitud POST con un timeout de 30 segundos
            response = requests.post(API_URL, files=files, timeout=30)
            
            # Lanza una excepción si la respuesta del servidor es un error (4xx o 5xx)
            response.raise_for_status()

            print("Respuesta recibida del servidor.")
            # Devolvemos la respuesta del servidor en formato JSON (diccionario)
            return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión o en la solicitud a la API: {e}")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado al enviar la imagen: {e}")
        return None
