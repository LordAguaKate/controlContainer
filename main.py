import serial
import time
from src import photos, api_client

# --- Configuración del Puerto Serie ---
# Revisar el puerto correcto en la Raspberry Pi. Comúnmente es /dev/ttyACM0 o /dev/ttyUSB0
# Puedes encontrarlo con el comando 'ls /dev/tty*' en la terminal.
SERIAL_PORT = '/dev/tty*'
BAUD_RATE = 9600

def process_api_response(response_data):
    """
    Procesa la respuesta de la API para determinar la accion.
    CORREGIDO: Se hace la comparacion explicita 'is True' para mayor seguridad.
    """
    if response_data and response_data.get('success') and response_data.get('data'):
        scan_data = response_data['data']
        is_recyclable = scan_data.get('reciclable')

        # --- CORRECCION LOGICA ---
        # Comparamos explicitamente con 'True'. Esto evita problemas si el valor
        # fuera None o algo inesperado.
        if is_recyclable is True:
            tipo_material = scan_data.get('tipo_espanol', 'Desconocido')
            print(f"Resultado: MATERIAL RECICLABLE ({tipo_material}).")
        else:
            print("Resultado: MATERIAL NO VALIDO O NO RECICLABLE.")
    else:
        print("No se recibio una respuesta valida del servidor.")   


def main():
    """Funcion principal del programa."""
    print("Iniciando sistema de control del contenedor...")
    
    # Inicializar la camara una sola vez al inicio
    camera = photos.setup_camera()
    if not camera:
        print("No se pudo inicializar la camara. Abortando.")
        return

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Conectado al Arduino en {SERIAL_PORT}")
        time.sleep(2) # Dar tiempo a que se establezca la conexion
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    if line == "FOTO":
                        print("!Comando de foto recibido!")
                        filepath = photos.take_photo(camera)
                        
                        if filepath:
                            api_response = api_client.send_image_to_server(filepath)
                            if api_response:
                                print(f"Respuesta de la API: {api_response}")
                                process_api_response(api_response)
                            else:
                                print("El envio de la imagen a la API fallo.")
                    else:
                        print(f"Recibido de Arduino: '{line}'")

    except serial.SerialException as e:
        print(f"Error al conectar con el puerto serie: {e}")
        print("Asegurate de que el Arduino este conectado y que el puerto sea el correcto.")
    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
        if camera:
            camera.close()
            print("Camara y puerto serie cerrados correctamente.")

if __name__ == "__main__":
    main()
