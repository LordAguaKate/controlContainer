import requests
import os
from src.config import CONTAINER_ID, USER_ID  # Importamos los IDs desde el archivo de configuración

# --- URL del Endpoint en Laravel ---
# ¡IMPORTANTE! Debes reemplazar esto con la URL real de tu API.
API_URL = "COLOCA LA URL DE TU API"

def send_image_to_server(image_path):
    """
    Envia una imagen junto con los IDs a un servidor y procesa la respuesta JSON.
    Incluye un manejo de errores mejorado para diagnostico.
    """
    if not os.path.exists(image_path):
        print(f"Error: El archivo de imagen no se encuentra en la ruta: {image_path}")
        return None

    print(f"Enviando imagen '{os.path.basename(image_path)}' al servidor con container_id={CONTAINER_ID} y user_id={USER_ID}...")

    try:
        # 1. Preparamos los campos de datos adicionales
        data_payload = {
            'container_id': CONTAINER_ID,
            'user_id': USER_ID
        }
        # 2. Abrimos la imagen en modo de lectura binaria ('rb')
        with open(image_path, 'rb') as image_file:
            # 3. Preparamos el archivo para la solicitud POST multipart/form-data
            files_payload = {
                'image': (os.path.basename(image_path), image_file, 'image/jpeg')
            }
            
            # 4. Hacemos la solicitud POST con un timeout de 30 segundos
            response = requests.post(API_URL, data=data_payload, files=files_payload, timeout=120)
            
            # 5. Lanza una excepción si la respuesta del servidor es un error (4xx o 5xx)
            response.raise_for_status()

            # --- MEJORA DE DIAGNoSTICO ---
            # Si el codigo de estado indica un error (4xx o 5xx), imprimimos el cuerpo
            # completo de la respuesta antes de lanzar la excepcion.
            if not response.ok:
                print("--- INICIO DE RESPUESTA DE ERROR DEL SERVIDOR ---")
                print(f"Codigo de Estado: {response.status_code}")
                print("Cuerpo de la Respuesta:")
                print(response.text) # Esto imprimira el error completo que envia Laravel
                print("--- FIN DE RESPUESTA DE ERROR DEL SERVIDOR ---")
            
            response.raise_for_status()

            print("Respuesta recibida del servidor.")
            return response.json()

    except requests.exceptions.HTTPError:
        print(f"Error HTTP: La solicitud fue enviada pero el servidor respondio con un error.")
        print(f"Revisa la 'Respuesta de Error del Servidor' mostrada arriba para mas detalles.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error de conexion o en la solicitud a la API: {e}")
        return None
    except Exception as e:
        print(f"Ocurrio un error inesperado al enviar la imagen: {e}")
        return None
