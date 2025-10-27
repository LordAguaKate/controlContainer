/*
  SensoresConect.ino
  V2.3 - Espera la respuesta de la API desde la Pi.

  Flujo:
  1. Envía "FOTO".
  2. Entra en estado "PROCESANDO_FOTO" y muestra "Procesando...".
  3. Espera un comando de la Pi: "APROBADO:<material>" o "RECHAZADO".
  4. Muestra el resultado y luego pasa a "ESPERANDO_RETIRO".
*/

// --- LIBRERÍAS ---
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// --- INICIALIZACIÓN DE LCD ---
LiquidCrystal_I2C lcd(0x27, 16, 2); // 0x27 o 0x3F

// --- PINES ---
const int SENSOR_PIN = 4;
const int botonPin = 3;
const int LED_PIN = 13;
const int BUZZER_PIN = 5;

// --- CONFIGURACIÓN DE TIEMPOS ---
const long tiempoDeteccionRequerido = 2000;
const long tiempoInactividadSesion = 15000;

// --- Máquina de Estados (NUEVO ESTADO) ---
enum Estado {
  INACTIVO,
  ESPERANDO_OBJETO,
  DETECTANDO_FOTO,
  PROCESANDO_FOTO, // Nuevo estado: esperando respuesta de la Pi
  ESPERANDO_RETIRO
};
Estado estadoActual = INACTIVO;

// --- Variables de control ---
unsigned long tiempoPrimerDeteccion = 0;
unsigned long tiempoUltimaActividad = 0;

// --- FUNCIÓN AUXILIAR PARA EL BUZZER ---
void beep(int duracion) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(duracion);
  digitalWrite(BUZZER_PIN, LOW);
}

// --- FUNCIÓN AUXILIAR PARA CAMBIAR ESTADO ---
void cambiarEstado(Estado nuevoEstado) {
  estadoActual = nuevoEstado;
  tiempoUltimaActividad = millis();
}

void setup() {
  pinMode(SENSOR_PIN, INPUT);
  pinMode(botonPin, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.begin(9600);
  Serial.println("Sistema de Sensores Conectados INICIADO. (v2.3)");

  lcd.init();
  lcd.backlight();
  Serial.println("LCD Inicializada.");

  lcd.setCursor(0, 0);
  lcd.print("Bienvenido");
  lcd.setCursor(0, 1);
  lcd.print("Escanee su QR...");
  beep(50);
}

// --- Revisar comandos de la Pi ---
void leerComandosSerial() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    // Comando para iniciar sesión
    if (comando == "START" && estadoActual == INACTIVO) {
      Serial.println("Info: Comando START recibido. Iniciando sesion.");
      beep(100);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Deposite");
      lcd.setCursor(0, 1);
      lcd.print("el objeto...");
      cambiarEstado(ESPERANDO_OBJETO);
    }
    
    // --- RESPUESTA DE API ---
    // Solo escuchar si estamos en el estado de espera correcto
    if (estadoActual == PROCESANDO_FOTO) {
      
      if (comando.startsWith("APROBADO:")) {
        String material = comando.substring(9); // Obtiene el texto después de "APROBADO:"
        
        beep(300); // Sonido de éxito
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Aprobado:");
        lcd.setCursor(0, 1);
        lcd.print(material); // Muestra el tipo de material
        
        Serial.println("Info: Pi aprobo el material. Esperando retiro.");
        delay(2500); // Mostrar el mensaje por 2.5 segundos

        // Siguiente paso: esperar que la cinta lo retire
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Retirando...");
        cambiarEstado(ESPERANDO_RETIRO);

      } else if (comando == "RECHAZADO") {
        
        beep(50); delay(50); beep(50); // Sonido de error
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Material");
        lcd.setCursor(0, 1);
        lcd.print("Rechazado");
        
        Serial.println("Info: Pi rechazo el material. Esperando retiro.");
        delay(2500); // Mostrar el mensaje por 2.5 segundos

        // Siguiente paso: esperar que la cinta lo retire
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Retirando...");
        cambiarEstado(ESPERANDO_RETIRO);
      }
    }
  }
}

// --- Ir al estado INACTIVO ---
void finalizarSesion(String motivo) {
  Serial.println(motivo); // "TERMINAR"
  digitalWrite(LED_PIN, LOW);

  if (motivo == "TERMINAR") {
    beep(150); delay(50); beep(100);
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sesion terminada");
    lcd.setCursor(0, 1);
    lcd.print("!Gracias!");
    delay(2000);
  }
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Bienvenido");
  lcd.setCursor(0, 1);
  lcd.print("Escanee su QR...");
  estadoActual = INACTIVO;
}


void loop() {
  // 1. Siempre escuchar a la Pi
  leerComandosSerial();

  if (estadoActual == INACTIVO) {
    return;
  }

  // --- Lógica de Sesión Activa ---
  bool objetoDetectado = (digitalRead(SENSOR_PIN) == LOW);
  bool botonPresionado = (digitalRead(botonPin) == HIGH);

  // 3. Reglas Globales de Cierre de Sesión
  // No se puede cerrar sesión mientras se procesa la foto
  if (estadoActual != PROCESANDO_FOTO) {
    if (botonPresionado) {
      while(digitalRead(botonPin) == HIGH) { delay(50); }
      finalizarSesion("TERMINAR");
      return;
    }

    if (millis() - tiempoUltimaActividad > tiempoInactividadSesion) {
      Serial.println("Info: Timeout de inactividad.");
      finalizarSesion("TERMINAR");
      return;
    }
  }

  // 4. Máquina de Estados
  switch (estadoActual) {

    case ESPERANDO_OBJETO:
      if (objetoDetectado) {
        tiempoPrimerDeteccion = millis();
        digitalWrite(LED_PIN, HIGH);
        
        beep(100);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Objeto detectado");
        lcd.setCursor(0, 1);
        lcd.print("Espere 2 seg...");
        
        Serial.println("Info: Objeto detectado, iniciando temporizador de foto...");
        cambiarEstado(DETECTANDO_FOTO);
      }
      break;

    case DETECTANDO_FOTO:
      if (!objetoDetectado) {
        // Objeto retirado prematuramente
        digitalWrite(LED_PIN, LOW);
        beep(50); delay(50); beep(50);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Objeto retirado");
        lcd.setCursor(0, 1);
        lcd.print("Reiniciando...");
        Serial.println("Info: Objeto retirado prematuramente. Reiniciando.");
        delay(1500);

        lcd.clear();
        lcd.setCursor(0, 0); lcd.print("Deposite");
        lcd.setCursor(0, 1); lcd.print("el objeto...");
        cambiarEstado(ESPERANDO_OBJETO);
        
      } else if (millis() - tiempoPrimerDeteccion >= tiempoDeteccionRequerido) {
        // ÉXITO: Foto tomada, enviar señal a Pi
        Serial.println("FOTO"); // Enviar comando a la RPi
        beep(100); // Beep corto de "procesando"
        
        // --- CAMBIO ---
        // Ahora mostramos "Procesando" y esperamos respuesta
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Procesando...");
        lcd.setCursor(0, 1);
        lcd.print("Espere...");
        
        Serial.println("Info: Foto solicitada. Esperando respuesta de la API...");
        cambiarEstado(PROCESANDO_FOTO); // Mover al nuevo estado de espera
      }
      break;

      case ESPERANDO_RETIRO:
        // Este estado ahora solo espera que la cinta retire el objeto
        if (!objetoDetectado) {
          beep(100);
          lcd.clear();
          lcd.setCursor(0, 0);
          lcd.print("Deposite otro");
          lcd.setCursor(0, 1);
          lcd.print("o pulse p/fin");

          Serial.println("Info: Objeto retirado. Esperando siguiente objeto o fin de sesion...");
          cambiarEstado(ESPERANDO_OBJETO); // Vuelve a esperar objeto
        }
        break;
    
    // Estados inactivos o de espera
    case INACTIVO:
    case PROCESANDO_FOTO:
      // No hacer nada, solo esperar comandos en leerComandosSerial()
      break;
  }
  delay(50);
}

