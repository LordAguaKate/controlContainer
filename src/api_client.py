import requests
import os
from src.config import CONTAINER_ID # Solo importamos el ID del contenedor
# --- URL del Endpoint en Laravel ---
# ¡IMPORTANTE! Debes reemplazar esto con la URL real de tu API.
API_URL = "COLOCA LA URL DE TU API"
UPDATE_CAPACITY_URL = "COLOCA LA URL DE TU API"

def send_image_to_server(image_path, user_id):
    """
    Envia una imagen junto con el ID del contenedor y el ID del usuario.
    """
    if not os.path.exists(image_path):
        print(f"Error: El archivo de imagen no se encuentra en la ruta: {image_path}")
        return None

    print(f"Enviando imagen... (User: {user_id}, Contenedor: {CONTAINER_ID})")

    try:
        data_payload = {
            'container_id': CONTAINER_ID,
            'user_id': user_id
        }
        with open(image_path, 'rb') as image_file:
            files_payload = {
                'image': (os.path.basename(image_path), image_file, 'image/jpeg')
            }
            # POST request
            response = requests.post(SCAN_URL, data=data_payload, files=files_payload, timeout=120)
            
            if response.status_code == 200 or response.status_code == 422:
                return response.json()
            else:
                print(f"Error API (Scan): {response.status_code} - {response.text}")
                return None

    except requests.exceptions.RequestException as e:
        print(f"Error de conexion (Scan): {e}")
        return None

# --- NUEVA FUNCION: ACTUALIZAR NIVELES ---
def update_container_capacity(alu_val, pla_val, basura_val):
    """
    Envia los niveles de los sensores ultrasonicos a la API mediante PUT.
    Espera valores enteros (cm).
    """
    print(f"[API] Actualizando niveles -> Alu: {alu_val}, Pla: {pla_val}, Bas: {basura_val}...")

    try:
        # Estructura JSON segun tu imagen
        # NOTA: Asumiendo el orden de sensores que pediste.
        payload = {
            "capacity": {
                "sensor1": int(pla_val),
                "sensor2": int(basura_val),
                "sensor3": int(alu_val)
            }
        }

        # Header necesario para enviar JSON
        headers = {'Content-Type': 'application/json'}

        # Peticion POST (Tu modificacion)
        response = requests.post(UPDATE_CAPACITY_URL, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            print("[API] Niveles actualizados correctamente.")
            return True
        else:
            print(f"[API] Error al actualizar niveles: {response.status_code}")
            print(f"      Respuesta: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[API] Error de conexion (Update Capacity): {e}")
        return False
