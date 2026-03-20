import serial
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ArduinoManager:
    """Clase para gestionar la conexión y comunicación serial con placas Arduino."""
    
    def __init__(self, port: str, baud_rate: int, name: str):
        self.port = port
        self.baud_rate = baud_rate
        self.name = name
        self.connection: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """Intenta establecer conexión con el Arduino."""
        try:
            self.connection = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2)  # Tiempo crucial para el reinicio del Arduino tras conectar
            self.connection.flushInput()
            logger.info(f"[OK] {self.name} conectado exitosamente en {self.port}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Fallo al conectar {self.name} en {self.port}: {e}")
            self.connection = None
            return False

    def send_command(self, command: str) -> None:
        """Envía un string al Arduino seguido de un salto de línea."""
        if self.connection and self.connection.is_open:
            try:
                self.connection.write(f"{command}\n".encode('utf-8'))
                logger.debug(f"Comando '{command}' enviado a {self.name}")
            except Exception as e:
                logger.error(f"Fallo al escribir en {self.name}: {e}")
        else:
            # Muy útil para pruebas cuando no tienes el hardware conectado
            logger.warning(f"[Simulación] {self.name} desconectado. Se omitió enviar: '{command}'")

    def read_line(self) -> Optional[str]:
        """Lee una línea del buffer del Arduino si hay datos disponibles."""
        if self.connection and self.connection.is_open and self.connection.in_waiting > 0:
            try:
                return self.connection.readline().decode('utf-8').strip()
            except UnicodeDecodeError:
                logger.warning(f"Error de decodificación leyendo de {self.name}")
                return None
        return None

    def in_waiting(self) -> int:
        """Devuelve la cantidad de bytes esperando en el buffer."""
        if self.connection and self.connection.is_open:
            return self.connection.in_waiting
        return 0

    def close(self) -> None:
        """Cierra el puerto serial de forma segura."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info(f"Conexión cerrada para {self.name}")