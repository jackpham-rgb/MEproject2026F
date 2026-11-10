// ME 2331 Project 2 - Concept A: claw + wrist flip + turntable (4 servos)
//
// One move at a time: grip -> lift -> flip -> turn 90 -> lower -> release.
// Every move eases in and out (slow - fast - slow) so the light can doesn't shake loose.
// Single file, only the built-in Servo library: pastes straight into Tinkercad or Wokwi.
//
// Wiring (see docs/tinkercad_concept_a.md):
//   D9  turntable servo      D10 lift servo       D6 wrist servo     D5 gripper servo
//   D4  start button to GND  D13 LED (+220 ohm)
// Real robot: Uno on its own 9 V battery; 12 V adapter -> XL4015 buck at 5.8 V -> servos only (docs/04_wiring.md, EE/).
//
// Button: press to run. After DONE, take the can away, then press again to go home.
// (Going home with the can still there would knock it over: the open arms are on both sides.)
//
// Laptop control (USB, 9600 baud, one command per line; viewer/control_panel.html does this for you):
//   s            same as pressing START (run, or go home after DONE)
//   t 135        move one servo to an angle, eased: t = turntable, l = lift, w = wrist, g = gripper
//   h            go to the HOME pose safely, one servo at a time (lift up, wrist, turn, open, lift down)
//   x            stop: hold where it is
//   ?            print the status line
//   c            print the calibration constants and the laptop-move limits ("= NAME value ..." line)
// The Uno reports "@ MODE STEP turn lift wrist grip" while moving and after every change.

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
const unsigned long T_GRIP = 800, T_LIFT = 1000, T_FLIP = 1500, T_TURN = 2500, T_RELEASE = 600;   // turn slowed: 1.5 -> 2.5 s

// ---------- Pins ----------
const int PIN_TURN = 9, PIN_LIFT = 10, PIN_WRIST = 6, PIN_GRIP = 5;
const int PIN_BUTTON = 4, PIN_LED = 13;
// The wrist needs a full 180 deg: a wider pulse range (500-2500 us) lets an MG90S reach it.
const int WRIST_MIN_US = 500, WRIST_MAX_US = 2500;
const int SERVO_MIN_US = 544, SERVO_MAX_US = 2400;   // Servo library defaults (the other three servos)
// Laptop moves: ms per degree. The base carries the whole arm, so it moves slower (90 deg in ~1.6 s).
const unsigned long MS_PER_DEG[4] = {18, 8, 8, 8};   // turn, lift, wrist, grip

Servo turnServo, liftServo, wristServo, gripServo;

// All types first, before any function: the Arduino IDE writes a prototype for every function and puts
// them above the first function in the file, so a type used in a function header must already exist there.
struct Pose { int turn, lift, wrist, grip; };
struct Step { const char* name; Pose to; unsigned long ms; };   // one move: where every servo is at the END
enum Mode { IDLE, RUNNING, DONE, RETURNING, MANUAL };   // MANUAL = moves asked for from the laptop

Pose makePose(int turn, int lift, int wrist, int grip) { Pose p; p.turn = turn; p.lift = lift; p.wrist = wrist; p.grip = grip; return p; }

// The run, one move per step. Each row = where every servo should be at the END of the step.
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

Mode mode = IDLE;
Step* steps = RUN;
int stepCount = RUN_STEPS, stepIndex = 0;
Pose now, from;
unsigned long stepStart = 0;
Mode afterManual = IDLE;                   // where a laptop move returns to
Step manualSteps[5];                       // built on the fly for laptop moves
// Laptop moves stay inside these angles (a bit past the working angles, not the servo's full travel)
const int LIM[4][2] = {{TURN_TARGET - 10, TURN_START + 10}, {LIFT_DOWN - 5, LIFT_UP + 5}, {0, 180}, {GRIP_OPEN - 10, GRIP_CLOSED + 5}};

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

// During a move: send the in-between angle in microseconds (~10 us per degree) instead of whole degrees,
// so slow moves glide instead of stepping 1 degree at a time.
int usFor(float deg, int lo, int hi) { return lo + (int)((hi - lo) * deg / 180.0 + 0.5); }
float mix(int a, int b, float e) { return a + (b - a) * e; }

void writeSmooth(const Pose& a, const Pose& b, float e) {
  turnServo.writeMicroseconds(usFor(mix(a.turn, b.turn, e), SERVO_MIN_US, SERVO_MAX_US));
  liftServo.writeMicroseconds(usFor(mix(a.lift, b.lift, e), SERVO_MIN_US, SERVO_MAX_US));
  wristServo.writeMicroseconds(usFor(mix(a.wrist, b.wrist, e), WRIST_MIN_US, WRIST_MAX_US));
  gripServo.writeMicroseconds(usFor(mix(a.grip, b.grip, e), SERVO_MIN_US, SERVO_MAX_US));
}

bool buttonPressed() {                     // true once per press (debounced)
  static bool last = false;
  static unsigned long changed = 0;
  bool down = digitalRead(PIN_BUTTON) == LOW;
  if (down != last && millis() - changed > 40) { last = down; changed = millis(); return down; }
  return false;
}

const char* modeName(Mode m) {
  switch (m) { case RUNNING: return "RUNNING"; case DONE: return "DONE"; case RETURNING: return "RETURNING"; case MANUAL: return "MANUAL"; default: return "IDLE"; }
}

void status() {                            // one line the laptop page reads
  Serial.print(F("@ ")); Serial.print(modeName(mode)); Serial.print(' ');
  Serial.print((mode == IDLE || mode == DONE) ? "-" : steps[stepIndex].name); Serial.print(' ');
  Serial.print(now.turn); Serial.print(' '); Serial.print(now.lift); Serial.print(' ');
  Serial.print(now.wrist); Serial.print(' '); Serial.println(now.grip);
}

void config() {                            // calibration constants + move limits, for the laptop page
  Serial.print(F("= TURN_START ")); Serial.print(TURN_START); Serial.print(F(" TURN_TARGET ")); Serial.print(TURN_TARGET);
  Serial.print(F(" LIFT_DOWN ")); Serial.print(LIFT_DOWN); Serial.print(F(" LIFT_UP ")); Serial.print(LIFT_UP);
  Serial.print(F(" WRIST_UP ")); Serial.print(WRIST_UP); Serial.print(F(" WRIST_FLIP ")); Serial.print(WRIST_FLIP);
  Serial.print(F(" GRIP_OPEN ")); Serial.print(GRIP_OPEN); Serial.print(F(" GRIP_CLOSED ")); Serial.print(GRIP_CLOSED);
  Serial.print(F(" GRIP_RELEASE ")); Serial.print(GRIP_RELEASE);
  const char* k = "tlwg";
  for (int i = 0; i < 4; i++) { Serial.print(F(" LIM_")); Serial.print(k[i]); Serial.print(' '); Serial.print(LIM[i][0]); Serial.print(' '); Serial.print(LIM[i][1]); }
  Serial.println();
}

void startSteps(Step* list, int count, Mode m) {
  steps = list; stepCount = count; stepIndex = 0;
  from = now; stepStart = millis(); mode = m;
  Serial.print(F("> ")); Serial.println(steps[0].name);
  status();
}

unsigned long moveMs(int i, int a, int b) {   // MS_PER_DEG for that servo, at least 300 ms: gentle
  unsigned long d = (unsigned long)abs(b - a) * MS_PER_DEG[i];
  return d < 300 ? 300 : d;
}

int clampAngle(int i, int a) { return a < LIM[i][0] ? LIM[i][0] : (a > LIM[i][1] ? LIM[i][1] : a); }

bool atHome() {
  return now.turn == TURN_START && now.lift == LIFT_DOWN && now.wrist == WRIST_UP && now.grip == GRIP_OPEN;
}

// START (button or laptop): run from HOME; after DONE, go home. From anywhere else it refuses,
// because the first step would move several servos at once from an unknown pose.
void pressStart() {
  if (mode == IDLE) {
    if (atHome()) startSteps(RUN, RUN_STEPS, RUNNING);
    else Serial.println(F("Not at HOME: send h (or use the HOME button) first."));
  } else if (mode == DONE) {
    Serial.println(F("Going home (can should be removed).")); startSteps(HOMING, HOME_STEPS, RETURNING);
  } else Serial.println(F("Busy: wait, or x to stop."));
}

// ---------- laptop commands ----------
void command(char c, int value, bool hasValue) {
  bool busy = (mode == RUNNING || mode == RETURNING || mode == MANUAL);
  if (c == '?') { status(); return; }
  if (c == 'c') { config(); return; }
  if (c == 'x') {                          // stop and hold where it is
    mode = IDLE;
    Serial.println(F("Stopped. Send h (home) before starting again.")); status(); return;
  }
  if (c == 's') { pressStart(); return; }  // same as the button
  if (busy) { Serial.println(F("Busy: wait, or x to stop.")); return; }
  afterManual = IDLE;                      // after a laptop move: IDLE (START then needs HOME)
  if (c == 'h') {                          // HOME, one servo at a time
    Pose p = now; int n = 0;
    p.lift = LIFT_UP;     manualSteps[n].name = "M-LIFT";  manualSteps[n].to = p; manualSteps[n++].ms = moveMs(1, now.lift, LIFT_UP);
    p.wrist = WRIST_UP;   manualSteps[n].name = "M-WRIST"; manualSteps[n].to = p; manualSteps[n++].ms = moveMs(2, now.wrist, WRIST_UP);
    p.turn = TURN_START;  manualSteps[n].name = "M-TURN";  manualSteps[n].to = p; manualSteps[n++].ms = moveMs(0, now.turn, TURN_START);
    p.grip = GRIP_OPEN;   manualSteps[n].name = "M-GRIP";  manualSteps[n].to = p; manualSteps[n++].ms = moveMs(3, now.grip, GRIP_OPEN);
    p.lift = LIFT_DOWN;   manualSteps[n].name = "M-LOWER"; manualSteps[n].to = p; manualSteps[n++].ms = moveMs(1, LIFT_UP, LIFT_DOWN);
    startSteps(manualSteps, n, MANUAL);
    return;
  }
  const char* names = "tlwg";
  const char* p = strchr(names, c);
  if (!p || !hasValue) { Serial.println(F("? commands: s, t/l/w/g <angle>, h, x, ?, c")); return; }
  int i = p - names;
  Pose to = now;
  int a = clampAngle(i, value);
  int* field = (i == 0) ? &to.turn : (i == 1) ? &to.lift : (i == 2) ? &to.wrist : &to.grip;
  int was = *field; *field = a;
  manualSteps[0].name = (i == 0) ? "M-TURN" : (i == 1) ? "M-LIFT" : (i == 2) ? "M-WRIST" : "M-GRIP";
  manualSteps[0].to = to; manualSteps[0].ms = moveMs(i, was, a);
  if (a != value) { Serial.print(F("limited to ")); Serial.println(a); }
  startSteps(manualSteps, 1, MANUAL);
}

void readSerial() {                        // "t 135\n" style lines, no String class
  static char buf[16]; static byte len = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      buf[len] = 0; len = 0;
      char* q = buf; while (*q == ' ') q++;
      if (!*q) continue;
      char c = *q++;
      while (*q == ' ') q++;
      bool hasValue = (*q >= '0' && *q <= '9') || *q == '-';
      command(c, hasValue ? atoi(q) : 0, hasValue);
    } else if (len < sizeof(buf) - 1) buf[len++] = ch;
  }
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
  Serial.println(F("Concept A ready. Press the button (or send s) to start."));
  config();
  status();
}

void loop() {
  bool pressed = buttonPressed();
  readSerial();
#ifdef AUTO_START
  static bool autoDone = false;            // headless test only: press once after 1 s
  if (!autoDone && millis() > 1000) { pressed = true; autoDone = true; }
#endif

  // LED: off = idle, blinking = moving, on = done
  unsigned long t = millis();
  digitalWrite(PIN_LED, mode == DONE ? HIGH : (mode == IDLE ? LOW : (t / 400) % 2));
  static unsigned long lastReport = 0;     // live angles for the laptop page while moving
  if ((mode == RUNNING || mode == RETURNING || mode == MANUAL) && t - lastReport >= 100) { lastReport = t; status(); }

  switch (mode) {
    case IDLE:
    case DONE:
      if (pressed) pressStart();
      break;

    case MANUAL:

    case RUNNING:
    case RETURNING: {
      Step& st = steps[stepIndex];
      Pose to = st.to;
      float e = ease((float)(millis() - stepStart) / st.ms);
      now = makePose(blend(from.turn, to.turn, e), blend(from.lift, to.lift, e),
                     blend(from.wrist, to.wrist, e), blend(from.grip, to.grip, e));

      writeSmooth(from, to, e);                          // fine steps; "now" (whole degrees) is for the status line
#if PRINT_ANGLES
      Serial.print(now.turn); Serial.print(' '); Serial.print(now.lift); Serial.print(' ');
      Serial.print(now.wrist); Serial.print(' '); Serial.println(now.grip);
#endif

      if (e >= 1) {                                      // step finished
        from = to; now = to;
        if (++stepIndex >= stepCount) {
          if (mode == MANUAL) { mode = afterManual; Serial.println(F("Moved.")); }
          else {
            mode = (mode == RUNNING) ? DONE : IDLE;
            Serial.println(mode == DONE ? F("DONE: can is upside down at the target.") : F("Home."));
          }
          status();
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
