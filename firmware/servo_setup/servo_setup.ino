// ME 2331 Project 2 - Concept A: servo setup and calibration helper.
//
// Use it while assembling (to fit each horn at the right angle) and to find the calibration
// angles for firmware/concept_a/concept_a.ino. Same pins and pulse ranges as the main sketch.
//
// Serial Monitor at 9600 baud, line ending "Newline". Commands:
//   t 135     turntable to 135 deg        l 30   lift      w 0   wrist      g 20   gripper
//   t+ / t-   nudge the turntable by 1 deg (same for l, w, g)
//   h         all servos to the HOME pose of the main sketch
//   p         print the current angles (copy them into concept_a.ino)
//   r         slow sweep test of every servo between its two working angles
//
// With the 12 V adapter plugged in, USB can stay connected (the Uno switches USB power off).

#include <Servo.h>

const int PIN_TURN = 9, PIN_LIFT = 10, PIN_WRIST = 6, PIN_GRIP = 5;
const int WRIST_MIN_US = 500, WRIST_MAX_US = 2500;

// HOME pose and working angles, same as concept_a.ino
const int TURN_START = 135, TURN_TARGET = 45, LIFT_DOWN = 30, LIFT_UP = 75;
const int WRIST_UP = 0, WRIST_FLIP = 180, GRIP_OPEN = 20, GRIP_CLOSED = 95;

Servo sv[4];
const char NAMES[4] = {'t', 'l', 'w', 'g'};
const int PINS[4] = {PIN_TURN, PIN_LIFT, PIN_WRIST, PIN_GRIP};
const int HOME_POSE[4] = {TURN_START, LIFT_DOWN, WRIST_UP, GRIP_OPEN};
const int WORK[4][2] = {{TURN_START, TURN_TARGET}, {LIFT_DOWN, LIFT_UP}, {WRIST_UP, WRIST_FLIP}, {GRIP_OPEN, GRIP_CLOSED}};
int angle[4];

void moveSlow(int i, int to) {               // 1 deg every 15 ms: gentle, nothing jumps
  while (angle[i] != to) {
    angle[i] += (to > angle[i]) ? 1 : -1;
    sv[i].write(angle[i]);
    delay(15);
  }
}

void printAngles() {
  Serial.print(F("TURN ")); Serial.print(angle[0]);
  Serial.print(F("  LIFT ")); Serial.print(angle[1]);
  Serial.print(F("  WRIST ")); Serial.print(angle[2]);
  Serial.print(F("  GRIP ")); Serial.println(angle[3]);
}

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < 4; i++) {
    angle[i] = HOME_POSE[i];
    sv[i].write(angle[i]);                    // set the angle before attach, then attach 0.3 s apart
    if (i == 2) sv[i].attach(PINS[i], WRIST_MIN_US, WRIST_MAX_US);
    else sv[i].attach(PINS[i]);
    delay(300);
  }
  Serial.println(F("Servo setup: all servos at HOME. Commands: t/l/w/g <angle>, t+ t- ..., h, p, r"));
  printAngles();
}

void loop() {
  if (!Serial.available()) return;
  String s = Serial.readStringUntil('\n');
  s.trim();
  if (s.length() == 0) return;
  char c = s.charAt(0);
  if (c == 'h') {
    for (int i = 0; i < 4; i++) moveSlow(i, HOME_POSE[i]);
  } else if (c == 'p') {
    // printed below
  } else if (c == 'r') {
    for (int i = 0; i < 4; i++) {
      Serial.print(F("sweep ")); Serial.println(NAMES[i]);
      moveSlow(i, WORK[i][1]); delay(400); moveSlow(i, WORK[i][0]); delay(400);
    }
  } else {
    for (int i = 0; i < 4; i++) {
      if (c != NAMES[i]) continue;
      int to = angle[i];
      if (s.length() >= 2 && s.charAt(1) == '+') to = angle[i] + 1;
      else if (s.length() >= 2 && s.charAt(1) == '-') to = angle[i] - 1;
      else to = s.substring(1).toInt();
      moveSlow(i, constrain(to, 0, 180));
    }
  }
  printAngles();
}
