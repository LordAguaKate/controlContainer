import requests
import os
from src.config import CONTAINER_ID # Solo importamos el ID del contenedor
# --- URL del Endpoint en Laravel ---
# ¡IMPORTANTE! Debes reemplazar esto con la URL real de tu API.
API_URL = "COLOCA LA URL DE TU API"

# --- MODIFICADO ---
# La función ahora ACEPTA el user_id como parámetro.
def send_image_to_server(image_path, user_id):
    """
    Envía una imagen junto con el ID del contenedor y el ID del usuario (dinámico)
    a un servidor y procesa la respuesta JSON.
    """

    # Usamos el user_id que recibimos como argumento.
    if not os.path.exists(image_path):
        print(f"Error: El archivo de imagen no se encuentra en la ruta: {image_path}")
        return None

    print(f"Enviando imagen '{os.path.basename(image_path)}' al servidor con container_id={CONTAINER_ID} y user_id={user_id}...")

    try:
        # 1. Preparamos los campos de datos adicionales
        data_payload = {
            'container_id': CONTAINER_ID,
            'user_id': user_id
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
            response.encoding = 'utf-8'

            # --- MEJORA DE DIAGNoSTICO ---
            if response.status_code == 200 or response.status_code == 422:
                print("Respuesta recibida del servidor.")
                return response.json() # Devolvemos el JSON en ambos casos
            else:
                # Para otros errores (como 500), sí los mostramos y fallamos.
                print("--- INICIO DE RESPUESTA DE ERROR INESPERADO ---")
                print(f"Código de Estado: {response.status_code}, Cuerpo: {response.text}")
                print("--- FIN DE RESPUESTA DE ERROR INESPERADO ---")
                return None

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión a la API: {e}")
        return None