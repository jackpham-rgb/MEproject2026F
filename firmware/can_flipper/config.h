// Pin map, physical constants and controller gains.
// Gains/model numbers come from sim/flip_control.py and sim/grip_control.py;
// re-run those after bench system ID and copy the new values here.
#pragma once

// ---- Build options ---------------------------------------------------------
// 1 = replace the encoder/FSR/ultrasonic with the software plant in plant_model.h
//     (for Wokwi / bench runs with no mechanism attached). 0 = real hardware.
#ifndef SIM_PLANT
#define SIM_PLANT 0
#endif

// ---- Pins (Arduino Uno) ------------------------------------------------------
// D2/D3 are the only external-interrupt pins: both go to the flip encoder for 4x decoding.
#define PIN_ENC_A 2
#define PIN_ENC_B 3
#define PIN_START 4       // start button to GND (INPUT_PULLUP)
#define PIN_MOT_PWM 5     // TB6612 PWMA / L298N ENA (Timer0 PWM; Timer1 is taken by Servo, Timer2 by the control tick)
#define PIN_MOT_IN1 7
#define PIN_MOT_IN2 8
#define PIN_GRIP_SERVO 9
#define PIN_HOME 10       // home microswitch in the theta = 0 hard stop, to GND (INPUT_PULLUP)
#define PIN_US_ECHO 11
#define PIN_US_TRIG 12
#define PIN_LED 13
#define PIN_FSR A0        // FSR to 5 V, 10k to GND, junction to A0

// ---- Loop timing -------------------------------------------------------------
// Timer2 CTC, prescaler 1024, OCR2A = 77 -> 16 MHz / 1024 / 78 = 200.3 Hz
#define CTRL_OCR2A 77
static const float DT = (CTRL_OCR2A + 1) * 1024.0f / 16.0e6f;   // 4.992 ms
#define TELEMETRY_DIV 2   // CSV line every 2nd tick (100 Hz) at 250000 baud

// ---- Flip axis model (ESTIMATES - replace after system ID) ------------------------
static const float V_SUPPLY = 12.0f;
static const float ENC_CPR = 1496.0f;          // 11 PPR x 34:1 x 4
static const float ENC_SIGN = 1.0f;            // flip if +PWM counts down
static const float KT = 0.0375f;               // N m / V  (stall torque / V_supply)
static const float B_VISC = 0.0215f;           // N m s / rad (stall torque / no-load speed)
static const float J_FLIP = 8.611e-4f;         // kg m^2, loaded arm incl. reflected rotor
static const float T_COULOMB = 0.02f;          // N m
static const float G_MR_LOADED = 0.01808f;     // g * m*r unbalance with can, N m
static const float G_MR_EMPTY = 0.00485f;      // without can (after release)

// ---- Flip axis controller (pole placement, triple pole at -30 rad/s) ------------
static const float FLIP_KP = 62.0f;            // V / rad
static const float FLIP_KI = 620.0f;           // V / (rad s)
static const float FLIP_KD = 1.494f;           // V s / rad
static const float FLIP_I_LIM = 3.0f;          // V
static const float FLIP_T = 1.6f;              // s, quintic duration
static const float THETA_END = 3.13287f;       // 179.5 deg: aim short, overshoot > +0.9 deg hits the table
static const float FLIP_DONE_ERR = 0.0087f;    // 0.5 deg
static const float FLIP_DONE_W = 0.2f;         // rad/s
static const float FLIP_FAULT_ERR = 0.175f;    // 10 deg tracking error -> stall / encoder fault
static const float SEAT_VOLTS = -1.2f;         // gentle push onto the home stop

// ---- Grip axis ---------------------------------------------------------------------
static const float SERVO_OPEN_DEG = 0.0f;
static const float SERVO_MAX_DEG = 80.0f;      // fully closed on nothing -> can missing
static const float GRIP_CLOSE_RATE = 90.0f;    // deg/s before contact
static const float GRIP_F_CONTACT = 0.15f;     // N
static const float GRIP_F_SET = 1.5f;          // N per finger (slip limit 0.44 N, dent ~8 N)
static const float GRIP_F_TOL = 0.25f;         // N
static const float GRIP_F_LOST = 0.35f;        // N, below this mid-flip = can slipping out
static const float GRIP_F_MAX = 4.0f;          // N, abort before denting
static const float GRIP_KI = 25.0f;            // deg / (N s)
static const float GRIP_KP = 1.5f;             // deg / N  (on error change, velocity form)
static const int SERVO_US_MIN = 544;           // Servo library defaults, 0..180 deg
static const int SERVO_US_MAX = 2400;

// ---- Can detection (HC-SR04 at the axis foot, under the arm, aimed at the start spot) ----
// Can face is 2.34 in (5.9 cm) from the axis foot; re-centre this window once CAD fixes
// the sensor position (measure: can present vs absent).
static const float US_MIN_CM = 3.0f;
static const float US_MAX_CM = 9.0f;
#define US_TIMEOUT_US 3000UL
#define DETECT_HITS 5

// ---- Timeouts (s) ------------------------------------------------------------------
static const float T_HOME_MAX = 4.0f;
static const float T_DETECT_MAX = 3.0f;
static const float T_GRIP_MAX = 2.5f;
static const float T_GRIP_SETTLE = 0.15f;
static const float T_FLIP_SETTLE = 0.10f;
static const float T_RELEASE = 0.40f;
static const float T_SEAT_MAX = 1.0f;
