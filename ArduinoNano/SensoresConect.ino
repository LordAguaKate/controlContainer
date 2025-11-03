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
const long tiempoInactividadSesion = 60000; // 60 segundos
const long TIEMPO_MENSAJE = 3000; // 3 seg para mostrar mensajes

// --- Máquina de Estados ---
enum Estado {
  INACTIVO,
  VALIDANDO_QR,
  MOSTRANDO_ERROR_SESION,
  MOSTRANDO_BIENVENIDA_1,
  ESPERANDO_OBJETO,
  DETECTANDO_FOTO,
  PROCESANDO_FOTO,
  MOSTRANDO_APROBADO,
  MOSTRANDO_RECHAZADO,
  ESPERANDO_RETIRO
};
Estado estadoActual = INACTIVO;

// --- Variables de control ---
unsigned long tiempoPrimerDeteccion = 0;
unsigned long tiempoUltimaActividad = 0;
unsigned long tiempoInicioPausa = 0;

// --- FUNCIÓN AUXILIAR PARA EL BUZZER ---
void beep(int duracion) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(duracion);
  digitalWrite(BUZZER_PIN, LOW);
}

// --- FUNCIÓN PARA CAMBIAR ESTADO (Reinicia timers) ---
void cambiarEstado(Estado nuevoEstado) {
  estadoActual = nuevoEstado;
  tiempoInicioPausa = millis(); // Para los estados de pausa
  tiempoUltimaActividad = millis(); // Reinicia el timeout de inactividad
}

void setup() {
  pinMode(SENSOR_PIN, INPUT);
  pinMode(botonPin, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.begin(9600);
  Serial.println("Sistema de Sensores Conectados INICIADO.");

  lcd.init();
  lcd.backlight();
  Serial.println("LCD Inicializada.");

  lcd.setCursor(0, 0);
  lcd.print("Escanee su QR...");
  beep(50);
  
  tiempoUltimaActividad = millis();
}

// --- Revisar comandos de la Pi (SIN DELAYS) ---
void leerComandosSerial() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    // 1. Pi detectó un QR y está validando
    if (comando == "VALIDANDO" && estadoActual == INACTIVO) {
      Serial.println("Info: Pi esta validando el QR. Esperando resultado...");
      beep(50);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Iniciando sesion"); 
      lcd.setCursor(0, 1);
      lcd.print("Por favor espere"); 
      cambiarEstado(VALIDANDO_QR);
    }
    
    // 2. Pi informa que la sesión falló
    else if (comando == "ERROR_SESION" && estadoActual == VALIDANDO_QR) {
      Serial.println("Info: Pi reporta error de sesion.");
      beep(50); delay(50); beep(50);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Error al iniciar"); 
      lcd.setCursor(0, 1);
      lcd.print("Intente de nuevo"); 
      cambiarEstado(MOSTRANDO_ERROR_SESION);
    }

    // 3. Pi informa que la sesión fue exitosa
    else if (comando.startsWith("SESION_OK:") && estadoActual == VALIDANDO_QR) {
      String name = comando.substring(10);
      Serial.println("Info: Pi reporta sesion OK.");
      
      beep(150);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Sesion correcta"); 
      lcd.setCursor(0, 1);
      lcd.print(name); 
      
      cambiarEstado(MOSTRANDO_BIENVENIDA_1);
    }

    // 4. Lógica de respuesta de API (para la foto)
    if (estadoActual == PROCESANDO_FOTO) {
      if (comando.startsWith("APROBADO:")) {
        String material = comando.substring(9);
        beep(300);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Material:"); 
        lcd.setCursor(0, 1);
        lcd.print(material); 
        Serial.println("Info: Pi aprobo el material. Esperando retiro.");
        cambiarEstado(MOSTRANDO_APROBADO);

      } else if (comando == "RECHAZADO") {
        beep(50); delay(50); beep(50);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Material"); 
        lcd.setCursor(0, 1);
        lcd.print("No Reciclable"); 
        Serial.println("Info: Pi rechazo el material. Esperando retiro.");
        cambiarEstado(MOSTRANDO_RECHAZADO);
      }
    }
  }
}

// --- Ir al estado INACTIVO ---
void finalizarSesion(String motivo) {
  Serial.println(motivo);
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
  lcd.print("Escanee su QR..."); 
  estadoActual = INACTIVO;
  tiempoUltimaActividad = millis();
}


void loop() {
  // 1. Siempre escuchar a la Pi
  leerComandosSerial();

  // --- LÓGICA DE SCROLL ELIMINADA ---

  // 3. Lógica de Sesión Activa (Timeout y Botón)
  if (estadoActual == ESPERANDO_OBJETO ||
      estadoActual == DETECTANDO_FOTO ||
      estadoActual == ESPERANDO_RETIRO) 
  {
      bool objetoDetectado = (digitalRead(SENSOR_PIN) == LOW);
      bool botonPresionado = (digitalRead(botonPin) == HIGH);

      // 3a. Regla de Botón
      if (botonPresionado) {
          while(digitalRead(botonPin) == HIGH) { delay(50); }
          finalizarSesion("TERMINAR");
          return;
      }

      // 3b. Regla de Timeout
      if (millis() - tiempoUltimaActividad > tiempoInactividadSesion) {
          Serial.println("Info: Timeout de inactividad.");
          finalizarSesion("TERMINAR");
          return;
      }
  }

  // 4. Máquina de Estados (Incluye estados de pausa)
  switch (estadoActual) {

    // --- Estados de Lógica Principal ---
    case ESPERANDO_OBJETO:
      if (digitalRead(SENSOR_PIN) == LOW) {
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
      if (digitalRead(SENSOR_PIN) == HIGH) { // Objeto retirado
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
        lcd.setCursor(0, 0); 
        lcd.print("Deposite objeto"); 
        lcd.setCursor(0, 1); 
        lcd.print("en el contenedor"); 
        cambiarEstado(ESPERANDO_OBJETO);
        
      } else if (millis() - tiempoPrimerDeteccion >= tiempoDeteccionRequerido) {
        Serial.println("FOTO");
        beep(100);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Procesando..."); 
        lcd.setCursor(0, 1);
        lcd.print("Espere por favor"); 
        Serial.println("Info: Foto solicitada. Esperando respuesta de la API...");
        cambiarEstado(PROCESANDO_FOTO);
      }
      break;

    case ESPERANDO_RETIRO:
      if (digitalRead(SENSOR_PIN) == HIGH) { // Objeto retirado
        beep(100);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Deposite otro o"); 
        lcd.setCursor(0, 1);
        lcd.print("pulse p/ salir"); 
        Serial.println("Info: Objeto retirado. Esperando siguiente objeto o fin de sesion...");
        cambiarEstado(ESPERANDO_OBJETO);
      }
      break;

    // --- Estados de Pausa (No Bloqueantes) ---
    
    case MOSTRANDO_ERROR_SESION:
      // Espera 3 segundos (definido en TIEMPO_MENSAJE)
      if (millis() - tiempoInicioPausa > TIEMPO_MENSAJE) {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Escanee su QR...");
        cambiarEstado(INACTIVO);
      }
      break;

    case MOSTRANDO_BIENVENIDA_1:
      // Espera 3 segundos (definido en TIEMPO_MENSAJE)
      if (millis() - tiempoInicioPausa > TIEMPO_MENSAJE) {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Deposite objeto"); 
        lcd.setCursor(0, 1);
        lcd.print("en contenedor"); 
        cambiarEstado(ESPERANDO_OBJETO);
      }
      break;

    case MOSTRANDO_APROBADO:
    case MOSTRANDO_RECHAZADO:
      // Espera 3 segundos (definido en TIEMPO_MENSAJE)
      if (millis() - tiempoInicioPausa > TIEMPO_MENSAJE) {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Retirando..."); 
        lcd.setCursor(0, 1);
        lcd.print("Espere por favor"); 
        cambiarEstado(ESPERANDO_RETIRO);
      }
      break;

    // --- Estados "Pasivos" ---
    case INACTIVO:
    case VALIDANDO_QR:
    case PROCESANDO_FOTO:
      // No hacer nada, solo esperar comandos
      break;
  }
  delay(50); // Pequeño delay general
}
