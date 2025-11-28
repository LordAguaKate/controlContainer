/*
 * ARDUINO NANO 2 - CONTROL DE MOTORES Y BANDA (MODO COMPUERTAS + REFUERZO)
 * -------------------------------------------
 * Lógica: 
 * 1. Inicio: Servos en posición CERRADO (Posición de espera).
 * 2. Si es PLASTICO:
 * - Compuerta ALUMINIO se ABRE (deja pasar).
 * - Compuerta PLASTICO se CIERRA EXTRA (asegura el rebote).
 * 3. Si es ALUMINIO:
 * - Compuerta PLASTICO se ABRE (deja pasar).
 * - Compuerta ALUMINIO se CIERRA EXTRA (asegura el rebote).
 * 4. Al finalizar, regresan a CERRADO (Normal).
 */

#include <Servo.h>

// --- OBJETOS SERVO ---
Servo servoAluminio; // Pin D9  (Power HD LF-20MG) 
Servo servoPlastico; // Pin D10 (RB-150MG)         

// --- PINES ---
const int PIN_BANDA = 6;     
const int PIN_SERVO_ALU = 9;  
const int PIN_SERVO_PLA = 10; 

// --- CONFIGURACIÓN DE ÁNGULOS ---

// 1. SERVO ALUMINIO (D9)
// Cierra bajando grados (150 -> 80)
const int ALU_ABIERTO = 150;      // Deja pasar
const int ALU_CERRADO = 80;       // Posición de espera
const int ALU_CERRADO_EXTRA = 50; 

// 2. SERVO PLÁSTICO (D10)
// Cierra subiendo grados (30 -> 140)
const int PLA_ABIERTO = 30;       // Deja pasar
const int PLA_CERRADO = 140;      // Posición de espera
const int PLA_CERRADO_EXTRA = 160;

// --- TIEMPOS ---
const int TIEMPO_ESPERA_SERVO = 1000; // Tiempo para que los servos se acomoden antes de prender banda
const int TIEMPO_RECORRIDO    = 5000; // Tiempo que la banda dura prendida

void setup() {
  Serial.begin(9600);
  
  // Configuración de Pines
  pinMode(PIN_BANDA, OUTPUT);
  digitalWrite(PIN_BANDA, LOW); // Banda apagada al inicio

  // Configuración de Servos
  servoAluminio.attach(PIN_SERVO_ALU, 500, 2500);
  servoPlastico.attach(PIN_SERVO_PLA, 500, 2500); 

  // Posiciones iniciales: AMBOS CERRADOS (NORMAL)
  resetearServos();
  
  Serial.println("SISTEMA DE MOTORES (CON REFUERZO DE CIERRE) LISTO");
}

void loop() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    if (comando.length() > 0) {
      procesarClasificacion(comando);
    }
  }
}

void procesarClasificacion(String material) {
  Serial.print("Clasificando: ");
  Serial.println(material);

  // --- PASO 1: POSICIONAR SERVOS ---
  
  if (material == "PLASTICO") {
    // Queremos PLASTICO:
    // 1. Abrimos la puerta de ALUMINIO para que no estorbe.
    servoAluminio.write(ALU_ABIERTO);
    // 2. Cerramos EXTRA la puerta de PLASTICO para asegurar que choque y caiga en su lugar.
    servoPlastico.write(PLA_CERRADO_EXTRA);
    
  } else if (material == "ALUMINIO") {
    // Queremos ALUMINIO:
    // 1. Cerramos EXTRA la puerta de ALUMINIO para asegurar que choque y caiga en su lugar.
    servoAluminio.write(ALU_CERRADO_EXTRA);
    // 2. Abrimos la puerta de PLASTICO para que no estorbe.
    servoPlastico.write(PLA_ABIERTO);
    
  } else {
    // "OTRO" o "RECHAZADO"
    // Ambos se abren para dejar pasar todo recto.
    servoAluminio.write(ALU_ABIERTO);
    servoPlastico.write(PLA_ABIERTO); 
  }

  // --- PASO 2: ESPERAR MOVIMIENTO ---
  delay(TIEMPO_ESPERA_SERVO);

  // --- PASO 3: ACTIVAR BANDA ---
  digitalWrite(PIN_BANDA, HIGH);
  
  // --- PASO 4: TIEMPO DE TRANSPORTE ---
  delay(TIEMPO_RECORRIDO);

  // --- PASO 5: FINALIZAR ---
  digitalWrite(PIN_BANDA, LOW);
  
  // Regresamos ambos servos a posición CERRADO NORMAL (Espera)
  resetearServos();
  
  Serial.println("Ciclo terminado.");
}

// Función auxiliar para volver al estado de reposo normal
void resetearServos() {
  servoAluminio.write(ALU_CERRADO); 
  servoPlastico.write(PLA_CERRADO); 
}
