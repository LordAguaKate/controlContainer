import serial
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class QRScanner:
    """Gestiona la lectura física del dispositivo escáner de códigos QR."""
    
    def __init__(self, port: str, baud_rate: int):
        self.port = port
        self.baud_rate = baud_rate
        self.connection: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """Conecta con el lector QR serial."""
        try:
            self.connection = serial.Serial(self.port, self.baud_rate, timeout=1)
            logger.info(f"[OK] Lector QR conectado en {self.port}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Fallo al conectar Lector QR: {e}")
            return False

    def flush(self) -> None:
        """Limpia el buffer para evitar lecturas antiguas."""
        if self.connection and self.connection.is_open:
            self.connection.flushInput()

    def read_token(self) -> Optional[str]:
        """Intenta leer un token del puerto serie. Devuelve el último token válido."""
        if self.connection and self.connection.is_open and self.connection.in_waiting > 0:
            try:
                # Leer todo el buffer y decodificar
                raw_data = self.connection.read(self.connection.in_waiting).decode('utf-8')
                tokens = raw_data.strip().split()
                
                if tokens:
                    return tokens[-1] # Tomamos siempre la lectura más reciente
            except Exception as e:
                logger.error(f"Error de lectura en escáner QR: {e}")
        return None

    def close(self) -> None:
        """Cierra el puerto del escáner."""
        if self.connection and self.connection.is_open:
            self.connection.close()