// Controller building blocks. Plain C++ (no Arduino.h) so the host test in
// firmware/host_test compiles exactly the same code the Uno runs.
#pragma once
#include <math.h>

#include "config.h"

static inline float clampf(float x, float lo, float hi) { return x < lo ? lo : (x > hi ? hi : x); }

// Discrete PID with feedforward, derivative on (ref_rate - measured rate) and
// conditional-integration anti-windup. See sim/flip_control.py for the rationale.
struct Pid {
  float kp, ki, kd, i_lim, out_lim;
  float integ = 0.0f;
  float prev_meas = 0.0f;
  bool primed = false;

  Pid(float kp_, float ki_, float kd_, float i_lim_, float out_lim_)
      : kp(kp_), ki(ki_), kd(kd_), i_lim(i_lim_), out_lim(out_lim_) {}

  void reset(float meas) {
    integ = 0.0f;
    prev_meas = meas;
    primed = true;
  }

  float update(float ref, float meas, float ff, float ref_rate, float dt) {
    const float e = ref - meas;
    const float rate = primed ? (meas - prev_meas) / dt : 0.0f;
    prev_meas = meas;
    primed = true;
    const float u = ff + kp * e + integ + kd * (ref_rate - rate);
    if (fabsf(u) < out_lim || ((u > 0) != (e > 0))) {
      integ = clampf(integ + ki * e * dt, -i_lim, i_lim);
    }
    return clampf(u, -out_lim, out_lim);
  }
};

// Minimum-jerk (quintic) profile: zero velocity and acceleration at both ends,
// so the can arrives at the table moving (nearly) straight down at ~0 speed.
struct Quintic {
  float th0 = 0, th1 = 0, T = 1;
  void start(float from, float to, float dur) { th0 = from; th1 = to; T = dur; }
  void eval(float t, float& pos, float& vel, float& acc) const {
    const float s = clampf(t / T, 0.0f, 1.0f);
    const float d = th1 - th0;
    const float s2 = s * s, s3 = s2 * s;
    pos = th0 + d * (10 * s3 - 15 * s3 * s + 6 * s3 * s2);
    vel = d * (30 * s2 - 60 * s3 + 30 * s2 * s2) / T;
    acc = d * (60 * s - 180 * s2 + 120 * s3) / (T * T);
  }
};

// Model-based feedforward voltage for the flip motor (nominal parameters).
static inline float flipFeedforward(float pos, float vel, float acc, float g_mr) {
  float tau = J_FLIP * acc + B_VISC * vel + g_mr * cosf(pos);
  if (fabsf(vel) > 1e-3f) tau += (vel > 0 ? T_COULOMB : -T_COULOMB);
  return tau / KT;
}

// FSR 402 through a 10k pull-down. Nominal curve F/(F+1) = adc/1023;
// replace with a fit to bench calibration weights.
static inline float fsrAdcToNewtons(int adc) {
  if (adc <= 2) return 0.0f;
  const float r = adc / 1023.0f;
  return r / fmaxf(1e-3f, 1.0f - r);
}

// Outer force loop that trims a position servo's command (velocity-form PI).
struct GripForceLoop {
  float prev_err = 0.0f;
  bool primed = false;
  void reset() { primed = false; }
  float update(float cmd_deg, float f_set, float f_meas, float dt) {
    const float e = f_set - f_meas;
    const float de = primed ? e - prev_err : 0.0f;
    prev_err = e;
    primed = true;
    return clampf(cmd_deg + GRIP_KI * e * dt + GRIP_KP * de, SERVO_OPEN_DEG, SERVO_MAX_DEG);
  }
};
