from picamera2 import Picamera2
import time

picam = Picamera2()

config = picam.create_preview_configuration()
picam.configure(config)


picam.start()

print("Cámara iniciada. Ajustando exposición...")

time.sleep(2)

output_file = "prueba_v2.jpg"
picam.capture_file(output_file)

print(f"¡Foto capturada con éxito! Guardada como: {output_file}")

picam.stop()