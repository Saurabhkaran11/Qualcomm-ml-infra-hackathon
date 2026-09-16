#include <Arduino_LED_Matrix.h>
#include <Arduino_Modulino.h>
#include "Arduino_RouterBridge.h"
#include "auth_frames.h"

ModulinoPixels pixels;
ModulinoBuzzer buzzer;
Arduino_LED_Matrix matrix;  // the Uno Q's own 12x8 display
bool hasBuzzer = false;

const int BRIGHTNESS = 25;
const ModulinoColor OFF(0, 0, 0);

// 2.7 kHz is the piezo's resonant peak — the loudest note it can make, and the buzzer has no
// volume control. Repeated so it reads as a warning. Green is silent: only a refusal sounds.
const int DENY_HZ = 2730;

void fill(ModulinoColor color) {
  for (int i = 0; i < 8; i++) pixels.set(i, color, BRIGHTNESS);
  pixels.show();
}

void face(const uint32_t art[4]) {
  matrix.loadFrame(art);
}

// One beep per denied person, with a cross flashing on the matrix in time with each beep.
// Silent and a steady tick when every light is green.
void alert(int denied) {
  if (denied <= 0) {
    face(TICK);
    return;
  }

  for (int n = 0; n < denied; n++) {
    face(CROSS);
    if (hasBuzzer) buzzer.tone(DENY_HZ, 200);
    delay(200);  // tone() returns immediately; the icon and the beep share this window
    face(BLANK);
    delay(100);  // gap, so both the beeps and the flashes stay countable
  }
  if (hasBuzzer) buzzer.noTone();
  face(CROSS);  // leave the cross up as the standing verdict
}

// Called from Linux once per camera frame.
// count = people detected (0..8), mask = bit i set when person i is authorized.
// LED i shows person i, leftmost first; unused LEDs stay off so the count is readable.
int set_people(int count, int mask) {
  if (count > 8) count = 8;

  fill(OFF);   // one blackout so a repeated result still reads as a new frame
  delay(150);

  int denied = 0;
  for (int i = 0; i < 8; i++) {
    if (i >= count) {
      pixels.set(i, OFF, BRIGHTNESS);
    } else if ((mask >> i) & 1) {
      pixels.set(i, GREEN, BRIGHTNESS);
    } else {
      pixels.set(i, RED, BRIGHTNESS);
      denied++;
    }
  }
  pixels.show();
  alert(denied);  // lights first, then sound
  return count;
}

// Single-result path: one person on LED 0.
int set_status(int authorized, int denied) {
  (void)denied;
  return set_people(1, authorized ? 1 : 0);
}

void setup() {
  matrix.begin();
  matrix.clear();

  Modulino.begin();
  pixels.begin();
  hasBuzzer = buzzer.begin();  // optional: the lights still work without it
  fill(BLUE);                  // idle: waiting for a check

  if (!Bridge.begin()) {
    while (true) {
      fill(VIOLET);
      delay(200);
      fill(OFF);
      delay(200);
    }
  }
  Bridge.provide("set_people", set_people);
  Bridge.provide("set_status", set_status);
}

void loop() {
  delay(1);
}
