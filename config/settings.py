# config/settings.py
import os
from dotenv import load_dotenv

# Carga las variables del archivo .env al entorno de Python
load_dotenv()

# --- HARDWARE SETTINGS ---
ARDUINO_SENSORES_PORT = os.getenv("ARDUINO_SENSORES_PORT", "/dev/ttyUSB0")
ARDUINO_MOTORES_PORT = os.getenv("ARDUINO_MOTORES_PORT", "/dev/ttyUSB1")
QR_SCANNER_PORT = os.getenv("ARDUINO_MOTORES_PORT", "/dev/ttyACM0")
BAUD_RATE = int(os.getenv("BAUD_RATE", 9600))

# --- API & DB SETTINGS ---
API_AUTH_URL = os.getenv("API_AUTH_URL", "")
API_DB_URL = os.getenv("API_DB_URL", "")
CONTAINER_ID = int(os.getenv("CONTAINER_ID", 1))

# --- PATHS SETTINGS ---
# Definimos rutas absolutas para evitar problemas al ejecutar el main desde otros lados
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")