#include <Arduino_Modulino.h>
#include "Arduino_RouterBridge.h"

ModulinoPixels pixels;
const int BRIGHTNESS = 25;

void fill(ModulinoColor color) {
  for (int i = 0; i < 8; i++) pixels.set(i, color, BRIGHTNESS);
  pixels.show();
}

// Called from Linux: 1 = authorized (green), 0 = unauthorized (red).
// ponytail: no buzzer on board or Pixels; flashes stand in for the beep. Add ModulinoBuzzer.tone() here once wired.
int set_status(int authorized) {
  ModulinoColor color = authorized ? GREEN : RED;
  int flashes = authorized ? 1 : 3;
  for (int n = 0; n < flashes; n++) {
    fill(color);
    delay(150);
    fill(ModulinoColor(0, 0, 0));
    delay(150);
  }
  fill(color);
  return authorized;
}

void setup() {
  Modulino.begin();
  pixels.begin();
  fill(BLUE);  // idle: waiting for a check

  if (!Bridge.begin()) {
    while (true) {
      fill(VIOLET);
      delay(200);
      fill(ModulinoColor(0, 0, 0));
      delay(200);
    }
  }
  Bridge.provide("set_status", set_status);
}

void loop() {
  delay(1);
}
