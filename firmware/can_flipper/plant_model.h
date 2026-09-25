// Software model of the mechanism: flip gearmotor + arm + can, grip servo + pads,
// FSR divider, ultrasonic presence, home switch. A C++ port of sim/*.py used by
//   * firmware/host_test (laptop regression test of the full sequence), and
//   * SIM_PLANT=1 builds (Wokwi or a bare Uno with no mechanism attached).
// Plain C++, no Arduino.h. "True" parameters can be scaled to test robustness.
#pragma once
#include <math.h>

#include "config.h"

struct PlantModel {
  // --- scaling / fault injection ---
  float j_scale = 1.0f, fric_scale = 1.0f, grav_scale = 1.0f, pad_k_scale = 1.0f;
  bool can_placed = true, motor_dead = false, fsr_dead = false;

  // --- state ---
  float theta = 0.0f, omega = 0.0f;
  float psi = 0.0f;              // servo angle, deg
  bool can_in_jaw = false, can_released = false;
  float peak_force = 0.0f, peak_theta = 0.0f;
  unsigned long rng = 12345UL;

  static constexpr float PSI_CONTACT = 40.0f;   // deg, pads touch the can
  static constexpr float PAD_K = 800.0f;        // N/m per finger
  static constexpr float JAW_LEVER = 0.030f;    // m
  static constexpr float SERVO_RATE = 360.0f;   // deg/s loaded
  static constexpr float CAN_MR_G = 0.01323f;   // g * m_can * r_arm, N m
  static constexpr float CAN_J = 1.21e-4f;      // m_can * r_arm^2

  float force() const {
    if (!can_placed || can_released) return 0.0f;
    const float x = (psi - PSI_CONTACT) * 0.0174533f * JAW_LEVER;
    return x > 0 ? x * PAD_K * pad_k_scale : 0.0f;
  }

  // Advance by dt with motor voltage v and servo command (deg).
  void step(float v, float servo_cmd, float dt) {
#ifdef __AVR__
    const int sub = 2;    // AVR float is slow; keeps SIM_PLANT builds inside the 5 ms tick
#else
    const int sub = 20;
#endif
    const float h = dt / sub;
    for (int k = 0; k < sub; ++k) {
      // servo: first-order 20 ms lag, rate limited
      float d = (servo_cmd - psi) * fminf(1.0f, h / 0.02f);
      d = fmaxf(-SERVO_RATE * h, fminf(SERVO_RATE * h, d));
      psi += d;
      const float f = force();
      if (f > peak_force) peak_force = f;
      if (f > 0.1f) can_in_jaw = true;
      if (can_in_jaw && f < 0.05f && theta > 1.5f) can_released = true;   // opened after the flip
      const bool loaded = can_in_jaw && !can_released;

      const float j = (J_FLIP - (loaded ? 0.0f : CAN_J)) * j_scale;
      const float g_mr = (G_MR_LOADED - (loaded ? 0.0f : CAN_MR_G)) * grav_scale;
      const float kt = motor_dead ? 0.0f : KT;
      float tau = kt * v - B_VISC * omega - g_mr * cosf(theta);
      const float tc = T_COULOMB * fric_scale;
      if (fabsf(omega) < 1e-4f && fabsf(tau) <= tc) {
        omega = 0.0f;
      } else {
        tau -= tc * (fabsf(omega) >= 1e-4f ? (omega > 0 ? 1.0f : -1.0f) : (tau > 0 ? 1.0f : -1.0f));
        omega += tau / j * h;
        theta += omega * h;
      }
      if (theta < 0.0f) { theta = 0.0f; if (omega < 0) omega = 0.0f; }   // hard stop
      if (theta > peak_theta) peak_theta = theta;
    }
  }

  long encoderCount() const { return (long)floorf(theta / 6.2831853f * ENC_CPR); }
  bool homeSwitch() const { return theta < 0.0035f; }   // closes within 0.2 deg of the stop
  bool canSeen() const { return can_placed && !can_released && theta < 0.05f; }

  int fsrAdc() {
    if (fsr_dead) return 0;
    const float f = force();
    float v = f < 0.1f ? 0.0f : f / (f + 1.0f);
    rng = rng * 1103515245UL + 12345UL;
    const float noise = ((long)((rng >> 16) & 0x7) - 3.5f) * 0.4f;   // ~ +-1.5 LSB
    int adc = (int)lroundf(v * 1023.0f + noise);
    return adc < 0 ? 0 : (adc > 1023 ? 1023 : adc);
  }
};
