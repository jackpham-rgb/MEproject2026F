// Runs firmware/concept_a/concept_a.ino on a PC with a fake Arduino (clock, Serial, Servo, button)
// and checks the laptop commands.   bash backend/tools/firmware_test/run.sh
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <deque>
#include <vector>
typedef unsigned char byte;
#define F(x) x
#define INPUT_PULLUP 2
#define OUTPUT 1
#define LOW 0
#define HIGH 1
static unsigned long t_ms = 0;
unsigned long millis() { return t_ms; }
void delay(unsigned long d) { t_ms += d; }
static int buttonLevel = HIGH;
void pinMode(int, int) {}
int digitalRead(int) { return buttonLevel; }
void digitalWrite(int, int) {}
static std::string out;
struct FakeSerial {
  std::deque<char> in;
  void begin(long) {}
  int available() { return (int)in.size(); }
  int read() { char c = in.front(); in.pop_front(); return c; }
  void print(const char* s) { out += s; }
  void print(char c) { out += c; }
  void print(int v) { out += std::to_string(v); }
  void println(const char* s) { out += s; out += '\n'; }
  void println(int v) { out += std::to_string(v); out += '\n'; }
  void println() { out += '\n'; }
  void send(const char* s) { while (*s) in.push_back(*s++); in.push_back('\n'); }
} Serial;
struct Servo {
  int pin = -1, angle = -1, writesBeforeAttach = 0;
  void attach(int p) { pin = p; }
  void attach(int p, int, int) { pin = p; }
  void write(int a) { angle = a; if (pin < 0) writesBeforeAttach++; }
  int us = 0;
  void writeMicroseconds(int u) { us = u; }
};
#include "../../../firmware/concept_a/concept_a.ino"

static int fails = 0;
static std::string lastStatus() {
  size_t p = out.rfind("@ ");
  return p == std::string::npos ? "" : out.substr(p, out.find('\n', p) - p);
}
static void runFor(unsigned long ms) { unsigned long end = t_ms + ms; while (t_ms < end) loop(); }
static void expect(bool ok, const char* what, const std::string& got = "") {
  printf("%s  %s%s%s\n", ok ? "PASS" : "FAIL", what, got.empty() ? "" : "   got: ", got.c_str());
  if (!ok) fails++;
}
static bool has(const char* s) { return out.find(s) != std::string::npos; }

int main() {
  setup();
  expect(lastStatus() == "@ IDLE - 135 30 0 20", "boots at HOME, reports status", lastStatus());
  expect(turnServo.writesBeforeAttach > 0, "angle written before attach (no jump at power-up)");

  out.clear(); Serial.send("w 90"); runFor(2000);
  expect(lastStatus() == "@ IDLE - 135 30 90 20", "w 90: wrist moves to 90, others stay", lastStatus());
  expect(has("@ MANUAL M-WRIST"), "live status while moving");

  out.clear(); Serial.send("s"); runFor(100);
  expect(has("Not at HOME"), "START refused away from HOME (would swing several servos at once)");

  out.clear(); Serial.send("h"); runFor(4000);
  expect(lastStatus() == "@ IDLE - 135 30 0 20", "h: back to HOME, one servo at a time", lastStatus());

  out.clear(); unsigned long t0 = t_ms; Serial.send("t 45"); while (t_ms - t0 < 5000 && !has("Moved.")) loop();
  unsigned long baseMs = t_ms - t0;
  expect(baseMs >= 1550 && baseMs <= 1750, "base moves slowly: 90 deg in ~1.6 s (18 ms/deg)", std::to_string(baseMs) + " ms");
  out.clear(); t0 = t_ms; Serial.send("t 75"); runFor(200);
  int us1 = turnServo.us; runFor(10); int us2 = turnServo.us;
  expect(us1 > 0 && us1 != us2 && abs(us2 - us1) < 10, "fine steps: base gets microseconds, < 1 degree per update",
         std::to_string(us1) + " -> " + std::to_string(us2));
  runFor(2000); out.clear(); Serial.send("h"); runFor(4000);
  size_t a = out.find("M-LIFT"), b = out.find("M-WRIST"), c = out.find("M-TURN"), d = out.find("M-LOWER");
  expect(a < b && b < c && c < d, "home order: lift up, wrist, turn, ..., lower");

  out.clear(); Serial.send("t 10"); runFor(2500);
  expect(has("limited to 35"), "out-of-range angle is clamped (turntable 35..145)");
  out.clear(); Serial.send("h"); runFor(4000);

  out.clear(); Serial.send("l 75"); runFor(150); Serial.send("g 90"); runFor(50);
  expect(has("Busy"), "a second command while moving is refused");
  Serial.send("x"); runFor(50);
  expect(has("Stopped") && lastStatus().rfind("@ IDLE", 0) == 0, "x stops and holds", lastStatus());
  out.clear(); Serial.send("h"); runFor(5000);
  expect(lastStatus() == "@ IDLE - 135 30 0 20", "h after a stop returns HOME", lastStatus());

  out.clear(); Serial.send("s"); t0 = t_ms; while (t_ms - t0 < 12000 && !has("DONE")) loop();
  expect(t_ms - t0 >= 7300 && t_ms - t0 <= 7600, "sequence takes ~7.4 s (TURN now 2.5 s)", std::to_string(t_ms - t0) + " ms");
  runFor(100);
  expect(has("> GRIP") && has("> RELEASE") && has("DONE"), "laptop START runs the whole sequence");
  expect(lastStatus() == "@ DONE - 45 30 180 70", "ends at the target, inverted, released", lastStatus());

  out.clear(); buttonLevel = LOW; runFor(60); buttonLevel = HIGH; runFor(9000);
  expect(has("Going home") && lastStatus() == "@ IDLE - 135 30 0 20", "physical button after DONE: goes home", lastStatus());

  out.clear(); buttonLevel = LOW; runFor(60); buttonLevel = HIGH; runFor(9000);
  expect(has("DONE"), "physical button from HOME: runs the sequence");

  out.clear(); Serial.send("c"); runFor(50);
  expect(has("= TURN_START 135 TURN_TARGET 45 LIFT_DOWN 30 LIFT_UP 75 WRIST_UP 0 WRIST_FLIP 180 GRIP_OPEN 20 GRIP_CLOSED 95 GRIP_RELEASE 70 LIM_t 35 145 LIM_l 25 80 LIM_w 0 180 LIM_g 10 100"),
         "c: reports the calibration constants and limits", out.substr(0, 200));

  printf("\n%s (%d failed)\n", fails ? "FAIL" : "ALL PASS", fails);
  return fails ? 1 : 0;
}
