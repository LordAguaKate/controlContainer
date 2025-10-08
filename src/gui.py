import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from src.config import LED_COLORS, BLINK_INTERVAL_MS


class LEDIndicator(ttk.Frame):
    def __init__(self, master, diameter=24, initial_color='off'):
        super().__init__(master)
        self.diameter = diameter
        # En algunos entornos (p.ej. Tk/ttk en Raspberry Pi), ttk.Frame no expone 'background'.
        # Obtenemos el color de fondo desde el tema de ttk.Style con un fallback seguro.
        style = ttk.Style(self)
        try:
            bg = style.lookup('TFrame', 'background') or self.master.cget('background')
        except Exception:
            bg = '#f0f0f0'
        self.canvas = tk.Canvas(self, width=diameter, height=diameter, highlightthickness=0, bg=bg)
        self.canvas.pack()
        self.oval = self.canvas.create_oval(2, 2, diameter - 2, diameter - 2, fill=LED_COLORS.get(initial_color, '#222'))
        self._blink = False
        self._blink_colors = (LED_COLORS['white'], LED_COLORS['off'])
        self._blink_index = 0

    def set_color(self, color_key: str):
        self._blink = False
        color = LED_COLORS.get(color_key, '#222')
        self.canvas.itemconfig(self.oval, fill=color)

    def start_blink(self, color_on='white', color_off='off'):
        self._blink = True
        self._blink_colors = (LED_COLORS.get(color_on, '#FFF'), LED_COLORS.get(color_off, '#222'))
        self._blink_index = 0
        self._do_blink()

    def stop_blink(self):
        self._blink = False

    def _do_blink(self):
        if not self._blink:
            return
        color = self._blink_colors[self._blink_index % 2]
        self.canvas.itemconfig(self.oval, fill=color)
        self._blink_index += 1
        self.after(BLINK_INTERVAL_MS, self._do_blink)


class LoginFrame(ttk.Frame):
    def __init__(self, master, on_start_session: Callable[[int], None]):
        super().__init__(master)
        self.on_start_session = on_start_session

        self.title = ttk.Label(self, text="Control de Contenedor - Iniciar sesión", font=('Segoe UI', 16, 'bold'))
        self.title.pack(pady=(16, 8))

        self.subtitle = ttk.Label(self, text="Escanee su código QR para continuar", font=('Segoe UI', 12))
        self.subtitle.pack(pady=(0, 12))

        self.led = LEDIndicator(self, diameter=28, initial_color='off')
        self.led.pack(pady=8)

        self.status_var = tk.StringVar(value="Esperando QR...")
        self.status = ttk.Label(self, textvariable=self.status_var)
        self.status.pack(pady=(4, 12))

        self.user_var = tk.StringVar(value="")
        self.user_label = ttk.Label(self, textvariable=self.user_var, font=('Segoe UI', 10))
        self.user_label.pack(pady=(0, 8))

    # Thread-safe UI updates via after
    def set_waiting(self):
        self.after(0, lambda: (self.status_var.set("Esperando QR..."), self.led.start_blink('white', 'off')))

    def set_validating(self):
        self.after(0, lambda: (self.status_var.set("Validando..."), self.led.set_color('orange')))

    def set_denied(self):
        self.after(0, lambda: (self.status_var.set("Acceso denegado"), self.led.set_color('red')))

    def set_approved(self, user_id: int):
        def _approved():
            self.status_var.set("Acceso concedido")
            self.user_var.set(f"Usuario ID: {user_id}")
            self.led.set_color('green')
            # Dejar que el controlador cambie de pantalla
            self.on_start_session(user_id)
        self.after(0, _approved)


class SessionFrame(ttk.Frame):
    def __init__(self, master, on_end_session: Callable[[int, int], None]):
        super().__init__(master)
        self.on_end_session = on_end_session
        self.points_total = 0
        self.points_added_last = 0

        self.title = ttk.Label(self, text="Sesión de Reciclaje", font=('Segoe UI', 16, 'bold'))
        self.title.pack(pady=(16, 8))

        top = ttk.Frame(self)
        top.pack(pady=6)
        ttk.Label(top, text="Estado:").pack(side=tk.LEFT)
        self.state_var = tk.StringVar(value="Esperando objeto")
        ttk.Label(top, textvariable=self.state_var, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=6)

        self.led = LEDIndicator(self, diameter=28, initial_color='off')
        self.led.pack(pady=8)

        self.info_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.info_var, wraplength=420, justify='center').pack(pady=(6, 12))

        stats = ttk.Frame(self)
        stats.pack(pady=4)
        self.points_last_var = tk.StringVar(value="Puntos última acción: 0")
        self.points_total_var = tk.StringVar(value="Puntos totales: 0")
        ttk.Label(stats, textvariable=self.points_last_var).pack()
        ttk.Label(stats, textvariable=self.points_total_var).pack()

    def set_waiting_object(self):
        self.after(0, lambda: (self.state_var.set("Esperando objeto"), self.led.start_blink('white', 'off'), self.info_var.set("Coloque el material")))

    def set_object_detected(self):
        self.after(0, lambda: (self.state_var.set("Objeto detectado"), self.led.set_color('white_solid'), self.info_var.set("Procesando captura...")))

    def set_processing(self):
        self.after(0, lambda: (self.state_var.set("Analizando"), self.led.set_color('blue'), self.info_var.set("Enviando imagen a la API...")))

    def set_result(self, recyclable: bool, tipo: str):
        def _set():
            if recyclable:
                self.state_var.set("Aprobado")
                self.led.set_color('green')
                self.info_var.set(f"MATERIAL RECICLABLE ({tipo}). Deposite el objeto.")
                self.points_added_last = 10
                self.points_total += self.points_added_last
            else:
                self.state_var.set("Rechazado")
                self.led.set_color('red')
                self.info_var.set(f"MATERIAL NO VALIDO ({tipo}). Retire el objeto.")
                self.points_added_last = 0
            self.points_last_var.set(f"Puntos última acción: {self.points_added_last}")
            self.points_total_var.set(f"Puntos totales: {self.points_total}")
        self.after(0, _set)

    def set_info(self, text: str, color_key: Optional[str] = None):
        def _set():
            self.info_var.set(text)
            if color_key:
                self.led.set_color(color_key)
        self.after(0, _set)

    def set_decision_wait(self):
        self.after(0, lambda: (self.state_var.set("Decisión del usuario"), self.info_var.set("Presione el botón para terminar, o acerque otro objeto para continuar.")))

    def end_session(self):
        def _end():
            self.on_end_session(self.points_added_last, self.points_total)
        self.after(0, _end)


class SummaryFrame(ttk.Frame):
    def __init__(self, master, on_back_to_login: Callable[[], None]):
        super().__init__(master)
        self.on_back_to_login = on_back_to_login

        self.title = ttk.Label(self, text="Resumen de Sesión", font=('Segoe UI', 16, 'bold'))
        self.title.pack(pady=(16, 8))

        self.led = LEDIndicator(self, diameter=28, initial_color='green')
        self.led.pack(pady=8)

        self.summary_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.summary_var, font=('Segoe UI', 12)).pack(pady=(6, 12))

        self.btn = ttk.Button(self, text="Volver al inicio", command=self.on_back_to_login)
        self.btn.pack(pady=8)

    def set_summary(self, points_added: int, total_points: int):
        self.after(0, lambda: self.summary_var.set(f"Puntos sumados: {points_added}\nPuntos totales: {total_points}"))


class ControlContainerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control Container")
        self.geometry("520x420")
        self.resizable(False, False)
        try:
            self.call('tk', 'scaling', 1.2)
        except Exception:
            pass

        style = ttk.Style(self)
        if 'vista' in style.theme_names():
            style.theme_use('vista')
        else:
            style.theme_use('default')

        self._on_start_session_cb: Optional[Callable[[int], None]] = None
        self._on_end_session_cb: Optional[Callable[[int, int], None]] = None

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        self.frames = {}
        self.login_frame = LoginFrame(container, on_start_session=self._handle_start_session)
        self.session_frame = SessionFrame(container, on_end_session=self._handle_end_session)
        self.summary_frame = SummaryFrame(container, on_back_to_login=self.show_login)

        for f in (self.login_frame, self.session_frame, self.summary_frame):
            self.frames[f.__class__.__name__] = f
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_login()

    def on_start_session(self, cb: Callable[[int], None]):
        self._on_start_session_cb = cb

    def on_end_session(self, cb: Callable[[int, int], None]):
        self._on_end_session_cb = cb

    def _handle_start_session(self, user_id: int):
        if self._on_start_session_cb:
            self._on_start_session_cb(user_id)

    def _handle_end_session(self, points_added: int, total_points: int):
        if self._on_end_session_cb:
            self._on_end_session_cb(points_added, total_points)

    def show_login(self):
        self.login_frame.tkraise()
        self.login_frame.set_waiting()

    def show_session(self):
        self.session_frame.tkraise()
        self.session_frame.set_waiting_object()

    def show_summary(self, points_added: int, total_points: int):
        self.summary_frame.set_summary(points_added, total_points)
        self.summary_frame.tkraise()

    # Expose some convenience methods for controller
    def login_validating(self):
        self.login_frame.set_validating()

    def login_denied(self):
        self.login_frame.set_denied()

    def login_approved(self, user_id: int):
        self.login_frame.set_approved(user_id)

    def session_waiting(self):
        self.session_frame.set_waiting_object()

    def session_detected(self):
        self.session_frame.set_object_detected()

    def session_processing(self):
        self.session_frame.set_processing()

    def session_result(self, recyclable: bool, tipo: str):
        self.session_frame.set_result(recyclable, tipo)

    def session_info(self, text: str, color_key: Optional[str] = None):
        self.session_frame.set_info(text, color_key)

    def session_decision(self):
        self.session_frame.set_decision_wait()

    def session_end(self):
        self.session_frame.end_session()
