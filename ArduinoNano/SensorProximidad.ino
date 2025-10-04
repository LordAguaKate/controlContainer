// Sensor de proximidad infrarrojo E18-D80NK y botón de captura
// Envía una señal a través del puerto serie para tomar una foto.

// --- Pines ---
const int SENSOR_PIN = 4;     // Pin del sensor infrarrojo
const int LED_PIN = 13;       // LED integrado en el Arduino Nano

// --- CONFIGURACIÓN DE TIEMPOS ---
const long tiempoDeteccionRequerido = 2000; // 2 segundos con objeto para tomar foto
const long tiempoConfirmacionRetiro = 3000; // 3 segundos sin objeto para reiniciar

// --- Máquina de Estados ---
enum Estado { ESPERANDO, DETECTANDO, EN_PAUSA, CONFIRMANDO_RETIRO };
Estado estadoActual = ESPERANDO;

// --- Variables de control ---
unsigned long tiempoPrimerDeteccion = 0;
unsigned long tiempoPrimerRetiro = 0;

void setup() {
  pinMode(sensorPin, INPUT);
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
  Serial.println("Sensor en modo automatico con confirmacion. Esperando objeto...");
}

void loop() {
  bool objetoDetectado = (digitalRead(sensorPin) == LOW);

  switch (estadoActual) {
    case ESPERANDO:
      // Estado inicial: esperando que un objeto sea colocado.
      if (objetoDetectado) {
        tiempoPrimerDeteccion = millis(); // Iniciar temporizador de detección
        estadoActual = DETECTANDO;
        digitalWrite(ledPin, HIGH); // Encender LED
        Serial.println("Estado: Objeto detectado. Iniciando temporizador de 2s...");
      }
      break;

    case DETECTANDO:
      // Un objeto está presente, estamos esperando que pasen 2 segundos.
      if (!objetoDetectado) {
        // Si el objeto se retira antes de tiempo, volvemos a empezar.
        estadoActual = ESPERANDO;
        digitalWrite(ledPin, LOW);
        Serial.println("Estado: Objeto retirado prematuramente. Reiniciando.");
      } else if (millis() - tiempoPrimerDeteccion >= tiempoDeteccionRequerido) {
        // Pasaron los 2 segundos, enviamos la señal para la foto.
        Serial.println("FOTO");
        estadoActual = EN_PAUSA;
        Serial.println("Estado: Foto solicitada. Por favor, retire el objeto.");
      }
      break;

    case EN_PAUSA:
      // La foto ya fue solicitada, esperamos a que el usuario retire el objeto.
      if (!objetoDetectado) {
        tiempoPrimerRetiro = millis(); // Iniciar temporizador de confirmación
        estadoActual = CONFIRMANDO_RETIRO;
        Serial.println("Estado: Objeto retirado. Confirmando en 3s...");
      }
      break;

    case CONFIRMANDO_RETIRO:
      // El objeto fue retirado, ahora contamos 3 segundos para asegurarnos.
      if (objetoDetectado) {
        // ¡El objeto volvió! El usuario no lo retiró completamente.
        estadoActual = EN_PAUSA;
        Serial.println("Estado: Objeto re-detectado. Vuelva a retirarlo.");
      } else if (millis() - tiempoPrimerRetiro >= tiempoConfirmacionRetiro) {
        // Pasaron los 3 segundos sin el objeto, el ciclo terminó.
        estadoActual = ESPERANDO;
        digitalWrite(ledPin, LOW); // Apagar LED, listo para la próxima
        Serial.println("-------------------------------------------------");
        Serial.println("Estado: Reinicio completo. Listo para proximo ciclo.");
      }
      break;
  }

  delay(50); // Pequeña pausa para estabilizar lecturas
}