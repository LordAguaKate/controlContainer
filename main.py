import serial
import time
from src import photos, api_client, qr_handler

# --- CONFIGURACIÓN DE PUERTOS SERIE ---
# ¡IMPORTANTE! Debes verificar estos puertos en tu Raspberry Pi con el comando 'ls /dev/tty* suele ser /dev/ttyACM0 o /dev/ttyUSB0.'
ARDUINO_PORT = '/dev/tty*'
QR_SCANNER_PORT = '/dev/tty*' # Este es un ejemplo, podría ser ttyUSB1, etc.
BAUD_RATE = 9600

def process_api_response(response_data):
    """Procesa la respuesta de la API, distinguiendo entre éxito y error 422."""
    if response_data and response_data.get('success') is True:
        scan_data = response_data.get('data', {})
        is_recyclable = scan_data.get('reciclable')
        tipo_material = scan_data.get('tipo_espanol', 'Desconocido')
        return is_recyclable, tipo_material
    # Si 'success' no es True, asumimos que no es reciclable.
    # Esto maneja el caso del 422 donde 'success' es false.
    return False, response_data.get('errors', "Error de procesamiento")

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
            
            # --- FASE 1: VALIDACIÓN DE USUARIO ---
            validated_user_id = None
            while validated_user_id is None:
                validated_user_id = qr_handler.validate_user_qr(qr_ser)
                time.sleep(0.2) # Pequeña pausa para no saturar la CPU
            
            print(f"\n--- FASE 2: Usuario valido (ID: {validated_user_id}). Coloque el material. ---")
            arduino_ser.write(b"START\n") # Comando para activar el Arduino

            # --- BUCLE DE SESIÓN DE RECICLAJE (INTERNO) ---
            session_active = True
            while session_active:
                if arduino_ser.in_waiting > 0:
                    arduino_msg = arduino_ser.readline().decode('utf-8').strip()

                    if arduino_msg == "FOTO":
                        print("\n--- FASE 3: Objeto detectado. Procesando... ---")
                        filepath = photos.take_photo(camera)
                        
                        if filepath:
                            print("Procesando, espere un poco...")
                            api_response = api_client.send_image_to_server(filepath, validated_user_id)
                            
                            reciclable, tipo = process_api_response(api_response)
                            if reciclable is True:
                                print(f"Resultado: MATERIAL RECICLABLE ({tipo}).")
                                print("[SIMULACION] Activando compuerta y cinta...")
                                print("--- FASE 4: Deposite el objeto y decida si continuar o terminar. ---")
                            else:
                                print(f"Resultado: MATERIAL NO VALIDO ({tipo}). Por favor, retirelo e intente con otro.")
                        else:
                            print("Error al tomar la fotografia. Por favor, retire el objeto.")

                    elif arduino_msg == "DECISION":
                        print("\n--- Para terminar presione el botón, para continuar deposite el siguiente objeto. ---")
                    
                    elif arduino_msg == "TERMINAR":
                        print("\n--- FASE 5: Proceso de reciclaje terminado. ---")
                        print("Actualizando tu historial...")
                        arduino_ser.write(b"PAUSE\n")
                        session_active = False
                    
                    elif "Info:" in arduino_msg:
                        print(arduino_msg) # Muestra mensajes de estado del Arduino

    except serial.SerialException as e: print(f"CRITICO: Error al conectar con un puerto serie: {e}")
    except KeyboardInterrupt: print("\nPrograma detenido.")
    finally:
        if 'arduino_ser' in locals() and arduino_ser.is_open:
            arduino_ser.write(b"PAUSE\n") # Asegurarse de pausar el Arduino al salir
            arduino_ser.close()
        if 'qr_ser' in locals() and qr_ser.is_open: qr_ser.close()
        if camera: camera.close()
        print("Conexiones y camara cerradas.")

if __name__ == "__main__":
    main()
