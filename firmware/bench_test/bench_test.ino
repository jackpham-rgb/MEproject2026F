// ME 2331 Project 2 - Concept A: electronics bench test (before anything is screwed together).
//
// Wire everything on the table first (docs/13_electronics_bench_test.md), servos loose, no horns.
// Works with or without the Serial Monitor (9600 baud): the button and the LED drive it.
//
//   power up          LED blinks 3 times = Uno alive, sketch running
//   press START       LED on while pressed (button + pull-up OK), then the next test runs:
//     1  SG90  gripper  (D5)  home 20 deg, wiggle +-10 deg, back
//     2  MG90S wrist    (D6)  home 0 deg,  wiggle 0..20 deg, then the full 0..180 (checks it reaches 180)
//     3  MG90S lift     (D10) home 30 deg, wiggle +-10 deg
//     4  MG996R turn    (D9)  home 135 deg, wiggle +-10 deg
//     5  all four together at HOME, held 5 s (rail sag test: meter on the rail, should stay > 5.5 V)
//   then it starts again at 1.
// Only the servo under test is attached; the others get no pulse (so a bad one is easy to spot).

#include <Servo.h>

const int PIN_TURN = 9, PIN_LIFT = 10, PIN_WRIST = 6, PIN_GRIP = 5;
const int PIN_BUTTON = 4, PIN_LED = 13;
const int WRIST_MIN_US = 500, WRIST_MAX_US = 2500;

struct Unit { const char *name; int pin; int home; int lo; int hi; };
const Unit U[4] = {
  {"SG90 gripper (D5)", PIN_GRIP, 20, 10, 30},
  {"MG90S wrist (D6)", PIN_WRIST, 0, 0, 20},
  {"MG90S lift (D10)", PIN_LIFT, 30, 20, 40},
  {"MG996R turntable (D9)", PIN_TURN, 135, 125, 145},
};
Servo sv;
Servo all[4];
int test = 0;

void blink(int n, int ms) {
  for (int i = 0; i < n; i++) { digitalWrite(PIN_LED, HIGH); delay(ms); digitalWrite(PIN_LED, LOW); delay(ms); }
}

void attachOne(int i) {
  if (i == 1) sv.attach(U[i].pin, WRIST_MIN_US, WRIST_MAX_US);
  else sv.attach(U[i].pin);
}

void sweep(int from, int to) {                        // 1 deg every 15 ms
  int a = from;
  while (a != to) { a += (to > a) ? 1 : -1; sv.write(a); delay(15); }
}

void waitPress() {
  while (digitalRead(PIN_BUTTON) == HIGH) delay(5);
  digitalWrite(PIN_LED, HIGH);
  delay(30);
  while (digitalRead(PIN_BUTTON) == LOW) delay(5);
  digitalWrite(PIN_LED, LOW);
}

void setup() {
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  Serial.begin(9600);
  blink(3, 200);
  Serial.println(F("Concept A bench test. Press START for the next test."));
}

void loop() {
  if (test < 4) {
    const Unit &u = U[test];
    Serial.print(F("Test ")); Serial.print(test + 1); Serial.print(F(": ")); Serial.print(u.name);
    Serial.println(F("  -> press START"));
    waitPress();
    sv.write(u.home);                                // set before attach: no jump
    attachOne(test);
    delay(600);
    sweep(u.home, u.hi); sweep(u.hi, u.lo); sweep(u.lo, u.home);
    if (test == 1) {                                 // the wrist must really reach 180
      Serial.println(F("  wrist full turn 0 -> 180 -> 0: watch that it reaches a half-turn"));
      sweep(0, 180); delay(800); sweep(180, 0);
    }
    delay(300);
    sv.detach();
    Serial.println(F("  done. Smooth, no buzzing, no reset? -> OK"));
    blink(2, 120);
    test++;
  } else {
    Serial.println(F("Test 5: all four at HOME for 5 s (meter on the servo rail: stays above 5.5 V?)  -> press START"));
    waitPress();
    for (int i = 0; i < 4; i++) {
      all[i].write(U[i].home);
      if (i == 1) all[i].attach(U[i].pin, WRIST_MIN_US, WRIST_MAX_US); else all[i].attach(U[i].pin);
      delay(300);                                    // staggered, like the main sketch
    }
    delay(5000);
    for (int i = 0; i < 4; i++) all[i].detach();
    Serial.println(F("  done. All tests passed if nothing reset or buzzed. Starting again."));
    blink(5, 100);
    test = 0;
  }
}
