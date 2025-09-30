import serial
import requests
import json
import time

ser = serial.Serial('COM4', 9600, timeout=1)
API_URL = "https://renova-3q4h.onrender.com/api/auth/validateToken"

print("Esperando QR...")

while True:
    if ser.in_waiting > 0:
        token = ser.readline().decode('utf-8').strip()
        print(f"Token recibido: '{token}'")

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.post(API_URL, headers=headers)

            if response.status_code == 200:
                data = response.json()

                user = data.get("data", {}).get("user", {})
                user_id = user.get("id", "N/A")
                user_name = user.get("name", "N/A")

                print(f"Usuario válido:")
                print(f"ID: {user_id} | Nombre: {user_name}")

            else:
                print(f"❌ Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"Error al conectar con API: {e}")

    time.sleep(0.5)
