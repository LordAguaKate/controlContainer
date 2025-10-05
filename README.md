# controlContainer

Sistema inteligente de reciclaje automatizado con reconocimiento de materiales mediante visión artificial y validación de usuarios por código QR.

## 📋 Descripción

**controlContainer** es un sistema IoT completo que combina hardware (Arduino Nano, Raspberry Pi, sensores) y software (Python, API REST) para crear un contenedor de reciclaje inteligente. El sistema valida usuarios mediante códigos QR, detecta objetos con sensores de proximidad, captura imágenes con una cámara, y utiliza inteligencia artificial para clasificar materiales reciclables en tiempo real.

### Características principales

- ✅ **Validación de usuarios** mediante códigos QR escaneados
- 🔍 **Detección automática** de objetos con sensor infrarrojo E18-D80NK
- 📸 **Captura de imágenes** con Raspberry Pi Camera Module (autoenfoque)
- 🤖 **Clasificación inteligente** de materiales mediante API con IA
- 🔄 **Sesiones de reciclaje** con múltiples objetos por usuario
- 📊 **Registro de historial** de reciclaje por usuario
- 🚦 **Máquina de estados** robusta en Arduino para control de flujo

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐
│  Lector QR      │──┐
└─────────────────┘  │
                     │
┌─────────────────┐  │    ┌──────────────────┐
│ Sensor IR       │──┼───→│  Raspberry Pi 4  │
│ (Arduino Nano)  │  │    │  (Python)        │
└─────────────────┘  │    └──────────────────┘
                     │            │
┌─────────────────┐  │            │
│ Pi Camera       │──┘            │
└─────────────────┘               │
                                  ↓
                         ┌─────────────────┐
                         │   API Laravel   │
                         │   (Backend)     │
                         └─────────────────┘
```

## 🔧 Componentes de Hardware

### Requeridos
- **Raspberry Pi 4** (o superior) con Raspberry Pi OS
- **Arduino Nano** (o compatible)
- **Raspberry Pi Camera Module** (con soporte de autoenfoque)
- **Sensor infrarrojo E18-D80NK** (detección de proximidad)
- **Lector de código QR** con salida serial (USB/UART)
- **Botón pulsador** (para finalizar sesión)
- **LED** (indicador de estado, opcional)
- Cables de conexión y fuente de alimentación

### Conexiones Arduino Nano

```cpp
Pin 4  → Sensor infrarrojo E18-D80NK (señal)
Pin 3  → Botón pulsador (con pull-down)
Pin 13 → LED indicador (integrado)
```

## 💻 Estructura del Proyecto

```
controlContainer/
│
├── main.py                          # Programa principal (orquestador)
├── README.md                        # Este archivo
│
├── src/
│   ├── api_client.py               # Cliente para enviar imágenes a la API
│   ├── qr_handler.py               # Validación de usuarios por QR
│   ├── photos.py                   # Captura de fotos con Pi Camera
│   └── config.py                   # Configuración (ID contenedor, etc.)
│
├── ArduinoNano/
│   └── SensorProximidad.ino        # Código para Arduino Nano
│
└── images/                          # Carpeta de imágenes capturadas
```

## 🚀 Instalación y Configuración

### 1. Configuración de Raspberry Pi

#### Instalar dependencias del sistema

```bash
sudo apt update
sudo apt install -y python3-pip python3-picamera2 python3-serial
```

#### Instalar dependencias de Python

```bash
pip3 install requests pyserial picamera2
```

#### Habilitar la cámara

```bash
sudo raspi-config
# Navegar a: Interface Options → Camera → Enable
```

### 2. Configuración de Arduino Nano

1. Abrir `ArduinoNano/SensorProximidad.ino` en el Arduino IDE
2. Conectar el Arduino Nano por USB
3. Seleccionar la placa: **Tools → Board → Arduino Nano**
4. Seleccionar el puerto correcto: **Tools → Port → /dev/ttyUSB0** (o el correspondiente)
5. Cargar el sketch: **Sketch → Upload**

### 3. Configuración del Proyecto

#### Identificar puertos serie

En la Raspberry Pi, ejecutar:

```bash
ls /dev/tty*
```

Identificar los puertos del Arduino y del lector QR (generalmente `/dev/ttyACM0`, `/dev/ttyUSB0`, etc.)

#### Editar configuración en `main.py`

```python
ARDUINO_PORT = '/dev/ttyACM0'      # Puerto del Arduino Nano
QR_SCANNER_PORT = '/dev/ttyUSB0'   # Puerto del lector QR
BAUD_RATE = 9600
```

#### Configurar archivo `src/config.py`

Crear el archivo `src/config.py` (si no existe):

```python
# ID único del contenedor (debe estar registrado en la API)
CONTAINER_ID = 1  # Cambiar según tu configuración
```

#### Configurar URLs de API

**En `src/api_client.py`:**

```python
API_URL = "https://tu-dominio.com/api/scans"  # Endpoint para enviar imágenes
```

**En `src/qr_handler.py`:**

```python
API_URL = "https://tu-dominio.com/api/validate-user"  # Endpoint de validación
```

## 🎮 Uso del Sistema

### Iniciar el sistema

```bash
cd /ruta/a/controlContainer
python3 main.py
```

### Flujo de operación

1. **FASE 1: Validación de usuario**
   - El sistema espera que un usuario escanee su código QR
   - El token se valida contra la API
   - Si es válido, se activa el Arduino y comienza la sesión

2. **FASE 2: Colocación de material**
   - El usuario coloca un objeto frente al sensor infrarrojo
   - El sensor detecta el objeto durante 2 segundos continuos

3. **FASE 3: Captura y análisis**
   - La Raspberry Pi captura una foto del objeto
   - La imagen se envía a la API junto con el ID del usuario y contenedor
   - La API responde con la clasificación del material (reciclable/no reciclable)

4. **FASE 4: Decisión del usuario**
   - Si el material es reciclable, la cinta (aun no implementada) se activa y deposita el objeto
   - Después de retirar el objeto, en un lapso de 3 segundos el usuario puede decidir:
     - **Presionar el botón** → Finalizar sesión
     - **Colocar otro objeto** → Continuar reciclando

5. **FASE 5: Finalización**
   - Al presionar el botón, se cierra la sesión del usuario
   - El sistema vuelve a la FASE 1 para el siguiente usuario

## 📡 Comunicación Serial

### Comandos Raspberry Pi → Arduino

| Comando | Descripción |
|---------|-------------|
| `START\n` | Activa el Arduino para comenzar a detectar objetos |
| `PAUSE\n` | Pausa el Arduino (al finalizar sesión o cerrar programa) |

### Mensajes Arduino → Raspberry Pi

| Mensaje | Descripción |
|---------|-------------|
| `FOTO` | Objeto detectado durante 2 segundos, solicita captura de foto |
| `TERMINAR` | Usuario presionó el botón para finalizar sesión |
| `LISTO_SIGUIENTE` | Usuario no presionó el botón, listo para siguiente objeto |
| `Info: ...` | Mensajes de estado del Arduino (informativos) |

## 🔌 API REST

### Endpoint: Validación de Usuario

**POST** `/api/validate-user`

**Headers:**
```
Authorization: Bearer {token_qr}
```

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "name": "Juan Pérez",
      "email": "juan@example.com"
    }
  }
}
```

### Endpoint: Envío de Imagen

**POST** `/api/scans`

**Parámetros (multipart/form-data):**
- `image`: Archivo de imagen (JPEG)
- `container_id`: ID del contenedor (integer)
- `user_id`: ID del usuario validado (integer)

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "data": {
    "reciclable": true,
    "tipo_espanol": "Plástico",
    "confianza": "95%"
  }
}
```

**Respuesta de error (422):**
```json
{
  "success": false,
  "errors": "Material no reconocido"
}
```

## 🛠️ Solución de Problemas

### Error: "No se pudo inicializar la cámara"

- Verificar que la cámara esté habilitada en `raspi-config`
- Comprobar la conexión física del cable de la cámara
- Reiniciar la Raspberry Pi

### Error: "Error al conectar con un puerto serie"

- Verificar los puertos con `ls /dev/tty*`
- Comprobar permisos: `sudo usermod -a -G dialout $USER` (luego reiniciar sesión)
- Verificar que los dispositivos estén conectados

### El sensor no detecta objetos

- Verificar la conexión del sensor al Arduino (pin 4)
- Comprobar la alimentación del sensor (5V)
- Ajustar la distancia de detección del sensor (potenciómetro)

### La API no responde

- Verificar la URL configurada en `api_client.py` y `qr_handler.py`
- Comprobar la conexión a Internet
- Revisar los logs del servidor API

## 📝 Notas Técnicas

### Máquina de Estados del Arduino

El Arduino implementa una máquina de estados robusta:

1. **ESPERANDO_OBJETO**: Estado inicial, esperando detección
2. **DETECTANDO_FOTO**: Objeto presente, contando 2 segundos
3. **ESPERANDO_RETIRO**: Foto solicitada, esperando que se retire el objeto
4. **VENTANA_DECISION**: Despues de 3 segundos el usuario decide continuar o terminar

### Tiempos Configurables

En `ArduinoNano/SensorProximidad.ino`:

```cpp
const long tiempoDeteccionRequerido = 2000; // Tiempo para confirmar objeto (ms)
const long tiempoConfirmacionRetiro = 3000; // Tiempo de ventana de decisión (ms)
```

### Configuración de Cámara

En `src/photos.py`, la resolución de captura es:

```python
capture_config = picam2.create_still_configuration(main={"size": (1280, 720)})
```

Puedes ajustar la resolución según tus necesidades.



## 📄 Licencia

Este proyecto es de código abierto. Consulta el archivo LICENSE para más detalles.

## 👥 Autores

- **Equipo 3** - Desarrolladores iniciales

## 🙏 Agradecimientos

- Comunidad de Raspberry Pi por la documentación de Picamera2
- Arduino por el ecosistema de hardware abierto
- Contribuidores de las librerías utilizadas (pyserial, requests, etc.)