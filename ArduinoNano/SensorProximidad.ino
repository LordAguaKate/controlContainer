// Sensor de proximidad infrarrojo E18-D80NK y botón de captura
// Envía una señal a través del puerto serie para tomar una foto.

// --- Pines ---
const int SENSOR_PIN = 4;     // Pin del sensor infrarrojo
const int BOTON_PIN = 3;      // Pin para el botón (configurado como pull-down)
const int LED_PIN = 13;       // LED integrado en el Arduino Nano

// --- Estados para la máquina de estados ---
enum Estado {
  ESPERANDO_OBJETO,            // No hay objeto, esperando que se coloque uno
  OBJETO_DETECTADO,            // Hay un objeto, esperando pulsación del botón
  ESPERANDO_RETIRO_OBJETO      // Foto tomada, esperando que se retire el objeto por 3 segundos
};
Estado estadoActual = ESPERANDO_OBJETO;

// --- Variables para el temporizador de retiro de objeto ---
unsigned long tiempoObjetoRetirado = 0;
const long tiempoDeEsperaParaReinicio = 3000; // 3 segundos

void setup() {
  pinMode(SENSOR_PIN, INPUT);
  pinMode(BOTON_PIN, INPUT); // Botón pull-down, HIGH cuando se presiona
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(9600);

  Serial.println("Sistema de captura iniciado.");
  Serial.println("============================");
}

void loop() {
  // Leemos el estado actual de los sensores
  bool objetoPresente = (digitalRead(SENSOR_PIN) == LOW);
  bool botonPresionado = (digitalRead(BOTON_PIN) == HIGH);

  // Máquina de estados para controlar el flujo
  switch (estadoActual) {
    case ESPERANDO_OBJETO:
      digitalWrite(LED_PIN, LOW); // LED apagado
      if (objetoPresente) {
        estadoActual = OBJETO_DETECTADO;
        Serial.println("Estado: Objeto detectado. Listo para foto.");
      }
      break;

    case OBJETO_DETECTADO:
      digitalWrite(LED_PIN, HIGH); // LED encendido para indicar que está listo
      if (!objetoPresente) {
        // Si el objeto se retira antes de tomar la foto, volvemos al estado inicial
        estadoActual = ESPERANDO_OBJETO;
        Serial.println("Estado: Objeto retirado. Esperando nuevo objeto.");
      } else if (botonPresionado) {
        // Si se presiona el botón CON el objeto presente
        Serial.println("FOTO"); // Enviamos el comando a la Raspberry Pi
        estadoActual = ESPERANDO_RETIRO_OBJETO;
        Serial.println("Estado: Foto solicitada. Esperando retiro del objeto...");
        delay(200); // Pequeño delay para evitar múltiples lecturas del botón
      }
      break;

    case ESPERANDO_RETIRO_OBJETO:
      digitalWrite(LED_PIN, LOW); // LED parpadea para indicar que espera retiro
      delay(150);
      digitalWrite(LED_PIN, HIGH);
      delay(150);

      if (!objetoPresente) {
        // Si el objeto ya no está, iniciamos el contador
        if (tiempoObjetoRetirado == 0) {
          tiempoObjetoRetirado = millis();
        }
        
        // Verificamos si han pasado los 3 segundos
        if (millis() - tiempoObjetoRetirado >= tiempoDeEsperaParaReinicio) {
          Serial.println("Estado: Sistema reiniciado. Esperando nuevo objeto.");
          estadoActual = ESPERANDO_OBJETO;
          tiempoObjetoRetirado = 0; // Reseteamos el contador
        }
      } else {
        // Si el objeto vuelve a aparecer, reseteamos el contador
        tiempoObjetoRetirado = 0;
      }
      break;
  }
}
