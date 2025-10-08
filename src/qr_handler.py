import serial
import requests
import time
from src.config import API_VALIDATE_URL

def validate_user_qr(qr_serial_port):
    """
    Lee un token QR desde un puerto serie, lo valida contra la API
    y devuelve el ID del usuario si es válido.
    """
    if qr_serial_port.in_waiting > 0:
        try:
            token = qr_serial_port.readline().decode('utf-8').strip()
            if not token:
                return None
            
            print(f"Token QR recibido: '{token}'")

            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(API_VALIDATE_URL, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                user = data.get("data", {}).get("user", {})
                user_id = user.get("id")
                
                if user_id:
                    print(f"-> Usuario valido. ID: {user_id}")
                    return user_id
                else:
                    print("-> Error: La API no devolvió un ID de usuario.")
                    return None
            else:
                print(f"-> Error de validacion. Codigo: {response.status_code}, Respuesta: {response.text}")
                return None

        except serial.SerialException as e:
            print(f"-> Error de lectura del puerto serie QR: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"-> Error de conexion con la API de validacion: {e}")
            return None
        except Exception as e:
            print(f"-> Ocurrio un error inesperado al validar el QR: {e}")
            return None
    
    return None # No hay datos para leer
