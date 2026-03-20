import serial
import requests
import time

# URL del endpoint de validación de usuario
API_URL = "COLOCA LA URL DE TU API"

def read_token(qr_serial_port):
    """
    Intenta leer un token del puerto serie.
    Devuelve el token (string) si encuentra uno, o None si no hay datos.
    """
    if qr_serial_port.in_waiting > 0:
        try:
            # 1. Leer *todo* lo que haya en el buffer
            raw_data = qr_serial_port.read(qr_serial_port.in_waiting).decode('utf-8')
            
            # 2. Limpiar, dividir y quedarse con el *ultimo* token no vacio.
            tokens = raw_data.strip().split()
            if not tokens:
                return None
            
            token = tokens[-1] # Coger el ultimo token valido
            return token

        except Exception as e:
            print(f"-> Error de lectura del puerto serie QR: {e}")
            return None
    
    return None # No hay datos para leer

def validate_token(token):
    """
    Toma un token (string), lo envia a la API y devuelve (user_id, user_name).
    En caso de error, devuelve (None, None).
    """
    try:
        print(f"Token QR recibido: '{token}'. Validando con API...")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(API_URL, headers=headers, timeout=20)

        if response.status_code == 200:
            data = response.json()
            user = data.get("data", {}).get("user", {})
            user_id = user.get("id")
            user_name = user.get("name")
            
            if user_id and user_name:
                return user_id, user_name
            else:
                print("-> Error: La API no devolvio un ID o nombre de usuario.")
                return None, None
        else:
            print(f"-> Error de validacion. Codigo: {response.status_code}, Respuesta: {response.text}")
            return None, None

    except requests.exceptions.RequestException as e:
        print(f"-> Error de conexion con la API de validacion: {e}")
        return None, None
    except Exception as e:
        print(f"-> Ocurrio un error inesperado al validar el token: {e}")
        return None, None