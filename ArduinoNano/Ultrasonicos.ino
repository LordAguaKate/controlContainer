#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5
#define TRIG3 6
#define ECHO3 7

void setup() {
  Serial.begin(9600);

  pinMode(TRIG1, OUTPUT);
  pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT);
  pinMode(ECHO2, INPUT);
  pinMode(TRIG3, OUTPUT);
  pinMode(ECHO3, INPUT);
}

int medirDistancia(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duracion = pulseIn(echoPin, HIGH, 25000); // timeout 25ms
  if (duracion == 0) return -1; // sensor falló

  int distancia = duracion * 0.034 / 2;
  if (distancia <= 0 || distancia > 400) return -1; // rango inválido

  return distancia;
}

void loop() {
  int d1 = medirDistancia(TRIG1, ECHO1);
  int d2 = medirDistancia(TRIG2, ECHO2);
  int d3 = medirDistancia(TRIG3, ECHO3);

  // Elegir un valor válido
  int valido = 0;
  if (d1 != -1) valido = d1;
  else if (d2 != -1) valido = d2;
  else if (d3 != -1) valido = d3;
  else valido = 0;  // Ninguno funciona

  // Crear JSON completo en UNA sola línea
  char jsonBuffer[120];
  sprintf(jsonBuffer,
          "{sensor1: %d, sensor2: %d, sensor3: %d}",
          (d1 == -1 ? valido : d1),
          (d2 == -1 ? valido : d2),
          (d3 == -1 ? valido : d3));

  Serial.println(jsonBuffer);

  delay(400);
}
