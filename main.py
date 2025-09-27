import serial
import time
from src.photos import setup_camera, take_photo

# --- Configuración del Puerto Serie ---
# Revisar el puerto correcto en la Raspberry Pi. Comúnmente es /dev/ttyACM0 o /dev/ttyUSB0
# Puedes encontrarlo con el comando 'ls /dev/tty*' en la terminal.
SERIAL_PORT = '/dev/tty*'
BAUD_RATE = 9600

def main():
    """
    Función principal que escucha los comandos del Arduino y controla la cámara.
    """
    print("Iniciando el sistema de captura de imágenes...")
    
    # Inicializar la cámara
    picam2 = setup_camera()
    if not picam2:
        print("No se pudo iniciar la cámara. El programa terminará.")
        return

    # Intentar conectar con el Arduino
    ser = None
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        # Esperar a que la conexión serie se establezca
        time.sleep(2) 
        print(f"Conectado al Arduino en {SERIAL_PORT}")
    except serial.SerialException:
        print(f"Error: No se pudo abrir el puerto serie {SERIAL_PORT}.")
        print("Asegúrate de que el Arduino esté conectado y el puerto sea correcto.")
        picam2.stop()
        return

    try:
        while True:
            # Revisar si hay datos llegando desde el Arduino
            if ser.in_waiting > 0:
                # Leer la línea, decodificarla y quitar espacios en blanco/saltos de línea
                line = ser.readline().decode('utf-8').rstrip()
                
                print(f"Recibido de Arduino: '{line}'") # Para depuración

                # Si el comando es "FOTO", llamamos a la función para tomar la foto
                if line == "FOTO":
                    print("¡Comando de foto recibido! Tomando fotografía...")
                    take_photo(picam2)
            
            # Pequeña pausa para no saturar el CPU
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario. Cerrando...")
    finally:
        # Asegurarse de cerrar los recursos correctamente
        if ser and ser.is_open:
            ser.close()
            print("Puerto serie cerrado.")
        if picam2:
            picam2.stop()
            print("Cámara detenida.")

if __name__ == '__main__':
    main()
