# Configuración central del sistema
# Ajusta estos valores en la Raspberry Pi según tus puertos reales

# Puertos Serial (ejemplos, reemplazar en producción)
ARDUINO_PORT = '/dev/ttyACM0'
QR_SCANNER_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

# Identificadores
CONTAINER_ID = 1  # Cambiar según tu configuración en el backend

# URLs de API (reemplazar por las reales)
API_SCAN_URL = "COLOCA LA URL DE TU API"  # e.g., https://tu-dominio.com/api/scans
API_VALIDATE_URL = "COLOCA LA URL DE TU API"  # e.g., https://tu-dominio.com/api/validate-user

# Colores de indicadores tipo LED (Tkinter)
LED_COLORS = {
    'off': '#222222',       # apagado
    'white': '#FFFFFF',     # esperando objeto (parpadeo)
    'white_solid': '#DDDDDD',  # objeto detectado (estático)
    'green': '#00C853',     # aprobado
    'red': '#D50000',       # acceso denegado
    'orange': '#FF6D00',    # problemas/advertencias
    'blue': '#2962FF',      # opcional: procesando
}

# Timings GUI
BLINK_INTERVAL_MS = 500
