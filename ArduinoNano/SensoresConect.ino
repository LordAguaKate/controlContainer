// --- LIBRERÍAS ---
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_NeoPixel.h> 

// --- INICIALIZACIÓN DE LCD ---
LiquidCrystal_I2C lcd(0x27, 16, 2); // 0x27 o 0x3F

// --- CONFIGURACIÓN DE TIRA LED ---
#define PIN_LED_TIRA 13    
#define NUM_LEDS 30        
Adafruit_NeoPixel tiraled = Adafruit_NeoPixel(NUM_LEDS, PIN_LED_TIRA, NEO_GRB + NEO_KHZ800);

// --- OTROS PINES EXISTENTES ---
const int SENSOR_PIN = 4;
const int botonPin = 3;
const int BUZZER_PIN = 5;

// --- NUEVOS PINES: ULTRASONICOS ---
// 1. Aluminio
const int TRIG_ALU = 7;
const int ECHO_ALU = 6;
// 2. No Reciclable (Basura)
const int TRIG_BASURA = 9;
const int ECHO_BASURA = 8;
// 3. Plástico
const int TRIG_PLA = 11;
const int ECHO_PLA = 10;

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

// --- FUNCIÓN AUXILIAR PARA LA TIRA LED ---
void colorFull(uint32_t color) {
  for (int i = 0; i < NUM_LEDS; i++) {
    tiraled.setPixelColor(i, color);
  }
  tiraled.show();
}

// --- FUNCIÓN AUXILIAR PARA EL BUZZER ---
void beep(int duracion) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(duracion);
  digitalWrite(BUZZER_PIN, LOW);
}

// --- NUEVA FUNCIÓN AUXILIAR PARA ULTRASONICOS ---
long obtenerDistancia(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Timeout de 30ms para no bloquear el sistema principal si falla un sensor
  long duracion = pulseIn(echoPin, HIGH, 30000); 
  
  if (duracion == 0) return -1; // Error
  return duracion * 0.034 / 2;
}

// --- FUNCIÓN PARA CAMBIAR ESTADO ---
void cambiarEstado(Estado nuevoEstado) {
  estadoActual = nuevoEstado;
  tiempoInicioPausa = millis(); 
  tiempoUltimaActividad = millis(); 
}

void setup() {
  // Pines existentes
  pinMode(SENSOR_PIN, INPUT);
  pinMode(botonPin, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // --- CONFIGURAR PINES ULTRASONICOS ---
  pinMode(TRIG_ALU, OUTPUT); pinMode(ECHO_ALU, INPUT);
  pinMode(TRIG_BASURA, OUTPUT); pinMode(ECHO_BASURA, INPUT);
  pinMode(TRIG_PLA, OUTPUT); pinMode(ECHO_PLA, INPUT);

  // Inicializar Tira LED
  tiraled.begin();
  tiraled.show(); 
  colorFull(tiraled.Color(0, 0, 0)); 

  Serial.begin(9600);
  Serial.println("Sistema Sensores + Ultrasonicos INICIADO.");

  lcd.init();
  lcd.backlight();
  Serial.println("LCD Inicializada.");

  lcd.setCursor(0, 0);
  lcd.print("Escanee su QR...");
  beep(50);
  
  tiempoUltimaActividad = millis();
}

// --- LEER COMANDOS DE LA PI ---
void leerComandosSerial() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    // --- COMANDO NUEVO: LEER NIVELES ---
    if (comando == "LEER_ULTRASONICOS") {
      // Leemos los 3 sensores
      long distAlu = obtenerDistancia(TRIG_ALU, ECHO_ALU);
      delay(10); // Pequeña pausa técnica
      long distBasura = obtenerDistancia(TRIG_BASURA, ECHO_BASURA);
      delay(10);
      long distPla = obtenerDistancia(TRIG_PLA, ECHO_PLA);

      // Enviamos respuesta a la Pi: "NIVELES:val1,val2,val3"
      Serial.print("NIVELES:");
      Serial.print(distAlu);
      Serial.print(",");
      Serial.print(distBasura);
      Serial.print(",");
      Serial.println(distPla);
      
      return; // Salimos para no procesar lógica de estados innecesariamente
    }

    // --- COMANDOS EXISTENTES DE FLUJO ---
    
    // 1. Pi detectó un QR
    if (comando == "VALIDANDO" && estadoActual == INACTIVO) {
      Serial.println("Info: Pi esta validando el QR...");
      beep(50);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Identificando..."); // lcd.print("Iniciando sesion"); 
      lcd.setCursor(0, 1);
      lcd.print("Por favor espere"); 
      cambiarEstado(VALIDANDO_QR);
    }
    
    // 2. Error de Sesión
    else if (comando == "ERROR_SESION" && estadoActual == VALIDANDO_QR) {
      Serial.println("Info: Error de sesion.");
      beep(50); delay(50); beep(50);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("No identificado"); // lcd.print("Error al iniciar"); 
      lcd.setCursor(0, 1);
      lcd.print("Intente de nuevo"); 
      cambiarEstado(MOSTRANDO_ERROR_SESION);
    }

    // 3. Sesión Exitosa
    else if (comando.startsWith("SESION_OK:") && estadoActual == VALIDANDO_QR) {
      String name = comando.substring(10);
      Serial.println("Info: Sesion OK.");
      
      beep(150);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Bienvenid@"); // lcd.print("Sesion correcta"); 
      lcd.setCursor(0, 1);
      lcd.print(name); 
      
      cambiarEstado(MOSTRANDO_BIENVENIDA_1);
    }

    // 4. Resultado de Foto
    if (estadoActual == PROCESANDO_FOTO) {
      if (comando.startsWith("APROBADO:")) {
        String material = comando.substring(9);
        beep(300);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Material:"); 
        lcd.setCursor(0, 1);
        lcd.print(material); 
        Serial.println("Info: Aprobado. Esperando retiro.");
        cambiarEstado(MOSTRANDO_APROBADO);

      } else if (comando == "RECHAZADO") {
        beep(50); delay(50); beep(50);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("El material es"); // lcd.print("Material"); 
        lcd.setCursor(0, 1);
        lcd.print("No valido"); // lcd.print("No Reciclable"); 
        Serial.println("Info: Rechazado. Esperando retiro.");
        cambiarEstado(MOSTRANDO_RECHAZADO);
      }
    }
  }
}

// --- Ir al estado INACTIVO ---
void finalizarSesion(String motivo) {
  Serial.println(motivo);
  colorFull(tiraled.Color(0, 0, 0)); 

  if (motivo == "TERMINAR") {
    beep(150); delay(50); beep(100);
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Finalizando"); // lcd.print("Sesion terminada"); 
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
  // 1. Escuchar comandos (Incluyendo LEER_ULTRASONICOS)
  leerComandosSerial();

  // 3. Lógica de Sesión Activa (Timeout y Botón)
  if (estadoActual == ESPERANDO_OBJETO ||
      estadoActual == DETECTANDO_FOTO ||
      estadoActual == ESPERANDO_RETIRO) 
  {
      bool objetoDetectado = (digitalRead(SENSOR_PIN) == LOW);
      bool botonPresionado = (digitalRead(botonPin) == HIGH);

      if (botonPresionado) {
          while(digitalRead(botonPin) == HIGH) { delay(50); }
          finalizarSesion("TERMINAR");
          return;
      }

      if (millis() - tiempoUltimaActividad > tiempoInactividadSesion) {
          Serial.println("Info: Timeout.");
          finalizarSesion("TERMINAR");
          return;
      }
  }

  // 4. Máquina de Estados
  switch (estadoActual) {

    case ESPERANDO_OBJETO:
      if (digitalRead(SENSOR_PIN) == LOW) {
        tiempoPrimerDeteccion = millis();
        colorFull(tiraled.Color(255, 255, 255)); 
        beep(100);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Objeto detectado"); 
        lcd.setCursor(0, 1);
        lcd.print("Espere 2 seg..."); 
        Serial.println("Info: Detectado, iniciando timer...");
        cambiarEstado(DETECTANDO_FOTO);
      }
      break;

    case DETECTANDO_FOTO:
      if (digitalRead(SENSOR_PIN) == HIGH) { 
        colorFull(tiraled.Color(0, 0, 0)); 
        beep(50); delay(50); beep(50);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Objeto retirado"); 
        Serial.println("Info: Retirado antes de tiempo.");
        delay(1500); 
        lcd.clear();
        lcd.setCursor(0, 0); 
        lcd.print("Deposite objeto"); 
        lcd.setCursor(0, 1); 
        lcd.print("en el contenedor"); 
        cambiarEstado(ESPERANDO_OBJETO);
        
      } else if (millis() - tiempoPrimerDeteccion >= tiempoDeteccionRequerido) {
        Serial.println("FOTO"); // Pi recibe esto y toma foto
        beep(100);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Procesando..."); 
        lcd.setCursor(0, 1);
        lcd.print("Espere por favor"); 
        cambiarEstado(PROCESANDO_FOTO);
      }
      break;

    case ESPERANDO_RETIRO:
      if (digitalRead(SENSOR_PIN) == HIGH) { 
        colorFull(tiraled.Color(0, 0, 0));
        beep(100);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Deposite otro o"); 
        lcd.setCursor(0, 1);
        lcd.print("pulse el boton"); // lcd.print("pulse p/ salir"); 
        Serial.println("Info: Retirado. Listo siguiente.");
        cambiarEstado(ESPERANDO_OBJETO);
      }
      break;
    
    // --- Temporizadores de Mensajes ---
    case MOSTRANDO_ERROR_SESION:
      if (millis() - tiempoInicioPausa > TIEMPO_MENSAJE) {
        lcd.clear(); lcd.print("Escanee su QR...");
        cambiarEstado(INACTIVO);
      }
      break;
    case MOSTRANDO_BIENVENIDA_1:
      if (millis() - tiempoInicioPausa > TIEMPO_MENSAJE) {
        lcd.clear(); lcd.print("Deposite objeto"); lcd.setCursor(0,1); lcd.print("en contenedor");
        cambiarEstado(ESPERANDO_OBJETO);
      }
      break;
    case MOSTRANDO_APROBADO:
    case MOSTRANDO_RECHAZADO:
      if (millis() - tiempoInicioPausa > TIEMPO_MENSAJE) {
        colorFull(tiraled.Color(0, 0, 0));
        lcd.clear(); lcd.print("Retirando..."); lcd.setCursor(0,1); lcd.print("Espere por favor");
        cambiarEstado(ESPERANDO_RETIRO);
      }
      break;
      
    case INACTIVO:
    case VALIDANDO_QR:
    case PROCESANDO_FOTO:
      break;
  }
  delay(50); 
}