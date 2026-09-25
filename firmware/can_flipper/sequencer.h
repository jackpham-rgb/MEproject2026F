// Test-sequence state machine. Hardware-free: it consumes one Inputs sample per
// control tick and produces one Outputs command, so the host test can drive it
// against the plant model and the Uno drives it against real sensors.
//
//   HOME -> IDLE -> DETECT -> GRIP -> FLIP -> RELEASE -> RETURN -> SEAT -> DONE
//                                any state -> FAULT (motor off, jaws open)
// Every transition waits on a measured condition (force settled, angle settled,
// switch closed), never on a guessed delay; timers only exist as fault timeouts.
#pragma once
#include "config.h"
#include "control.h"

enum State : unsigned char { HOME, IDLE, DETECT, GRIP, FLIP, RELEASE, RETURN, SEAT, DONE, FAULT };

enum Fault : unsigned char {
  F_NONE, F_HOME_TIMEOUT, F_NO_CAN, F_GRIP_TIMEOUT, F_GRIP_OVERFORCE, F_GRIP_EMPTY,
  F_CAN_LOST, F_TRACKING, F_SETTLE_TIMEOUT
};

static const char* const STATE_NAMES[] = {"HOME", "IDLE", "DETECT", "GRIP", "FLIP",
                                          "RELEASE", "RETURN", "SEAT", "DONE", "FAULT"};

struct Inputs {
  float theta;        // rad, flip axis (0 = arm horizontal on home stop, can side)
  float force;        // N, grip force per finger
  bool home_switch;   // true = arm on the theta = 0 stop
  bool start;         // start button edge or serial 'g'
  bool can_seen;      // ultrasonic reading inside the start-spot window this tick
};

struct Outputs {
  float motor_volts = 0.0f;
  float servo_deg = SERVO_OPEN_DEG;
  float theta_ref = 0.0f;
  float force_set = 0.0f;
  bool want_ultrasonic = false;   // lets the Uno skip the blocking ping outside DETECT
};

class Sequencer {
 public:
  State state = HOME;
  Fault fault = F_NONE;
  float peak_theta = 0.0f;

  Sequencer() : pid_(FLIP_KP, FLIP_KI, FLIP_KD, FLIP_I_LIM, V_SUPPLY) {}

  void step(const Inputs& in, Outputs& out, float dt) {
    t_state_ += dt;
    out.want_ultrasonic = false;
    out.force_set = 0.0f;
    if (in.theta > peak_theta) peak_theta = in.theta;

    switch (state) {
      case HOME:  // drive gently onto the hard stop; the switch there defines theta = 0
        out.servo_deg = SERVO_OPEN_DEG;
        out.motor_volts = in.home_switch ? 0.0f : SEAT_VOLTS;
        if (in.home_switch) { zero_request = true; enter(IDLE); }
        else if (t_state_ > T_HOME_MAX) failWith(F_HOME_TIMEOUT);
        break;

      case IDLE:
        out.motor_volts = 0.0f;
        out.servo_deg = SERVO_OPEN_DEG;
        if (in.start) { hits_ = 0; enter(DETECT); }
        break;

      case DETECT:
        out.want_ultrasonic = true;
        hits_ = in.can_seen ? hits_ + 1 : 0;
        if (hits_ >= DETECT_HITS) { servo_cmd_ = SERVO_OPEN_DEG; contact_ = false; grip_.reset(); enter(GRIP); }
        else if (t_state_ > T_DETECT_MAX) failWith(F_NO_CAN);
        break;

      case GRIP:
        out.motor_volts = 0.0f;
        out.force_set = GRIP_F_SET;
        if (!contact_) {
          servo_cmd_ = clampf(servo_cmd_ + GRIP_CLOSE_RATE * dt, SERVO_OPEN_DEG, SERVO_MAX_DEG);
          if (in.force > GRIP_F_CONTACT) contact_ = true;
        } else {
          servo_cmd_ = grip_.update(servo_cmd_, GRIP_F_SET, in.force, dt);
        }
        out.servo_deg = servo_cmd_;
        if (in.force > GRIP_F_MAX) { failWith(F_GRIP_OVERFORCE); break; }
        if (servo_cmd_ >= SERVO_MAX_DEG && in.force < GRIP_F_CONTACT) { failWith(F_GRIP_EMPTY); break; }
        settle_ = (contact_ && fabsf(in.force - GRIP_F_SET) < GRIP_F_TOL) ? settle_ + dt : 0.0f;
        if (settle_ >= T_GRIP_SETTLE) { startMove(in.theta, THETA_END); enter(FLIP); }
        else if (t_state_ > T_GRIP_MAX) failWith(F_GRIP_TIMEOUT);
        break;

      case FLIP:
        out.force_set = GRIP_F_SET;
        servo_cmd_ = grip_.update(servo_cmd_, GRIP_F_SET, in.force, dt);  // hold force through the flip
        out.servo_deg = servo_cmd_;
        if (in.force < GRIP_F_LOST) { failWith(F_CAN_LOST); break; }
        if (!track(in, out, dt, G_MR_LOADED)) break;
        if (moveSettled(in, dt)) { enter(RELEASE); }
        break;

      case RELEASE:  // hold the arm still at THETA_END while the jaws open
        out.servo_deg = SERVO_OPEN_DEG;
        if (!track(in, out, dt, G_MR_EMPTY)) break;
        if (t_state_ >= T_RELEASE && in.force < GRIP_F_CONTACT) { startMove(in.theta, 0.0f); enter(RETURN); }
        else if (t_state_ > T_RELEASE + 1.0f) failWith(F_SETTLE_TIMEOUT);
        break;

      case RETURN:
        out.servo_deg = SERVO_OPEN_DEG;
        if (!track(in, out, dt, G_MR_EMPTY)) break;
        if (move_t_ >= FLIP_T) enter(SEAT);
        break;

      case SEAT:
        out.servo_deg = SERVO_OPEN_DEG;
        out.motor_volts = in.home_switch ? 0.0f : SEAT_VOLTS;
        if (in.home_switch) { zero_request = true; enter(DONE); }
        else if (t_state_ > T_SEAT_MAX) failWith(F_HOME_TIMEOUT);
        break;

      case DONE:
        out.motor_volts = 0.0f;
        out.servo_deg = SERVO_OPEN_DEG;
        if (in.start) enter(IDLE);
        break;

      case FAULT:
      default:
        out.motor_volts = 0.0f;
        out.servo_deg = SERVO_OPEN_DEG;
        if (in.start) { fault = F_NONE; enter(HOME); }
        break;
    }
  }

  // Set by HOME/SEAT when the switch closes; the hardware layer re-zeros the encoder
  // count (removes any accumulated slip) and clears the flag.
  bool zero_request = false;

 private:
  Pid pid_;
  GripForceLoop grip_;
  Quintic traj_;
  float t_state_ = 0.0f, move_t_ = 0.0f, prev_theta_ = 0.0f, settle_ = 0.0f, servo_cmd_ = SERVO_OPEN_DEG;
  int hits_ = 0;
  bool contact_ = false;

  void enter(State s) { state = s; t_state_ = 0.0f; settle_ = 0.0f; }
  void failWith(Fault f) { fault = f; enter(FAULT); }

  void startMove(float from, float to) {
    traj_.start(from, to, FLIP_T);
    move_t_ = 0.0f;
    prev_theta_ = from;
    pid_.reset(from);
  }

  // Track the trajectory; returns false (and faults) on excessive error.
  bool track(const Inputs& in, Outputs& out, float dt, float g_mr) {
    float pos, vel, acc;
    traj_.eval(move_t_, pos, vel, acc);
    move_t_ += dt;
    out.theta_ref = pos;
    out.motor_volts = pid_.update(pos, in.theta, flipFeedforward(pos, vel, acc, g_mr), vel, dt);
    if (fabsf(pos - in.theta) > FLIP_FAULT_ERR) { failWith(F_TRACKING); out.motor_volts = 0.0f; return false; }
    return true;
  }

  bool moveSettled(const Inputs& in, float dt) {
    const float w = (in.theta - prev_theta_) / dt;
    prev_theta_ = in.theta;
    const bool ok = move_t_ >= FLIP_T && fabsf(traj_.th1 - in.theta) < FLIP_DONE_ERR && fabsf(w) < FLIP_DONE_W;
    settle_ = ok ? settle_ + dt : 0.0f;
    if (move_t_ > FLIP_T + 1.5f) failWith(F_SETTLE_TIMEOUT);
    return settle_ >= T_FLIP_SETTLE;
  }
};
