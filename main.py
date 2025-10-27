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
    """Procesa la respuesta de la API, distinguiendo entre exito y error 422."""
    if response_data and response_data.get('success') is True:
        scan_data = response_data.get('data', {})
        is_recyclable = scan_data.get('reciclable')
        tipo_material = scan_data.get('tipo_espanol', 'Desconocido')
        return is_recyclable, tipo_material
    
    # Maneja error 422 (no exitoso) o cualquier otra respuesta no esperada
    error_msg = response_data.get('errors', "Error de IA")
    if isinstance(error_msg, dict):
        error_msg_list = next(iter(error_msg.values()), ["Error de IA"])
        error_msg = error_msg_list[0] if error_msg_list else "Error de IA"
        
    return False, error_msg

def main():
    """Función principal que orquesta todo el flujo."""
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
            validated_user_id = None
            while validated_user_id is None:
                validated_user_id = qr_handler.validate_user_qr(qr_ser)
                time.sleep(0.2) # Pausa para no saturar la CPU
            
            print(f"\n--- FASE 2: Usuario valido (ID: {validated_user_id}). Activando Arduino... ---")
            # --- CAMBIO ---
            # Enviamos "START" para que el Arduino salga del estado INACTIVO
            arduino_ser.write(b"START\n") 
            print("--- FASE 3: Arduino activado. Esperando objetos... ---")

            
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
                                    
                                    # --- SOLUCION DEFINITIVA ---
                                    # Usamos la nueva funcion 'strip_accents'
                                    tipo_simple = strip_accents(tipo)
                                    
                                    arduino_ser.write(f"APROBADO:{tipo_simple}\n".encode('utf-8'))
                                        
                                    print("[SIMULACION] Activando compuerta y cinta...")
                                    print("--- FASE 5: Deposite el siguiente objeto o presione el boton para terminar. ---")
                                
                                else:
                                    print(f"Resultado: MATERIAL NO VALIDO ({tipo}).")
                                    # Enviar comando RECHAZADO al Arduino
                                    arduino_ser.write(b"RECHAZADO\n")
                                    print("--- FASE 5: Espere a que se retire e intente con otro. ---")
                                    # --- FIN DE NUEVA LOGICA ---
                            
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
        # --- CAMBIO ---
        # Ya no es necesario enviar "PAUSE" al cerrar.
        if 'arduino_ser' in locals() and arduino_ser.is_open:
            arduino_ser.close()
        if 'qr_ser' in locals() and qr_ser.is_open: qr_ser.close()
        if camera: camera.close()
        print("Conexiones y camara cerradas.")

if __name__ == "__main__":
    main()