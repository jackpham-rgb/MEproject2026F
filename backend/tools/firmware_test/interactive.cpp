// The real firmware/concept_a/concept_a.ino running live on a PC (fake Arduino, real-time clock):
// commands on stdin, the Uno's serial output on stdout. Used to test viewer/control_panel.html.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <unistd.h>
typedef unsigned char byte;
#define F(x) x
#define INPUT_PULLUP 2
#define OUTPUT 1
#define LOW 0
#define HIGH 1
static auto T0 = std::chrono::steady_clock::now();
unsigned long millis() { return (unsigned long)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - T0).count(); }
void delay(unsigned long d) { std::this_thread::sleep_for(std::chrono::milliseconds(d)); }
void pinMode(int, int) {}
int digitalRead(int) { return HIGH; }
void digitalWrite(int, int) {}
static std::mutex mu;
struct FakeSerial {
  std::deque<char> in;
  void begin(long) {}
  int available() { std::lock_guard<std::mutex> g(mu); return (int)in.size(); }
  int read() { std::lock_guard<std::mutex> g(mu); char c = in.front(); in.pop_front(); return c; }
  void print(const char* s) { fputs(s, stdout); }
  void print(char c) { fputc(c, stdout); }
  void print(int v) { printf("%d", v); }
  void println(const char* s) { puts(s); fflush(stdout); }
  void println(int v) { printf("%d\n", v); fflush(stdout); }
  void println() { puts(""); fflush(stdout); }
} Serial;
struct Servo { void attach(int) {} void attach(int, int, int) {} void write(int) {} };
#include "../../../firmware/concept_a/concept_a.ino"
int main() {
  std::thread([] { char c; while (::read(0, &c, 1) == 1) { std::lock_guard<std::mutex> g(mu); Serial.in.push_back(c); } exit(0); }).detach();
  setup();
  for (;;) loop();
}
