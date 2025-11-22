import serial
import json
import time

class ArduinoReader:
    def __init__(self, puerto='COM4', baudrate=9600):
        """
        Inicializa la conexión con Arduino
        puerto: 'COM3' en Windows, '/dev/ttyUSB0' o '/dev/ttyACM0' en Linux/Mac
        """
        try:
            self.arduino = serial.Serial(puerto, baudrate, timeout=1)
            time.sleep(2)  # Esperar a que Arduino se inicialice
            print(f"✓ Conectado a Arduino en {puerto}")
        except serial.SerialException as e:
            print(f"✗ Error al conectar: {e}")
            print("Puertos disponibles:")
            self.listar_puertos()
            raise
    
    def listar_puertos(self):
        """Lista los puertos seriales disponibles"""
        import serial.tools.list_ports
        puertos = serial.tools.list_ports.comports()
        for p in puertos:
            print(f"  - {p.device}: {p.description}")
    
    def leer_datos(self):
        """Lee una línea de datos del Arduino y la convierte a diccionario"""
        if self.arduino.in_waiting > 0:
            try:
                linea = self.arduino.readline().decode('utf-8').strip()
                if linea:
                    # Convertir el formato {sensor1: 10, ...} a JSON válido
                    linea_json = linea.replace('sensor1:', '"sensor1":')
                    linea_json = linea_json.replace('sensor2:', '"sensor2":')
                    linea_json = linea_json.replace('sensor3:', '"sensor3":') 
                    
                    datos = json.loads(linea_json)
                    return datos
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error al decodificar: {e}")
        return None
    
    def cerrar(self):
        """Cierra la conexión con Arduino"""
        self.arduino.close()
        print("✓ Conexión cerrada")


# Ejemplo de uso
if __name__ == "__main__":
    # Cambiar 'COM3' por tu puerto (usar 'COM5', '/dev/ttyUSB0', etc.)
    try:
        arduino = ArduinoReader(puerto='COM4', baudrate=9600)
        
        print("\nLeyendo datos (presiona Ctrl+C para detener)...\n")
        
        while True:
            datos = arduino.leer_datos()
            if datos:
                print(f"Sensor 1: {datos['sensor1']} cm")
                print(f"Sensor 2: {datos['sensor2']} cm")
                print(f"Sensor 3: {datos['sensor3']} cm") 
                print("-" * 40)
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\nDeteniendo lectura...")
    finally:
        arduino.cerrar()