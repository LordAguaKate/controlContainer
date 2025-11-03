import serial
import time
import unicodedata
from src import photos, api_client, qr_handler

# --- CONFIGURACIÓN DE PUERTOS SERIE ---
# ¡IMPORTANTE! Debes verificar estos puertos en tu Raspberry Pi con el comando 'ls /dev/tty* suele ser /dev/ttyACM0 o /dev/ttyUSB0.'
ARDUINO_PORT = '/dev/tty*'
QR_SCANNER_PORT = '/dev/tty*' # Este es un ejemplo, podría ser ttyUSB1, etc.
BAUD_RATE = 9600

# ---  PARA QUITAR ACENTOS ---
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

def process_api_response(response_data):
    
    # Esto previene el crash.
    if response_data is None:
        return False, "Error de IA"

    # Si la respuesta Si existe, continuamos como antes.
    if response_data.get('success') is True:
        scan_data = response_data.get('data', {})
        is_recyclable = scan_data.get('reciclable')
        tipo_material = scan_data.get('tipo_espanol', 'Desconocido')
        return is_recyclable, tipo_material
    
    # Maneja error 422 (no exitoso) o cualquier otra respuesta no exitosa
    error_msg = response_data.get('errors', "Error de IA")
    if isinstance(error_msg, dict):
        error_msg_list = next(iter(error_msg.values()), ["Error de IA"])
        error_msg = error_msg_list[0] if error_msg_list else "Error de IA"
        
    return False, error_msg
    
def main():
    # --- INICIO DEL PROGRAMA ---
    print("Iniciando sistema de control del contenedor...")
    
    camera = photos.setup_camera()
    if not camera:
        print("CRITICO: No se pudo inicializar la camara. Abortando.")
        return

    try:
        # Inicializamos ambas conexiones serie
        arduino_ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        qr_ser = serial.Serial(QR_SCANNER_PORT, BAUD_RATE, timeout=1)
        print(f"Conectado a Arduino en {ARDUINO_PORT} y Lector QR en {QR_SCANNER_PORT}")
        time.sleep(2)
        arduino_ser.flushInput() # Limpiar cualquier mensaje antiguo del Arduino

       # --- BUCLE DE USUARIOS (EXTERNO) ---
        while True:
            print("\n=======================================================")
            print("--- FASE 1: Esperando escaneo de codigo QR de usuario ---")
            
            # --- FASE 1: VALIDACION DE USUARIO ---
            qr_ser.flushInput()
            validated_user_id = None
            
            # 1. Bucle para *leer* un token
            token = None
            while token is None:
                token = qr_handler.read_token(qr_ser)
                time.sleep(0.2) # Pausa para no saturar la CPU
            
            # 2. Token leido. Notificar al Arduino y validar con la API
            print(f"Token QR leido. Enviando a Arduino para validar...")
            arduino_ser.write(b"VALIDANDO\n")
            
            user_id, user_name = qr_handler.validate_token(token)

            # 3. Reaccionar al resultado de la validacion
            if user_id:
                print(f"-> Usuario valido. ID: {user_id}, Nombre: {user_name}")
                validated_user_id = user_id
                
                # Obtener solo el primer nombre y sin acentos
                first_name = user_name.split()[0]
                first_name_simple = strip_accents(first_name)
                
                # Enviar comando de exito al Arduino
                arduino_ser.write(f"SESION_OK:{first_name_simple}\n".encode('utf-8'))
                
                print(f"\n--- FASE 2: Usuario valido (ID: {validated_user_id}). Activando Arduino... ---")
                print("--- FASE 3: Arduino activado. Esperando objetos... ---")
                
            else:
                # --- FALLO ---
                print("-> Error de validacion. Reiniciando bucle de QR.")
                # Enviar comando de error al Arduino
                arduino_ser.write(b"ERROR_SESION\n")
                
                # Volver al inicio del bucle de FASE 1
                time.sleep(0.5) 
                continue 

            
            # --- BUCLE DE SESION DE RECICLAJE (INTERNO) ---
            session_active = True
            while session_active:
                if arduino_ser.in_waiting > 0:
                    try:
                        arduino_msg = arduino_ser.readline().decode('utf-8').strip()
                        if not arduino_msg:
                            continue

                        # Mostrar siempre los mensajes de info del Arduino
                        if "Info:" in arduino_msg:
                            print(f"[Arduino] {arduino_msg}")
                        
                        elif arduino_msg == "FOTO":
                            print("\n--- FASE 4: FOTO solicitada. Procesando... ---")
                            filepath = photos.take_photo(camera)
                        
                            if filepath:
                                print("Enviando a API, espere...")
                                api_response = api_client.send_image_to_server(filepath, validated_user_id)
                            
                                reciclable, tipo = process_api_response(api_response)
                            
                                if reciclable is True:
                                    print(f"Resultado: MATERIAL RECICLABLE ({tipo}).")
                                    
                                    tipo_simple = strip_accents(tipo)
                                    
                                    arduino_ser.write(f"APROBADO:{tipo_simple}\n".encode('utf-8'))
                                        
                                    print("[SIMULACION] Activando compuerta y cinta...")
                                    print("--- FASE 5: Deposite el siguiente objeto o presione el boton para terminar. ---")
                                
                                else:
                                    print(f"Resultado: MATERIAL NO VALIDO ({tipo}).")
                                    # Enviar comando RECHAZADO al Arduino
                                    arduino_ser.write(b"RECHAZADO\n")
                                    print("--- FASE 5: Espere a que se retire e intente con otro. ---")

                            
                            else:
                                print("Error al tomar la fotografia. Retirando...")
                                # Si la foto falla, tambien hay que decirle al Arduino
                                arduino_ser.write(b"RECHAZADO\n")

                        elif arduino_msg == "TERMINAR":
                            print("\n--- FASE 6: Sesion terminada por el usuario o por timeout. ---")
                            session_active = False 
                        
                        elif arduino_msg:
                            # Capturar otros mensajes inesperados
                            print(f"[Arduino-WARN] Mensaje no reconocido: {arduino_msg}")

                    except UnicodeDecodeError:
                        print("[Error] No se pudo decodificar el mensaje del Arduino.")


    except serial.SerialException as e: print(f"CRITICO: Error al conectar con un puerto serie: {e}")
    except KeyboardInterrupt: print("\nPrograma detenido.")
    finally:

        if 'arduino_ser' in locals() and arduino_ser.is_open:
            arduino_ser.close()
        if 'qr_ser' in locals() and qr_ser.is_open: qr_ser.close()
        if camera: camera.close()
        print("Conexiones y camara cerradas.")

if __name__ == "__main__":
    main()