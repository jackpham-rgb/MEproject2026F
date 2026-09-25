// ME 2331 Project 2 - mirror-flip can robot, Arduino Uno hardware layer.
//
// All decisions live in sequencer.h / control.h (hardware-free, tested on the
// laptop by firmware/host_test). This file only:
//   * decodes the flip encoder (D2/D3 interrupts, 4x quadrature),
//   * raises a 200 Hz tick from Timer2 (the ISR only sets a flag, so analogRead,
//     Serial and the float math run in loop() and never inside an interrupt),
//   * reads sensors into Inputs, applies Outputs to the motor driver and servo,
//   * streams CSV telemetry for step-response plots.
//
// Serial (250000 baud): 'g' = start, 'r' = reset from FAULT/DONE,
//   'i' = system-ID open-loop voltage step (arm must be free to swing ~90 deg).

#include <Servo.h>

#include "config.h"
#include "sequencer.h"
#if SIM_PLANT
#include "plant_model.h"
PlantModel plant;
#endif

static volatile long enc_count = 0;
static volatile bool tick = false;
static long enc_offset = 0;
static unsigned int overruns = 0;   // control ticks missed because loop() ran > 5 ms

Servo grip_servo;
Sequencer seq;
Outputs out;

// ---- Encoder: state-table quadrature decode on both edges of A and B ----------
static volatile unsigned char enc_prev = 0;
static const signed char QDEC[16] = {0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0};

static void encoderIsr() {
  // PIND bits 2,3 = D2,D3; direct port read keeps the ISR ~2 us
  const unsigned char ab = (PIND >> 2) & 0x03;
  enc_count += QDEC[(enc_prev << 2) | ab];
  enc_prev = ab;
}

ISR(TIMER2_COMPA_vect) { tick = true; }

static void startControlTimer() {
  cli();
  TCCR2A = _BV(WGM21);                        // CTC
  TCCR2B = _BV(CS22) | _BV(CS21) | _BV(CS20); // clk/1024
  OCR2A = CTRL_OCR2A;
  TCNT2 = 0;
  TIMSK2 = _BV(OCIE2A);
  sei();
}

static long readEncoder() {
#if SIM_PLANT
  return plant.encoderCount();
#else
  noInterrupts();
  const long c = enc_count;
  interrupts();
  return c;
#endif
}

static void setMotorVolts(float v) {
  int pwm = (int)lroundf(fabsf(v) / V_SUPPLY * 255.0f);
  if (pwm > 255) pwm = 255;
  digitalWrite(PIN_MOT_IN1, v > 0 ? HIGH : LOW);
  digitalWrite(PIN_MOT_IN2, v < 0 ? HIGH : LOW);
  analogWrite(PIN_MOT_PWM, pwm);
}

static void setServoDeg(float deg) {
  const int us = SERVO_US_MIN + (int)lroundf(deg / 180.0f * (SERVO_US_MAX - SERVO_US_MIN));
  grip_servo.writeMicroseconds(us);   // ~0.18 deg resolution vs 1 deg for write()
}

static bool pingCan() {
#if SIM_PLANT
  return plant.canSeen();
#else
  digitalWrite(PIN_US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_US_TRIG, LOW);
  const unsigned long echo = pulseIn(PIN_US_ECHO, HIGH, US_TIMEOUT_US);  // <= 3 ms, only in DETECT
  const float cm = echo * 0.01715f;
  return echo > 0 && cm > US_MIN_CM && cm < US_MAX_CM;
#endif
}

static bool startPressed() {
  static bool prev = false;
  static unsigned char stable = 0;
  const bool raw = digitalRead(PIN_START) == LOW;
  stable = raw ? (stable < 10 ? stable + 1 : 10) : 0;   // 10 ticks = 50 ms debounce
  const bool pressed = stable >= 10;
  const bool edge = pressed && !prev;
  prev = pressed;
  return edge;
}

// Open-loop voltage step for system ID: logs theta at 200 Hz for 0.6 s.
// Fit K and tau of K/(s(tau s+1)) to the velocity curve, then rerun sim/flip_control.py.
static void systemIdStep(float volts) {
  Serial.println(F("# sysid t_ms,count"));
  const long c0 = readEncoder();
  const unsigned long t0 = millis();
  for (int k = 0; k < 120; ++k) {
    while (!tick) {}
    tick = false;
    setMotorVolts(volts);
    Serial.print(millis() - t0);
    Serial.print(',');
    Serial.println(readEncoder() - c0);
  }
  setMotorVolts(0);
  Serial.println(F("# sysid end"));
}

void setup() {
  Serial.begin(250000);
  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  pinMode(PIN_START, INPUT_PULLUP);
  pinMode(PIN_HOME, INPUT_PULLUP);
  pinMode(PIN_MOT_IN1, OUTPUT);
  pinMode(PIN_MOT_IN2, OUTPUT);
  pinMode(PIN_MOT_PWM, OUTPUT);
  pinMode(PIN_US_TRIG, OUTPUT);
  pinMode(PIN_US_ECHO, INPUT);
  pinMode(PIN_LED, OUTPUT);
  setMotorVolts(0);
  grip_servo.attach(PIN_GRIP_SERVO, SERVO_US_MIN, SERVO_US_MAX);
  setServoDeg(SERVO_OPEN_DEG);

  enc_prev = (PIND >> 2) & 0x03;
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encoderIsr, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), encoderIsr, CHANGE);
  startControlTimer();
  Serial.println(F("# t_ms,state,theta_ref_mdeg,theta_mdeg,mV,fset_mN,f_mN,servo_cdeg,fault,overruns,ctrl_us_max"));
}

void loop() {
  if (!tick) return;
  tick = false;
  static unsigned int n = 0;

  bool serial_start = false;
  while (Serial.available()) {
    const char c = Serial.read();
    if (c == 'g' || c == 'r') serial_start = true;
    if (c == 'i' && (seq.state == IDLE || seq.state == DONE)) systemIdStep(4.0f);
  }

  const unsigned long t_start = micros();
  Inputs in;
  const long count = readEncoder() - enc_offset;
  in.theta = ENC_SIGN * count * (6.2831853f / ENC_CPR);
#if SIM_PLANT
  in.force = fsrAdcToNewtons(plant.fsrAdc());
  in.home_switch = plant.homeSwitch();
#else
  in.force = fsrAdcToNewtons(analogRead(PIN_FSR));
  in.home_switch = digitalRead(PIN_HOME) == LOW;
#endif
  in.start = startPressed() || serial_start;
#if SIM_PLANT && defined(SIM_AUTOSTART)
  in.start = in.start || (seq.state == IDLE && n == 100);   // headless emulator runs (simavr)
#endif
  in.can_seen = out.want_ultrasonic ? pingCan() : false;

  const State before = seq.state;
  seq.step(in, out, DT);
  if (seq.state != before) {   // event line; '#' so CSV parsers skip it
    Serial.print(F("# ")); Serial.print(millis()); Serial.print(F(" -> "));
    Serial.print(STATE_NAMES[seq.state]);
    if (seq.state == FAULT) { Serial.print(F(" fault=")); Serial.print((int)seq.fault); }
    Serial.println();
  }
  if (seq.zero_request) {
    enc_offset = readEncoder();
    seq.zero_request = false;
  }
  setMotorVolts(out.motor_volts);
  setServoDeg(out.servo_deg);
  const unsigned int ctrl_us = micros() - t_start;   // sensing + control + actuation
  static unsigned int ctrl_us_max = 0;
  if (ctrl_us > ctrl_us_max) ctrl_us_max = ctrl_us;
#if SIM_PLANT
  plant.step(out.motor_volts, out.servo_deg, DT);   // excluded from ctrl_us; not on the robot
#endif

  // LED: blink while running, solid when DONE, fast blink on FAULT
  const bool led = seq.state == DONE ? true
                 : seq.state == FAULT ? (n & 0x10)
                 : (seq.state == IDLE ? false : (n & 0x40));
  digitalWrite(PIN_LED, led);

  if (++n % TELEMETRY_DIV == 0 && seq.state != IDLE && seq.state != DONE) {
    Serial.print(millis()); Serial.print(',');
    Serial.print(STATE_NAMES[seq.state]); Serial.print(',');
    Serial.print((long)(out.theta_ref * 57295.78f)); Serial.print(',');
    Serial.print((long)(in.theta * 57295.78f)); Serial.print(',');
    Serial.print((int)(out.motor_volts * 1000)); Serial.print(',');
    Serial.print((int)(out.force_set * 1000)); Serial.print(',');
    Serial.print((int)(in.force * 1000)); Serial.print(',');
    Serial.print((int)(out.servo_deg * 100)); Serial.print(',');
    Serial.print((int)seq.fault); Serial.print(',');
    Serial.print(overruns); Serial.print(',');
    Serial.println(ctrl_us_max);
    ctrl_us_max = 0;
  }
  if (tick) ++overruns;
}
