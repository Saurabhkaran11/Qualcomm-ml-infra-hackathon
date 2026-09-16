// Frames for the Uno Q's built-in LED matrix — the display the rpc_hearts example drew its
// heart on.
//
// The panel is 13 x 8 = 104 LEDs (canvasWidth = 13 in Arduino_LED_Matrix.h), NOT 12 x 8.
// Art drawn 12 wide shifts one column per row and comes out skewed.
//
// These are packed as four uint32 words for loadFrame(): 3 full words plus the last 8 bits
// left-aligned in word 4. Do not switch to renderBitmap()/loadPixels() here — its internal
// _frameHolder is only 3 words and overruns on a 104-LED panel.
#pragma once

// ###.......###
// ####.....####
// .###########.
// ...#######...
// ...#######...
// .###########.
// ####.....####
// ###.......###
const uint32_t CROSS[4] = { 0xe03f83df, 0xfc3f81fc, 0x3ffbc1fc, 0x07000000 };

// ...........##
// .........####
// ........####.
// ##....#####..
// ###..#####...
// .#######.....
// ..#####......
// ...##........
const uint32_t TICK[4] = { 0x001803c0, 0x3d87ce7c, 0x3f80f803, 0x00000000 };

const uint32_t BLANK[4] = { 0, 0, 0, 0 };
