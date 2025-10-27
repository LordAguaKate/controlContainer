import serial
import requests
import time

# URL del endpoint de validación de usuario
API_URL = "COLOCA LA URL DE TU API"

def validate_user_qr(qr_serial_port):
    """
    Lee un token QR desde un puerto serie, lo valida contra la API
    y devuelve el ID del usuario si es válido.
    """
    if qr_serial_port.in_waiting > 0:
        try:
            # 1. Leer *todo* lo que haya en el buffer
            raw_data = qr_serial_port.read(qr_serial_port.in_waiting).decode('utf-8')
            
            ''' 2. Limpiar, dividir por cualquier salto de linea (\r o \n)
                y quedarse solo con el *ultimo* token no vacio. '''
            tokens = raw_data.strip().split() # split() maneja \r, \n, etc.
            if not tokens:
                return None
            
            token = tokens[-1] # Coger el ultimo token valido

            if not token:
                return None
            
            print(f"Token QR recibido: '{token}'")

            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(API_URL, headers=headers, timeout=20)

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
