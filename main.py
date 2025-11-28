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
    
# --- FUNCION PARA PROCESAR NIVELES ---
def procesar_niveles(linea_datos):
    """
    1. Recibe string 'NIVELES:15,-1,12'
    2. Aplica la simulacion del sensor danado.
    3. Envia los datos a la API.
    """
    try:
        datos = linea_datos.replace("NIVELES:", "").strip().split(",")
        if len(datos) == 3:
            alu_str, bas_str, pla_str = datos
            
            final_alu = 0
            final_pla = 0
            final_bas = 0

            print(f"\n[ESTADO CONTENEDORES - FINAL DE SESION]")

            try:
                # 1. Convertir Aluminio y Plastico (Sensores Buenos)
                final_alu = int(alu_str)
                final_pla = int(pla_str)
                final_bas = int(bas_str)
                # 2. Calcular Basura (Sensor Danado -> Simulado)
                # TODO: Cuando arregles el sensor, descomenta la linea real y comenta la simulada:
                # final_bas = int(bas_str)  # <-- LINEA REAL
                # final_bas = (final_alu + final_pla) // 2  # <-- LINEA SIMULADA

                # 3. Mostrar en consola
                print(f"   - Aluminio:      {final_alu} cm")
                print(f"   - Plastico:      {final_pla} cm")
                print(f"   - No Reciclable: {final_bas} cm")

                # 4. ENVIAR A LA API (Solo al finalizar sesion)
                api_client.update_container_capacity(final_alu, final_pla, final_bas)

            except ValueError:
                print("[Error] Valores no numericos recibidos de sensores.")
            
        else:
            print(f"[ADVERTENCIA] Formato incorrecto: {linea_datos}")
    except Exception as e:
        print(f"[ERROR] Al procesar niveles: {e}")

              
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
            token = None
            
            while token is None:
                

                # --- B. LEER RESPUESTAS DEL ARDUINO (NIVELES) ---
                if arduino_sensores and arduino_sensores.in_waiting > 0:
                    try:
                        linea = arduino_sensores.readline().decode('utf-8').strip()
                        if linea.startswith("NIVELES:"): 
                            procesar_niveles(linea) # <--- AQUI SE PROCESA Y ENVIA A LA API
                        elif "Info:" in linea: 
                            print(f"[Log] {linea}")
                    except: pass
                        
                # C. LEER QR
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
                # (ELIMINADO CHECK PERIODICO DE ULTRASONICOS)

                # B. LEER ARDUINO
                if arduino_sensores.in_waiting > 0:
                    try:
                        msg = arduino_sensores.readline().decode('utf-8').strip()
                        if not msg: continue

                        if "Info:" in msg: print(f"[Sens] {msg}")
                        elif msg.startswith("NIVELES:"): 
                            procesar_niveles(msg)
                        
                        elif msg == "FOTO":
                            print("\n--- FOTO ---")
                            path = photos.take_photo(camera)
                            if path:
                                res = api_client.send_image_to_server(path, validated_user_id)
                                ok, tipo = process_api_response(res)
                                tipo_simple = strip_accents(tipo)

                                if ok:
                                    print(f"-> APROBADO: {tipo_simple}")
                                    arduino_sensores.write(f"APROBADO:{tipo_simple}\n".encode())
                                    if arduino_motores:
                                        m = tipo_simple.lower()
                                        if "aluminio" in m or "lata" in m: arduino_motores.write(b"ALUMINIO\n")
                                        elif "plastico" in m or "botella" in m: arduino_motores.write(b"PLASTICO\n")
                                        else: arduino_motores.write(b"OTRO\n")
                                else:
                                    print(f"-> RECHAZADO: {tipo_simple}")
                                    arduino_sensores.write(b"RECHAZADO\n")
                                    if arduino_motores: arduino_motores.write(b"OTRO\n")
                            else:
                                arduino_sensores.write(b"RECHAZADO\n")

                        elif msg == "TERMINAR":
                            print("\n--- Fin Sesion Detectado ---")
                            print("Solicitando niveles finales a Arduino...")
                            # 1. PEDIMOS LOS NIVELES AHORA
                            arduino_sensores.write(b"LEER_ULTRASONICOS\n")
                            # 2. CERRAMOS EL BUCLE
                            # La respuesta "NIVELES:..." llegara en unos milisegundos
                            # y sera capturada por el Bucle de la FASE 1.
                            session_active = False 

                    except: pass

    except KeyboardInterrupt: print("\nPrograma detenido.")
    finally:
        if arduino_sensores and arduino_sensores.is_open: arduino_sensores.close()
        if arduino_motores and arduino_motores.is_open: arduino_motores.close()
        if qr_ser and qr_ser.is_open: qr_ser.close()
        if camera: camera.close()
        print("Limpieza completa.")

if __name__ == "__main__":
    main()