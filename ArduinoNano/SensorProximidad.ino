// Sensor de proximidad infrarrojo E18-D80NK y botón de captura
// Envía una señal a través del puerto serie para tomar una foto.

// --- Pines ---
const int SENSOR_PIN = 4;     // Pin del sensor infrarrojo
const int botonPin = 3;  // Botón para finalizar la sesión del usuario.
const int LED_PIN = 13;       // LED integrado en el Arduino Nano

// --- CONFIGURACIÓN DE TIEMPOS ---
const long tiempoDeteccionRequerido = 2000; // 2 segundos con objeto para tomar foto
const long tiempoConfirmacionRetiro = 3000; // 3 segundos sin objeto para reiniciar

// --- Máquina de Estados ---
enum Estado {
  ESPERANDO_OBJETO,
  DETECTANDO_FOTO,
  ESPERANDO_RETIRO,
  VENTANA_DECISION
};
Estado estadoActual = ESPERANDO_OBJETO;

// --- Variables de control ---
unsigned long tiempoPrimerDeteccion = 0;
unsigned long tiempoPrimerRetiro = 0;

void setup() {
  pinMode(sensorPin, INPUT);
  pinMode(botonPin, INPUT); // Botón configurado como pull-down.
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
  Serial.println("Sensor en modo automatico con confirmacion. Esperando objeto...");
}

void loop() {
  bool objetoDetectado = (digitalRead(sensorPin) == LOW);
  bool botonPresionado = (digitalRead(botonPin) == HIGH);

  switch (estadoActual) {

    case ESPERANDO_OBJETO:
      // Estado inicial: esperando que un objeto sea colocado.
      if (objetoDetectado) {
        tiempoInicioDeteccion = millis();
        estadoActual = DETECTANDO_FOTO;
        digitalWrite(ledPin, HIGH);
        Serial.println("Info: Objeto detectado, iniciando temporizador de foto...");
      }
      break;

    case DETECTANDO_FOTO:
      // Un objeto está presente, estamos esperando que pasen 2 segundos.
      if (!objetoDetectado) {
        // Si el objeto se retira antes de tiempo, volvemos a empezar.
        estadoActual = ESPERANDO_OBJETO;
        digitalWrite(ledPin, LOW);
        Serial.println("Info: Objeto retirado prematuramente. Reiniciando.");
      } else if (millis() - tiempoInicioDeteccion >= tiempoDeteccionRequerido) {
        // Pasaron los 2 segundos, enviamos la señal para la foto.
        Serial.println("FOTO"); // Enviar comando a la RPi
        estadoActual = ESPERANDO_RETIRO;
        Serial.println("Info: Foto solicitada. Esperando retiro del objeto...");
      }
      break;

      case ESPERANDO_RETIRO:
      if (!objetoDetectado) {
        tiempoInicioRetiro = millis();
        estadoActual = VENTANA_DECISION;
        Serial.println("Info: Objeto retirado. El usuario tiene 3 segundos para decidir...");
      }
      break;

      case VENTANA_DECISION:
      // Durante 3 segundos, revisamos si el usuario presiona el botón.
      if (botonPresionado) {
        Serial.println("TERMINAR"); // El usuario quiere finalizar la sesión.
        estadoActual = ESPERANDO_OBJETO; // Listo para el próximo usuario.
        digitalWrite(ledPin, LOW);
        // Esperamos a que suelte el botón para no enviar multiples señales
        while(digitalRead(botonPin) == HIGH) { delay(50); }
      } else if (millis() - tiempoInicioRetiro >= tiempoDecisionUsuario) {
        // Pasaron los 3 segundos y no presionó el botón.
        Serial.println("LISTO_SIGUIENTE"); // Continuar con el siguiente objeto.
        estadoActual = ESPERANDO_OBJETO;
        digitalWrite(ledPin, LOW);
        Serial.println("Info: Ventana de decision terminada. Esperando siguiente objeto...");
      }
      break;
  }
  delay(50);
}