import serial
import time
import threading
from src import photos, api_client, qr_handler
from src.gui import ControlContainerGUI
from src.config import ARDUINO_PORT, QR_SCANNER_PORT, BAUD_RATE

# --- Utilidad: Procesar respuesta de API ---
def process_api_response(response_data):
    """Procesa la respuesta de la API, distinguiendo entre éxito y error 422."""
    if response_data and response_data.get('success') is True:
        scan_data = response_data.get('data', {})
        is_recyclable = scan_data.get('reciclable')
        tipo_material = scan_data.get('tipo_espanol', 'Desconocido')
        return is_recyclable, tipo_material
    # Si 'success' no es True, asumimos que no es reciclable.
    # Esto maneja el caso del 422 donde 'success' es false.
    return False, (response_data.get('errors') if isinstance(response_data, dict) else "Error de procesamiento")


class Controller:
    def __init__(self):
        self.gui = ControlContainerGUI()
        self.gui.on_start_session(self._on_start_session)
        self.gui.on_end_session(self._on_end_session)

        self.camera = photos.setup_camera()
        if not self.camera:
            print("CRITICO: No se pudo inicializar la camara. La interfaz seguirá abierta, pero no habrá capturas.")

        self.arduino_ser = None
        self.qr_ser = None
        self.current_user_id = None
        self.session_running = False
        self._threads = []

        self._init_serials()

        # Iniciar ciclo de espera de QR en un hilo
        t = threading.Thread(target=self._qr_wait_loop, name="QRWaitLoop", daemon=True)
        t.start()
        self._threads.append(t)

    def _init_serials(self):
        try:
            self.arduino_ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
            self.qr_ser = serial.Serial(QR_SCANNER_PORT, BAUD_RATE, timeout=1)
            print(f"Conectado a Arduino en {ARDUINO_PORT} y Lector QR en {QR_SCANNER_PORT}")
            time.sleep(2)
            if self.arduino_ser:
                self.arduino_ser.flushInput()
        except serial.SerialException as e:
            print(f"CRITICO: Error al conectar con un puerto serie: {e}")

    # --- Hilo: Espera y validación de QR ---
    def _qr_wait_loop(self):
        while True:
            if not self.qr_ser:
                time.sleep(1)
                continue

            try:
                user_id = qr_handler.validate_user_qr(self.qr_ser)
                if user_id:
                    self.current_user_id = user_id
                    print(f"Usuario válido (ID: {user_id}).")
                    self.gui.login_approved(user_id)
                    # El callback on_start_session activará la sesión y mostrará la pantalla
                    # Esperar a que termine la sesión antes de volver a esperar QR
                    while self.session_running:
                        time.sleep(0.2)
                    # Al finalizar, volvemos a la pantalla de login automáticamente desde el callback
                else:
                    # Continuar esperando
                    time.sleep(0.2)
            except Exception as e:
                print(f"Error en loop de QR: {e}")
                time.sleep(0.5)

    # --- Callback GUI: iniciar sesión ---
    def _on_start_session(self, user_id: int):
        self.gui.show_session()
        self.session_running = True
        # Activar Arduino para comenzar detección
        try:
            if self.arduino_ser and self.arduino_ser.is_open:
                self.arduino_ser.write(b"START\n")
        except Exception as e:
            print(f"Advertencia: no se pudo enviar START al Arduino: {e}")
        # Lanzar hilo de sesión
        t = threading.Thread(target=self._session_loop, name="SessionLoop", daemon=True)
        t.start()
        self._threads.append(t)

    # --- Bucle de sesión: leer Arduino y coordinar cámara/API ---
    def _session_loop(self):
        while self.session_running:
            try:
                if self.arduino_ser and self.arduino_ser.in_waiting > 0:
                    arduino_msg = self.arduino_ser.readline().decode('utf-8', errors='ignore').strip()

                    if arduino_msg == "FOTO":
                        print("Objeto detectado. Procesando...")
                        self.gui.session_detected()
                        filepath = photos.take_photo(self.camera)
                        if filepath:
                            self.gui.session_processing()
                            api_response = api_client.send_image_to_server(filepath, self.current_user_id)
                            reciclable, tipo = process_api_response(api_response)
                            self.gui.session_result(bool(reciclable), str(tipo))
                            if reciclable is True:
                                print("[SIMULACION] Activando compuerta y cinta...")
                                self.gui.session_info("Deposite el objeto y retirelo cuando sea indicado.")
                            else:
                                self.gui.session_info("Retire el objeto e intente con otro.")
                        else:
                            print("Error al tomar la fotografia.")
                            self.gui.session_info("Error al tomar la fotografía. Retire el objeto.", color_key='orange')

                    elif arduino_msg == "TERMINAR":
                        print("Fin de sesión solicitado por el usuario.")
                        try:
                            if self.arduino_ser and self.arduino_ser.is_open:
                                self.arduino_ser.write(b"PAUSE\n")
                        except Exception:
                            pass
                        # Disparar cierre de sesión en GUI (esto invocará on_end_session)
                        self.gui.session_end()
                        # Terminar bucle
                        self.session_running = False

                    elif arduino_msg == "LISTO_SIGUIENTE":
                        print("Usuario decidió continuar. Listo para siguiente objeto.")
                        self.gui.session_decision()
                        self.gui.session_waiting()

                    elif arduino_msg == "DECISION":
                        # Por compatibilidad si llegara este mensaje
                        self.gui.session_decision()

                    elif "Info:" in arduino_msg:
                        print(arduino_msg)
                        if "Esperando objeto" in arduino_msg:
                            self.gui.session_waiting()
                else:
                    time.sleep(0.05)
            except Exception as e:
                print(f"Error en loop de sesión: {e}")
                time.sleep(0.2)

    # --- Callback GUI: fin de sesión, mostrar resumen y volver a login ---
    def _on_end_session(self, points_added: int, total_points: int):
        self.gui.show_summary(points_added, total_points)
        # Pausa Arduino por seguridad
        try:
            if self.arduino_ser and self.arduino_ser.is_open:
                self.arduino_ser.write(b"PAUSE\n")
        except Exception:
            pass
        # Limpiar usuario actual y permitir que QR espere nuevamente
        self.current_user_id = None
        # Volver a login después de unos segundos
        def _back():
            self.gui.show_login()
        self.gui.after(2500, _back)

    # --- Cierre ordenado ---
    def close(self):
        try:
            self.session_running = False
            if self.arduino_ser and self.arduino_ser.is_open:
                self.arduino_ser.write(b"PAUSE\n")
                self.arduino_ser.close()
            if self.qr_ser and self.qr_ser.is_open:
                self.qr_ser.close()
            if self.camera:
                try:
                    self.camera.close()
                except Exception:
                    pass
        finally:
            print("Conexiones y camara cerradas.")


def main():
    print("Iniciando sistema de control del contenedor...")
    controller = Controller()
    try:
        controller.gui.mainloop()
    except KeyboardInterrupt:
        print("\nPrograma detenido.")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
