# -*- coding: utf-8 -*-

import serial
import time
import unicodedata
from src import photos, api_client, qr_handler

# --- CONFIGURACION DE PUERTOS ---
# Verifica con 'ls /dev/tty*' cual es cual.
# Tip: Arduino Uno/Nano suele ser ttyUSBx, Arduino Leonardo/Micro o Scanner ttyACMx
ARDUINO_SENSORES_PORT = '/dev/ttyUSB*'  # Arduino Nano (Sensores/LCD)
ARDUINO_MOTORES_PORT  = '/dev/ttyUSB*'  # Arduino Nano (Motores/Banda) -> NUEVO
QR_SCANNER_PORT       = '/dev/ttyACM*'  # Lector QR
BAUD_RATE = 9600

# --- FUNCION PARA QUITAR ACENTOS ---
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

# --- PROCESAR RESPUESTA API ---
def process_api_response(response_data):
    if response_data is None:
        return False, "Error de IA"

    if response_data.get('success') is True:
        scan_data = response_data.get('data', {})
        is_recyclable = scan_data.get('reciclable')
        tipo_material = scan_data.get('tipo_espanol', 'Desconocido')
        return is_recyclable, tipo_material
    
    error_msg = response_data.get('errors', "Error de IA")
    if isinstance(error_msg, dict):
        error_msg_list = next(iter(error_msg.values()), ["Error de IA"])
        error_msg = error_msg_list[0] if error_msg_list else "Error de IA"
        
    return False, error_msg
    
def main():
    """Funcion principal que orquesta todo el flujo."""
    print("Iniciando sistema de control del contenedor...")
    
    camera = photos.setup_camera()
    if not camera:
        print("CRITICO: No se pudo inicializar la camara. Abortando.")
        return
        
    # Inicializamos las conexiones
    arduino_sensores = None
    arduino_motores = None
    qr_ser = None

    try:
        # 1. Conexion Arduino SENSORES (Pantalla, Boton, Sensor presencia)
        try:
            arduino_sensores = serial.Serial(ARDUINO_SENSORES_PORT, BAUD_RATE, timeout=1)
            time.sleep(2) # Reset de Arduino
            arduino_sensores.flushInput()
            print(f"[OK] Sensores conectados en {ARDUINO_SENSORES_PORT}")
        except Exception as e:
            print(f"[ERROR] Fallo al conectar Arduino Sensores: {e}")
            return # Es critico, salimos

        # 2. Conexion Arduino MOTORES (Banda, Servos)
        try:
            arduino_motores = serial.Serial(ARDUINO_MOTORES_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            print(f"[OK] Motores conectados en {ARDUINO_MOTORES_PORT}")
        except Exception as e:
            print(f"[WARNING] No se detecto Arduino de Motores ({e}). El sistema funcionara solo en modo visual.")

        # 3. Conexion Lector QR
        try:
            qr_ser = serial.Serial(QR_SCANNER_PORT, BAUD_RATE, timeout=1)
            print(f"[OK] Lector QR conectado en {QR_SCANNER_PORT}")
        except Exception as e:
             print(f"[ERROR] Fallo al conectar Lector QR: {e}")
             return

       # --- BUCLE PRINCIPAL ---
        while True:
            print("\n=======================================================")
            print("--- FASE 1: Esperando usuario (QR) ---")
            
            qr_ser.flushInput()
            validated_user_id = None
            
            # Esperar token QR
            token = None
            while token is None:
                token = qr_handler.read_token(qr_ser)
                time.sleep(0.2)
            
            print(f"Token leido. Validando...")
            arduino_sensores.write(b"VALIDANDO\n")
            
            user_id, user_name = qr_handler.validate_token(token)

            if user_id:
                print(f"-> Usuario valido: {user_name}")
                validated_user_id = user_id
                first_name_simple = strip_accents(user_name.split()[0])
                arduino_sensores.write(f"SESION_OK:{first_name_simple}\n".encode('utf-8'))
            else:
                print("-> Usuario invalido.")
                arduino_sensores.write(b"ERROR_SESION\n")
                time.sleep(0.5)
                continue 
                
            # --- FASE DE RECICLAJE ---
            session_active = True
            while session_active:
                if arduino_sensores.in_waiting > 0:
                    try:
                        arduino_msg = arduino_sensores.readline().decode('utf-8').strip()
                        if not arduino_msg: continue

                        if "Info:" in arduino_msg:
                            print(f"[Sensores] {arduino_msg}")
                        
                        elif arduino_msg == "FOTO":
                            print("\n--- FASE FOTO: Procesando objeto ---")
                            filepath = photos.take_photo(camera)
                        
                            if filepath:
                                api_response = api_client.send_image_to_server(filepath, validated_user_id)
                                reciclable, tipo = process_api_response(api_response)
                                tipo_simple = strip_accents(tipo)

                                if reciclable is True:
                                    print(f"-> APROBADO: {tipo_simple}")
                                    arduino_sensores.write(f"APROBADO:{tipo_simple}\n".encode('utf-8'))
                                    
                                    # --- LOGICA DE CLASIFICACION FISICA ---
                                    if arduino_motores and arduino_motores.is_open:
                                        print(f"[Motores] Enviando comando de clasificacion...")
                                        
                                        material_lower = tipo_simple.lower()
                                        
                                        if "aluminio" in material_lower or "lata" in material_lower:
                                            arduino_motores.write(b"ALUMINIO\n")
                                        elif "plastico" in material_lower or "botella" in material_lower:
                                            arduino_motores.write(b"PLASTICO\n")
                                        else:
                                            arduino_motores.write(b"OTRO\n")
                                    else:
                                        print("[Simulacion] Motor activado (Hardware no conectado)")

                                else:
                                    print(f"-> RECHAZADO: {tipo_simple}")
                                    arduino_sensores.write(b"RECHAZADO\n")
                                    
                                    # Material no valido 
                                    if arduino_motores and arduino_motores.is_open:
                                        arduino_motores.write(b"OTRO\n")

                            else:
                                print("Error camara.")
                                arduino_sensores.write(b"RECHAZADO\n")

                        elif arduino_msg == "TERMINAR":
                            print("\n--- Sesion finalizada ---")
                            session_active = False 

                    except UnicodeDecodeError:
                        pass

    except KeyboardInterrupt: print("\nPrograma detenido.")
    finally:
        if arduino_sensores and arduino_sensores.is_open: arduino_sensores.close()
        if arduino_motores and arduino_motores.is_open: arduino_motores.close()
        if qr_ser and qr_ser.is_open: qr_ser.close()
        if camera: camera.close()
        print("Limpieza completa.")

if __name__ == "__main__":
    main()