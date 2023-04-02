
const int sensorPin[] = {A0, A1, A2}; 
int distance[3];//array to store calculated distance from sensors 
String string;
int command;
int leftMotorpin1 = 4;
int leftMotorpin2 = 5;
int leftMotorENApin = 10;//pin to control speed of left motor
int rightMotorpin1 = 2;
int rightMotorpin2 = 3;
int rightMotorENBpin = 9;
const float MCU_VOLTAGE = 5.0;


void readDistance(int sensor){

  float volts = 0;
  int tempDistance = 0;
  int sensorValue = analogRead(sensorPin[sensor]); //read analog pin of sensor 
  volts = sensorValue * (MCU_VOLTAGE / 1024.0);
  tempDistance = 120.8* pow(volts, -1.058); // convert voltage into distance with the equation of the curve of best fit from sensor data sheet (mm)
  
  while (!    ((tempDistance >= 30) && (tempDistance <= 300)) ){
    sensorValue = analogRead(sensorPin[sensor]);
    volts = sensorValue * (MCU_VOLTAGE / 1024.0);
    tempDistance = 120.8 * pow(volts, -1.058);

    if (tempDistance > 300) { // if distance calculated is more than 30cm (outside reliable range of sensor)
    tempDistance = 500; // assign dummy value 
    break;
    }

  }
  
  distance[sensor] = tempDistance;
  
}

void setup() {
  Serial.begin(38400); //establish braud rate of serial communciation
 
// set pin mode of motors
  pinMode(leftMotorpin1, OUTPUT);
  pinMode(leftMotorpin2, OUTPUT);
  pinMode(leftMotorENApin, OUTPUT);
  pinMode(rightMotorpin1, OUTPUT);
  pinMode(rightMotorpin2, OUTPUT);
  pinMode(rightMotorENBpin, OUTPUT);

  
// while serial communciation not established, wait.
 while (!Serial) {
  ;
 }



  //physically indicates serial communication is established when LED on arduino blinks twice
  digitalWrite(LED_BUILTIN, HIGH);   
  delay(2000);                       
  digitalWrite(LED_BUILTIN, LOW);    
  delay(2000);
  digitalWrite(LED_BUILTIN, HIGH);   
  delay(2000);                       
  digitalWrite(LED_BUILTIN, LOW);   
  delay(2000);

}

void loop() {
  

  if (Serial.available()) {
    string = Serial.readStringUntil('\n');
    string.trim();
    command = string.toInt();
 

    if (command == 1550){ //read infrared distance sensor 
      readDistance(0);
      readDistance(1);
      readDistance(2);
      Serial.print(distance[0]);
      Serial.print(',');  
      Serial.print(distance[1]);
      Serial.print(',');
      Serial.println(distance[2]);
    }

    else if (command == 0){ //stop robot 
      digitalWrite(leftMotorpin1, LOW);
      digitalWrite(leftMotorpin2, LOW);
      digitalWrite(rightMotorpin1, LOW);
      digitalWrite(rightMotorpin2, LOW);
    }

    else if (command == 90){ // move forwards (90 degrees)
      analogWrite(leftMotorENApin, 255);
      analogWrite(rightMotorENBpin, 255);
      digitalWrite(leftMotorpin1, HIGH);
      digitalWrite(leftMotorpin2, LOW);
      digitalWrite(rightMotorpin1, LOW);
      digitalWrite(rightMotorpin2, HIGH);
    
    }

    else if (command == -1){ // move backwards 
      analogWrite(leftMotorENApin, 255);
      analogWrite(rightMotorENBpin, 255);
      digitalWrite(leftMotorpin1, LOW);
      digitalWrite(leftMotorpin2, HIGH);
      digitalWrite(rightMotorpin1, HIGH);
      digitalWrite(rightMotorpin2, LOW);
    
    }
    else if (command == 1){ // turn left (0 degrees) 
      analogWrite(leftMotorENApin, 0);
      analogWrite(rightMotorENBpin, 255);
      digitalWrite(rightMotorpin1, LOW);
      digitalWrite(rightMotorpin2, HIGH);
    }

    else if (command == 180){ // turn right (180 degrees) 
      analogWrite(leftMotorENApin, 255);
      analogWrite(rightMotorENBpin, 0);
      digitalWrite(leftMotorpin1, HIGH);
      digitalWrite(leftMotorpin2, LOW);
    }
    else if (command == 45){ // turn slightly left (45 degrees) 
      analogWrite(leftMotorENApin, 180);
      analogWrite(rightMotorENBpin, 255);
      digitalWrite(leftMotorpin1, HIGH);
      digitalWrite(leftMotorpin2, LOW);
      digitalWrite(rightMotorpin1, LOW);
      digitalWrite(rightMotorpin2, HIGH);
    }

    else if (command == 135){ // turn slightly right (135 degrees) 
      analogWrite(leftMotorENApin, 255);
      analogWrite(rightMotorENBpin, 180);
      digitalWrite(leftMotorpin1, HIGH);
      digitalWrite(leftMotorpin2, LOW);
      digitalWrite(rightMotorpin1, LOW);
      digitalWrite(rightMotorpin2, HIGH);
    }
 }
}
