import serial
import time
from src import photos, api_client, qr_handler

# --- CONFIGURACIÓN DE PUERTOS SERIE ---
# ¡IMPORTANTE! Debes verificar estos puertos en tu Raspberry Pi con el comando 'ls /dev/tty* suele ser /dev/ttyACM0 o /dev/ttyUSB0.'
ARDUINO_PORT = '/dev/tty*'
QR_SCANNER_PORT = '/dev/tty*' # Este es un ejemplo, podría ser ttyUSB1, etc.
BAUD_RATE = 9600

def process_api_response(response_data):
    """Procesa la respuesta de la API para determinar la acción."""
    if response_data and response_data.get('data'):
        scan_data = response_data['data']
        is_recyclable = scan_data.get('reciclable')

        if is_recyclable is True:
            tipo_material = scan_data.get('tipo_espanol', 'Desconocido')
            print(f"Resultado: MATERIAL RECICLABLE ({tipo_material}).")
        else:
            print("Resultado: MATERIAL NO VALIDO O NO RECICLABLE.")
    else:
        print("No se recibió una respuesta de escaneo válida del servidor.")


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
        print(f"Conectado a Arduino en {ARDUINO_PORT}")
        print(f"Conectado a Lector QR en {QR_SCANNER_PORT}")
        time.sleep(2)

        # Bucle principal del programa
        while True:
            print("\n--- Esperando escaneo de codigo QR... ---")
            
            # --- FASE 1: VALIDACIÓN DE USUARIO ---
            validated_user_id = None
            while validated_user_id is None:
                validated_user_id = qr_handler.validate_user_qr(qr_ser)
                if validated_user_id is None:
                    # Si no hay usuario, revisamos si hay mensajes del Arduino (ej. "Objeto retirado")
                    if arduino_ser.in_waiting > 0:
                        line = arduino_ser.readline().decode('utf-8').strip()
                        if line: print(f"Info de Arduino: '{line}'")
                    time.sleep(0.5) # Pequeña pausa para no saturar la CPU
            
            print("\n--- Usuario valido, coloque el material en el contenedor. ---")
            
            # --- FASE 2: DETECCIÓN DE OBJETO Y FOTO ---
            foto_tomada = False
            while not foto_tomada:
                if arduino_ser.in_waiting > 0:
                    line = arduino_ser.readline().decode('utf-8').strip()
                    if line == "FOTO":
                        print("!Comando de foto automatico recibido!")
                        filepath = photos.take_photo(camera)
                        
                        if filepath:
                            api_response = api_client.send_image_to_server(filepath, validated_user_id)
                            if api_response:
                                print(f"Respuesta de la API: {api_response}")
                                process_api_response(api_response)
                            else:
                                print("El envio de la imagen a la API fallo.")
                        
                        foto_tomada = True # Salimos de este bucle para esperar al siguiente QR
                    elif line:
                        print(f"Info de Arduino: '{line}'")
                
                time.sleep(0.1)

    except serial.SerialException as e:
        print(f"CRITICO: Error al conectar con un puerto serie: {e}")
        print("Verifica que ambos dispositivos esten conectados y los puertos sean correctos.")
    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario.")
    finally:
        # Cerrar todas las conexiones al salir
        if 'arduino_ser' in locals() and arduino_ser.is_open: arduino_ser.close()
        if 'qr_ser' in locals() and qr_ser.is_open: qr_ser.close()
        if camera: camera.close()
        print("Conexiones y camara cerradas correctamente.")

if __name__ == "__main__":
    main()
