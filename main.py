# -*- coding: utf-8 -*-

import time
import logging
import unicodedata
import sys

# Importamos nuestras configuraciones globales
from config import settings

# Importamos nuestras capas modulares
from src.hardware.camera import setup_camera, take_photo
from src.hardware.arduino import ArduinoManager
from src.hardware.qr_scanner import QRScanner
from src.services.auth_service import validate_token
from src.ml.classifier import WasteClassifier

# ============================================================================
# CONFIGURACIÓN DEL LOGGING GLOBAL
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("contenedor_inteligente.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Main")

def strip_accents(s: str) -> str:
    """Elimina los acentos de un string para que el Arduino LCD lo lea sin basura."""
    if not s:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

def main():
    logger.info("=== INICIANDO SISTEMA DEL CONTENEDOR INTELIGENTE ===")
    
    # 1. Inicialización de Hardware e IA
    camera = setup_camera()
    if not camera:
        logger.critical("Abortando inicio: Sin cámara el sistema no puede operar.")
        return

    ia_classifier = WasteClassifier() # Aquí se carga el modelo .tflite o .keras

    sensores = ArduinoManager(settings.ARDUINO_SENSORES_PORT, settings.BAUD_RATE, "Arduino Sensores")
    motores = ArduinoManager(settings.ARDUINO_MOTORES_PORT, settings.BAUD_RATE, "Arduino Motores")
    escaner_qr = QRScanner(settings.QR_SCANNER_PORT, settings.BAUD_RATE)

    # Intentamos conectar
    if not sensores.connect():
        logger.critical("Abortando: El Arduino de Sensores/Pantalla es crítico y no conectó.")
        return
        
    motores.connect() # Si falla, ArduinoManager ya maneja el modo simulación
    escaner_qr.connect()

    try:
        # ============================================================================
        # BUCLE PRINCIPAL DEL SISTEMA MÁQUINA DE ESTADOS
        # ============================================================================
        while True:
            logger.info("--- FASE 1: ESPERANDO USUARIO (QR) ---")
            escaner_qr.flush()
            token = None
            
            # Esperar lectura de QR
            while not token:
                token = escaner_qr.read_token()
                time.sleep(0.2)
            
            logger.info("Token detectado. Validando...")
            sensores.send_command("VALIDANDO")
            
            user_id, user_name = validate_token(token)

            if not user_id:
                logger.warning("Usuario inválido o no reconocido.")
                sensores.send_command("ERROR_SESION")
                time.sleep(1)
                continue # Regresa a esperar otro QR
                
            first_name_simple = strip_accents(user_name.split()[0])
            sensores.send_command(f"SESION_OK:{first_name_simple}")
            
            # --- FASE 2: SESIÓN DE RECICLAJE ACTIVA ---
            logger.info(f"--- FASE 2: SESIÓN ACTIVA PARA {user_name} ---")
            session_active = True
            
            while session_active:
                arduino_msg = sensores.read_line()
                if not arduino_msg:
                    time.sleep(0.1)
                    continue

                if "Info:" in arduino_msg:
                    logger.info(f"[Sensores] {arduino_msg}")
                
                # --- EVENTO: EL USUARIO INGRESÓ UN OBJETO ---
                elif arduino_msg == "FOTO":
                    logger.info("Objeto detectado. Capturando y procesando...")
                    filepath = take_photo(camera)
                
                    if filepath:
                        # INFERENCIA LOCAL DE IA
                        predicted_class, confidence = ia_classifier.predict(filepath)
                        logger.info(f"IA Predice: {predicted_class} (Confianza: {confidence:.2f})")
                        
                        is_recyclable = ia_classifier.is_recyclable(predicted_class, confidence)
                        clase_limpia = strip_accents(predicted_class).upper()

                        if is_recyclable:
                            logger.info(f"-> APROBADO: {clase_limpia}")
                            sensores.send_command(f"APROBADO:{clase_limpia}")
                            
                            # Lógica de motores basada en la predicción
                            if "ALUMINIO" in clase_limpia:
                                motores.send_command("ALUMINIO")
                            elif "PLASTICO" in clase_limpia:
                                motores.send_command("PLASTICO")
                            else:
                                motores.send_command("OTRO") # Es reciclable pero va a otra caja
                        else:
                            logger.warning(f"-> RECHAZADO: {clase_limpia}")
                            sensores.send_command("RECHAZADO")
                            motores.send_command("OTRO") # Banda de descarte
                    else:
                        logger.error("Fallo al capturar foto.")
                        sensores.send_command("RECHAZADO")

                # --- EVENTO: EL USUARIO O EL TIMEOUT FINALIZÓ LA SESIÓN ---
                elif arduino_msg == "TERMINAR":
                    logger.info("El Arduino de sensores ha terminado la sesión.")
                    session_active = False 

    except KeyboardInterrupt:
        logger.info("Programa detenido manualmente por el operador (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Error inesperado en el bucle principal: {e}", exc_info=True)
    finally:
        # Limpieza rigurosa de recursos
        logger.info("Limpiando recursos y cerrando puertos...")
        sensores.close()
        motores.close()
        escaner_qr.close()
        if camera:
            camera.close()
        logger.info("=== SISTEMA APAGADO CORRECTAMENTE ===")

if __name__ == "__main__":
    main()