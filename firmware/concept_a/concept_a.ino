// ME 2331 Project 2 - Concept A: claw + wrist flip + turntable (4 servos)
//
// One move at a time: grip -> lift -> flip -> turn 90 -> lower -> release.
// Every move eases in and out (slow - fast - slow) so the light can doesn't shake loose.
// Single file, only the built-in Servo library: pastes straight into Tinkercad or Wokwi.
//
// Wiring (see docs/tinkercad_concept_a.md):
//   D9  turntable servo      D10 lift servo       D6 wrist servo     D5 gripper servo
//   D4  start button to GND  D13 LED (+220 ohm)   D11 IR sensor OUT (optional, LOW = can)
//   A0  FSR divider (optional: 5V - FSR - A0 - 10k - GND)
// Real robot: power the servos from their own 5-6 V supply, grounds joined to the Uno.
//
// Button: press to run. After DONE, take the can away, then press again to go home.
// (Going home with the can still there would knock it over: the open arms are on both sides.)

#include <Servo.h>

// ---------- Options ----------
#define USE_IR_SENSOR 0     // 1 = check a can is in the arms before starting
#define USE_FSR       0     // 1 = stop closing when the force sensor says "held"
#define PRINT_ANGLES  0     // 1 = print the 4 servo angles (open the Serial Plotter to see the smooth moves)

// ---------- Servo angles (degrees). Find the real values by testing. ----------
const int TURN_START  = 135;   // arm pointing at the start spot
const int TURN_TARGET = 45;    // 90 degrees later, pointing at the target spot
const int LIFT_DOWN   = 30;    // gripper at can mid-height (2.35 in)
const int LIFT_UP     = 75;    // about 0.6 in higher
const int WRIST_UP    = 0;     // can upright
const int WRIST_FLIP  = 180;   // can upside down (real angle, see WRIST_RANGE)
const int GRIP_OPEN   = 20;
const int GRIP_CLOSED = 95;    // just past where the pads touch the can
const int GRIP_RELEASE = 70;   // at the target the gripper is upside down: open only ~25 deg so the
                               // arms clear the can but don't swing down into the base (CAD check)
const int WRIST_RANGE = 180;   // set to 270 if the wrist is a 270-degree servo

// ---------- Move times (ms) ----------
const unsigned long T_GRIP = 800, T_LIFT = 1000, T_FLIP = 1500, T_TURN = 1500, T_RELEASE = 600;

// ---------- Optional sensors ----------
const int FSR_HELD = 300;      // analogRead value that means "can is held" (calibrate)
const int FSR_LOST = 120;      // below this while moving = can slipped

// ---------- Pins ----------
const int PIN_TURN = 9, PIN_LIFT = 10, PIN_WRIST = 6, PIN_GRIP = 5;
const int PIN_BUTTON = 4, PIN_LED = 13, PIN_IR = 11, PIN_FSR = A0;

Servo turnServo, liftServo, wristServo, gripServo;

struct Pose { int turn, lift, wrist, grip; };
Pose makePose(int turn, int lift, int wrist, int grip) { Pose p; p.turn = turn; p.lift = lift; p.wrist = wrist; p.grip = grip; return p; }

// The run, one move per step. Each row = where every servo should be at the END of the step.
struct Step { const char* name; Pose to; unsigned long ms; };
Pose gripAngle = {0, 0, 0, GRIP_CLOSED};   // grip angle can be shortened by the FSR

Step RUN[] = {
  {"GRIP",    {TURN_START,  LIFT_DOWN, WRIST_UP,   GRIP_CLOSED}, T_GRIP},
  {"LIFT",    {TURN_START,  LIFT_UP,   WRIST_UP,   GRIP_CLOSED}, T_LIFT},
  {"FLIP",    {TURN_START,  LIFT_UP,   WRIST_FLIP, GRIP_CLOSED}, T_FLIP},
  {"TURN",    {TURN_TARGET, LIFT_UP,   WRIST_FLIP, GRIP_CLOSED}, T_TURN},
  {"LOWER",   {TURN_TARGET, LIFT_DOWN, WRIST_FLIP, GRIP_CLOSED}, T_LIFT},
  {"RELEASE", {TURN_TARGET, LIFT_DOWN, WRIST_FLIP, GRIP_RELEASE}, T_RELEASE},
};
const int RUN_STEPS = sizeof(RUN) / sizeof(RUN[0]);

// Going home (only after the can is removed): lift, close the arms (open arms would hit the
// table while un-flipping), straighten the wrist, turn back, lower, open. Order checked in CAD.
Step HOMING[] = {
  {"H-LIFT",  {TURN_TARGET, LIFT_UP,   WRIST_FLIP, GRIP_RELEASE}, T_LIFT},
  {"H-CLOSE", {TURN_TARGET, LIFT_UP,   WRIST_FLIP, GRIP_CLOSED},  T_GRIP},
  {"H-WRIST", {TURN_TARGET, LIFT_UP,   WRIST_UP,   GRIP_CLOSED},  T_FLIP},
  {"H-TURN",  {TURN_START,  LIFT_UP,   WRIST_UP,   GRIP_CLOSED},  T_TURN},
  {"H-LOWER", {TURN_START,  LIFT_DOWN, WRIST_UP,   GRIP_CLOSED},  T_LIFT},
  {"H-OPEN",  {TURN_START,  LIFT_DOWN, WRIST_UP,   GRIP_OPEN},    T_GRIP},
};
const int HOME_STEPS = sizeof(HOMING) / sizeof(HOMING[0]);

enum Mode { IDLE, RUNNING, DONE, RETURNING, FAULT };
Mode mode = IDLE;
Step* steps = RUN;
int stepCount = RUN_STEPS, stepIndex = 0;
Pose now, from;
unsigned long stepStart = 0;

// ---------- helpers ----------
float ease(float s) {                      // slow - fast - slow (minimum-jerk curve)
  if (s <= 0) return 0;
  if (s >= 1) return 1;
  return s * s * s * (10 - 15 * s + 6 * s * s);
}

int blend(int a, int b, float e) { return a + (int)((b - a) * e + (b > a ? 0.5 : -0.5)); }

void writePose(const Pose& p) {
  turnServo.write(p.turn);
  liftServo.write(p.lift);
  wristServo.write((long)p.wrist * 180 / WRIST_RANGE);   // 270-degree servo: 180 real = 120 command
  gripServo.write(p.grip);
}

bool buttonPressed() {                     // true once per press (debounced)
  static bool last = false;
  static unsigned long changed = 0;
  bool down = digitalRead(PIN_BUTTON) == LOW;
  if (down != last && millis() - changed > 40) { last = down; changed = millis(); return down; }
  return false;
}

void startSteps(Step* list, int count, Mode m) {
  steps = list; stepCount = count; stepIndex = 0;
  from = now; stepStart = millis(); mode = m;
  Serial.print(F("> ")); Serial.println(steps[0].name);
}

void fault(const __FlashStringHelper* why) {
  mode = FAULT;                            // freeze where we are: opening mid-air would drop the can
  Serial.print(F("FAULT: ")); Serial.println(why);
}

// ---------- setup / loop ----------
void setup() {
  Serial.begin(9600);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_IR, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  now = makePose(TURN_START, LIFT_DOWN, WRIST_UP, GRIP_OPEN);
  writePose(now);                          // set the angle before attach so nothing jumps
  turnServo.attach(PIN_TURN);
  liftServo.attach(PIN_LIFT);
  wristServo.attach(PIN_WRIST);
  gripServo.attach(PIN_GRIP);
  writePose(now);
  Serial.println(F("Concept A ready. Press the button to start."));
}

void loop() {
  bool pressed = buttonPressed();
#ifdef AUTO_START
  static bool autoDone = false;            // headless test only: press once after 1 s
  if (!autoDone && millis() > 1000) { pressed = true; autoDone = true; }
#endif

  // LED: off = idle, slow blink = moving, on = done, fast blink = fault
  unsigned long t = millis();
  digitalWrite(PIN_LED, mode == DONE ? HIGH : mode == FAULT ? (t / 100) % 2 : (mode == IDLE ? LOW : (t / 400) % 2));

  switch (mode) {
    case IDLE:
      if (pressed) {
        if (USE_IR_SENSOR && digitalRead(PIN_IR) != LOW) { Serial.println(F("No can in the arms.")); break; }
        startSteps(RUN, RUN_STEPS, RUNNING);
      }
      break;

    case DONE:
      if (pressed) { Serial.println(F("Going home (can should be removed).")); startSteps(HOMING, HOME_STEPS, RETURNING); }
      break;

    case FAULT:
      if (pressed) { Serial.println(F("Reset: remove the can, going home.")); startSteps(HOMING, HOME_STEPS, RETURNING); }
      break;

    case RUNNING:
    case RETURNING: {
      Step& st = steps[stepIndex];
      Pose to = st.to;
      if (mode == RUNNING && to.grip == GRIP_CLOSED) to.grip = gripAngle.grip;   // FSR may stop the grip early
      float e = ease((float)(millis() - stepStart) / st.ms);
      now = makePose(blend(from.turn, to.turn, e), blend(from.lift, to.lift, e),
                     blend(from.wrist, to.wrist, e), blend(from.grip, to.grip, e));

      if (USE_FSR && mode == RUNNING) {
        int f = analogRead(PIN_FSR);
        if (stepIndex == 0 && f >= FSR_HELD) {           // held firmly: stop closing here
          gripAngle.grip = now.grip; to.grip = now.grip; e = 1;
        }
        if (stepIndex >= 1 && stepIndex <= 4 && f < FSR_LOST) { fault(F("can slipped")); break; }
      }
      writePose(now);
#if PRINT_ANGLES
      Serial.print(now.turn); Serial.print(' '); Serial.print(now.lift); Serial.print(' ');
      Serial.print(now.wrist); Serial.print(' '); Serial.println(now.grip);
#endif

      if (e >= 1) {                                      // step finished
        from = to; now = to;
        if (++stepIndex >= stepCount) {
          mode = (mode == RUNNING) ? DONE : IDLE;
          Serial.println(mode == DONE ? F("DONE: can is upside down at the target.") : F("Home."));
        } else {
          stepStart = millis();
          Serial.print(F("> ")); Serial.println(steps[stepIndex].name);
        }
      }
      break;
    }
  }
  delay(10);   // ~100 updates per second is plenty for hobby servos
}
