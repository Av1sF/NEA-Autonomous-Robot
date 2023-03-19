
#include <Servo.h>
Servo servo;
const int sensorPin[] = {A0, A1, A2};
int distance[3];
String string;
int command;
int motorpin1 = 5;
int motorpin2 = 6;
const float MCU_VOLTAGE = 5.0;


void readDistance(int sensor){

  float volts = 0;
  int tempDistance = 0;
  int sensorValue = analogRead(sensorPin[sensor]);
  volts = sensorValue * (MCU_VOLTAGE / 1023.0);
  tempDistance = 120.8* pow(volts, -1.058); // convert voltage into distance with the equation of the curve of best fit from sensor data sheet (mm)
  if (tempDistance > 300) {
    distance[sensor] = 1000; // if distance is outside of the range of sensor, it's unreliable hence we need a dummy value
  }
  else {
    distance[sensor] = tempDistance;
  }
}

void setup() {
  Serial.begin(9600);
  servo.attach(9);
  servo.write(90);
  pinMode(motorpin1, OUTPUT);
  pinMode(motorpin2, OUTPUT);
  digitalWrite(motorpin1, LOW);
  digitalWrite(motorpin2, LOW);

 while (!Serial) {
  ;
 }

  delay(2000);

  //physically indicates serial communication is established when LED on arduino blinks twice
  digitalWrite(LED_BUILTIN, HIGH);   
  delay(1000);                       
  digitalWrite(LED_BUILTIN, LOW);    
  delay(1000);
  digitalWrite(LED_BUILTIN, HIGH);   
  delay(1000);                       
  digitalWrite(LED_BUILTIN, LOW);   
  delay(1000);

}

void loop() {
  

  if (Serial.available()) {
    string = Serial.readStringUntil('\n');
    string.trim();
    command = string.toInt();

    if (command == 1550){
      readDistance(0);
      readDistance(1);
      readDistance(2);
      Serial.print(distance[0]);
      Serial.print(',');  
      Serial.print(distance[1]);
      Serial.print(',');
      Serial.println(distance[2]);
    }

    else if ((2 <= command) && (command <= 180)){
      servo.write(command);
    }

    else if ((-1 <= command) && (command <= 1)){
      if (command == 1){
        digitalWrite(motorpin1, LOW);
        digitalWrite(motorpin2, HIGH);
      }
      else if (command == 0){
        digitalWrite(motorpin1, LOW);
        digitalWrite(motorpin2, LOW);
      }

      else if (command == -1){
        digitalWrite(motorpin1, HIGH);
        digitalWrite(motorpin2, LOW);
      }
    }

 }
}
