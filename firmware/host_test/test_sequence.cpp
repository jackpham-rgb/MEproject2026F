// Laptop regression test: runs the exact firmware state machine + controllers
// against the plant model for the nominal case, parameter spreads and injected
// faults. Build/run:  make -C firmware/host_test
#include <math.h>
#include <stdio.h>

#include "../can_flipper/plant_model.h"
#include "../can_flipper/sequencer.h"

static const float RAD2DEG = 57.29578f;
static int failures = 0;

#define CHECK(cond, ...)                         \
  do {                                           \
    if (!(cond)) {                               \
      printf("    FAIL: " __VA_ARGS__);          \
      printf("\n");                              \
      ++failures;                                \
    }                                            \
  } while (0)

struct Result {
  State end_state;
  Fault fault;
  float peak_deg, release_deg, peak_force, t_done;
  FILE* csv;
};

static Result run(PlantModel& plant, const char* csv_path = nullptr, float t_max = 12.0f) {
  Sequencer seq;
  Outputs out;
  long enc_offset = 0;
  Result r{HOME, F_NONE, 0, 0, 0, 0, nullptr};
  FILE* csv = csv_path ? fopen(csv_path, "w") : nullptr;
  if (csv) fprintf(csv, "t,state,theta_ref_deg,theta_deg,volts,force_set,force,servo_deg\n");
  bool released_logged = false;
  for (int k = 0; k * DT < t_max; ++k) {
    const float t = k * DT;
    Inputs in;
    in.theta = ENC_SIGN * (plant.encoderCount() - enc_offset) * 6.2831853f / ENC_CPR;
    in.force = fsrAdcToNewtons(plant.fsrAdc());
    in.home_switch = plant.homeSwitch();
    in.start = (seq.state == IDLE && t > 0.3f);   // press start once, shortly after homing
    in.can_seen = plant.canSeen();
    seq.step(in, out, DT);
    if (seq.zero_request) { enc_offset = plant.encoderCount(); seq.zero_request = false; }
    if (seq.state == RELEASE && !released_logged) { r.release_deg = plant.theta * RAD2DEG; released_logged = true; }
    plant.step(out.motor_volts, out.servo_deg, DT);
    if (csv) fprintf(csv, "%.4f,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.2f\n", t, STATE_NAMES[seq.state],
                     out.theta_ref * RAD2DEG, plant.theta * RAD2DEG, out.motor_volts, out.force_set,
                     plant.force(), plant.psi);
    if (seq.state == DONE || seq.state == FAULT) { r.t_done = t; break; }
  }
  if (csv) fclose(csv);
  r.end_state = seq.state;
  r.fault = seq.fault;
  r.peak_deg = plant.peak_theta * RAD2DEG;   // true angle, not the quantised reading
  r.peak_force = plant.peak_force;
  return r;
}

static void expectSuccess(const char* name, PlantModel p, const char* csv = nullptr) {
  Result r = run(p, csv);
  printf("  %-28s end=%-6s peak=%7.2f deg  at-release=%7.2f deg  peakF=%.2f N  t=%.2f s\n", name,
         STATE_NAMES[r.end_state], r.peak_deg, r.release_deg, r.peak_force, r.t_done);
  CHECK(r.end_state == DONE, "%s: expected DONE, got %s (fault %d)", name, STATE_NAMES[r.end_state], r.fault);
  CHECK(r.peak_deg < 180.9f, "%s: peak %.2f deg exceeds table-contact limit 180.9", name, r.peak_deg);
  CHECK(fabsf(r.release_deg - 179.5f) < 1.0f, "%s: released at %.2f deg", name, r.release_deg);
  CHECK(r.peak_force < GRIP_F_MAX, "%s: peak force %.2f N", name, r.peak_force);
  CHECK(r.peak_force > 0.44f * 2, "%s: grip never exceeded 2x slip limit", name);
}

static void expectFault(const char* name, PlantModel p, Fault want) {
  Result r = run(p);
  printf("  %-28s end=%-6s fault=%d (want %d)\n", name, STATE_NAMES[r.end_state], r.fault, want);
  CHECK(r.end_state == FAULT && r.fault == want, "%s: expected fault %d, got state %s fault %d", name, want,
        STATE_NAMES[r.end_state], r.fault);
}

int main(int argc, char** argv) {
  const char* csv = argc > 1 ? argv[1] : nullptr;
  printf("Nominal and parameter spread:\n");
  PlantModel p;
  expectSuccess("nominal", p, csv);
  p = PlantModel(); p.j_scale = 1.3f;       expectSuccess("inertia +30%", p);
  p = PlantModel(); p.j_scale = 0.7f;       expectSuccess("inertia -30%", p);
  p = PlantModel(); p.fric_scale = 2.0f;    expectSuccess("friction x2", p);
  p = PlantModel(); p.grav_scale = 3.4f;    expectSuccess("counterweight missing", p);
  p = PlantModel(); p.pad_k_scale = 0.5f;   expectSuccess("soft pads (k x0.5)", p);
  p = PlantModel(); p.pad_k_scale = 2.0f;   expectSuccess("stiff pads (k x2)", p);
  p = PlantModel(); p.theta = 0.3f;         expectSuccess("starts off the home stop", p);

  printf("Fault injection:\n");
  p = PlantModel(); p.can_placed = false;   expectFault("no can on the start spot", p, F_NO_CAN);
  p = PlantModel(); p.motor_dead = true;    expectFault("flip motor disconnected", p, F_TRACKING);
  p = PlantModel(); p.fsr_dead = true;      expectFault("FSR disconnected", p, F_GRIP_EMPTY);

  printf(failures ? "\n%d check(s) FAILED\n" : "\nall checks passed\n", failures);
  return failures ? 1 : 0;
}
