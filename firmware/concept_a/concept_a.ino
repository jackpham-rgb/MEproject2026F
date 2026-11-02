// ME 2331 Project 2 - Concept A: claw + wrist flip + turntable (4 servos)
//
// One move at a time: grip -> lift -> flip -> turn 90 -> lower -> release.
// Every move eases in and out (slow - fast - slow) so the light can doesn't shake loose.
// Single file, only the built-in Servo library: pastes straight into Tinkercad or Wokwi.
//
// Wiring (see docs/tinkercad_concept_a.md):
//   D9  turntable servo      D10 lift servo       D6 wrist servo     D5 gripper servo
//   D4  start button to GND  D13 LED (+220 ohm)
// Real robot: 12 V adapter -> Uno VIN, and -> XL4015 buck at 5.8 V -> servo rail (docs/04_wiring.md, EE/).
//
// Button: press to run. After DONE, take the can away, then press again to go home.
// (Going home with the can still there would knock it over: the open arms are on both sides.)

#include <Servo.h>

// ---------- Debug ----------
#define PRINT_ANGLES  0     // 1 = print the 4 servo angles (open the Serial Plotter to see the smooth moves)

// ---------- Servo angles (degrees). Find the real values by testing. ----------
const int TURN_START  = 135;   // arm pointing at the start spot
const int TURN_TARGET = 45;    // 90 degrees later, pointing at the target spot
const int LIFT_DOWN   = 30;    // gripper at can mid-height (2.41 in, Coke can)
const int LIFT_UP     = 75;    // about 0.6 in higher
const int WRIST_UP    = 0;     // can upright
const int WRIST_FLIP  = 180;   // can upside down
const int GRIP_OPEN   = 20;
const int GRIP_CLOSED = 95;    // just past where the pads touch the can
const int GRIP_RELEASE = 70;   // at the target the gripper is upside down: open only ~25 deg so the
                               // arms clear the can but don't swing down into the base (CAD check)

// ---------- Move times (ms) ----------
const unsigned long ATTACH_GAP_MS = 300;
const unsigned long T_GRIP = 800, T_LIFT = 1000, T_FLIP = 1500, T_TURN = 1500, T_RELEASE = 600;

// ---------- Pins ----------
const int PIN_TURN = 9, PIN_LIFT = 10, PIN_WRIST = 6, PIN_GRIP = 5;
const int PIN_BUTTON = 4, PIN_LED = 13;
// The wrist needs a full 180 deg: a wider pulse range (500-2500 us) lets an MG90S reach it.
const int WRIST_MIN_US = 500, WRIST_MAX_US = 2500;

Servo turnServo, liftServo, wristServo, gripServo;

struct Pose { int turn, lift, wrist, grip; };
Pose makePose(int turn, int lift, int wrist, int grip) { Pose p; p.turn = turn; p.lift = lift; p.wrist = wrist; p.grip = grip; return p; }

// The run, one move per step. Each row = where every servo should be at the END of the step.
struct Step { const char* name; Pose to; unsigned long ms; };

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

enum Mode { IDLE, RUNNING, DONE, RETURNING };
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
  wristServo.write(p.wrist);
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

// ---------- setup / loop ----------
void setup() {
  Serial.begin(9600);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  now = makePose(TURN_START, LIFT_DOWN, WRIST_UP, GRIP_OPEN);
  writePose(now);                          // set the angle before attach so nothing jumps
  // Attach one servo at a time: if the robot was left away from home, only one servo jumps
  // (and pulls stall current) at once, not all 4 (4.8 A). See EE/README.md.
  turnServo.attach(PIN_TURN);                                  delay(ATTACH_GAP_MS);
  liftServo.attach(PIN_LIFT);                                  delay(ATTACH_GAP_MS);
  wristServo.attach(PIN_WRIST, WRIST_MIN_US, WRIST_MAX_US);    delay(ATTACH_GAP_MS);
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

  // LED: off = idle, blinking = moving, on = done
  unsigned long t = millis();
  digitalWrite(PIN_LED, mode == DONE ? HIGH : (mode == IDLE ? LOW : (t / 400) % 2));

  switch (mode) {
    case IDLE:
      if (pressed) startSteps(RUN, RUN_STEPS, RUNNING);
      break;

    case DONE:
      if (pressed) { Serial.println(F("Going home (can should be removed).")); startSteps(HOMING, HOME_STEPS, RETURNING); }
      break;

    case RUNNING:
    case RETURNING: {
      Step& st = steps[stepIndex];
      Pose to = st.to;
      float e = ease((float)(millis() - stepStart) / st.ms);
      now = makePose(blend(from.turn, to.turn, e), blend(from.lift, to.lift, e),
                     blend(from.wrist, to.wrist, e), blend(from.grip, to.grip, e));

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
