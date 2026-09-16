#include <Arduino_Modulino.h>
#include "Arduino_RouterBridge.h"

ModulinoPixels pixels;
const int BRIGHTNESS = 25;
const int PIXEL_COUNT = 8;
const ModulinoColor OFF(0, 0, 0);

void fill(ModulinoColor color) {
  for (int i = 0; i < PIXEL_COUNT; i++) pixels.set(i, color, BRIGHTNESS);
  pixels.show();
}

// Called from Linux once per camera frame.
// count = people detected (0..8), mask = bit i set when person i is authorized.
// LED i shows person i, leftmost first; unused LEDs stay off so the count is readable.
// ponytail: no buzzer on board or Pixels; the flash stands in for the beep. Add ModulinoBuzzer.tone() here once wired.
int set_people(int count, int mask) {
  if (count > PIXEL_COUNT) count = PIXEL_COUNT;

  // One flash so a repeated result is still visibly a new reading.
  fill(OFF);
  delay(150);

  for (int i = 0; i < PIXEL_COUNT; i++) {
    if (i >= count) {
      pixels.set(i, OFF, BRIGHTNESS);
    } else {
      pixels.set(i, (mask >> i) & 1 ? GREEN : RED, BRIGHTNESS);
    }
  }
  pixels.show();
  return count;
}

// Kept for the single-result path: one person on LED 0.
int set_status(int authorized) {
  return set_people(1, authorized ? 1 : 0);
}

void setup() {
  Modulino.begin();
  pixels.begin();
  fill(BLUE);  // idle: waiting for a frame

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
