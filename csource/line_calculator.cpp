#include <cstring>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>

using namespace std;

struct LineStruct {
    int lines[1000000][6];
    int numLines;
    int heightMap[1024][1024];
    int colorMap[1024][1024][3];
    float currentX;
    float currentY;
    float rotation;
    int height;
    float horizon;
    float scaleHeight;
    int distance;
    int screenWidth;
    int screenHeight;
    float quality;
};

extern "C"
void get_lines(LineStruct *ls) {
    // Precalculate viewing angle parameters
    float sinPhi = sin(ls->rotation);
    float cosPhi = cos(ls->rotation);

    float plx, ply, prx, pry = 0;

    // Establish height array
    int hiddenY[ls->screenWidth];

    for (int x = 0; x < ls->screenWidth; x++) {
        hiddenY[x] = ls->screenHeight;
    }

    float deltaZ = 1;
    float z = 1;

    int lineCount = 0;
    while (z < ls->distance) {
        // Find line on map. This calculation corresponds to a field of view of 90°
        plx = (z * (-cosPhi - sinPhi)) + ls->currentX;
        ply = (z * (sinPhi - cosPhi)) + ls->currentY;
        prx = (z * (cosPhi - sinPhi)) + ls->currentX;
        pry = (z * (-sinPhi - cosPhi)) + ls->currentY;

        float dx = (prx - plx) / ls->screenWidth;
        float dy = (pry - ply) / ls->screenWidth;

        float invz = 1 / z * ls->scaleHeight;
        float heightz = (ls->height * invz) + ls->horizon;

        float colorLerp = z / ls->distance;

        for (int i = 0; i < ls->screenWidth; i++) {
            int roundedplx = (int)floor(plx);
            int roundedply = (int)floor(ply);

            // Wrap x and y around map size
            if (roundedplx >= 0) {
                roundedplx %= 1024;
            }
            else if (roundedplx < 0) {
                roundedplx = (roundedplx + 10240) % 1024;
            }

            if (roundedply >= 0) {
                roundedply %= 1024;
            }
            else if (roundedply < 0) {
                roundedply = (roundedply + 10240) % 1024;
            }

            // Rasterize to screen height
            int heightMapNum = ls->heightMap[roundedplx][roundedply];
            int* color = ls->colorMap[roundedplx][roundedply];

            // Lerp color to color of sky
            int colorR = (int)(colorLerp * (135 - color[0]) + color[0]);
            int colorG = (int)(colorLerp * (206 - color[1]) + color[1]);
            int colorB = (int)(colorLerp * (235 - color[2]) + color[2]);

            int heightOnScreen = (int)floor(heightz - (invz * heightMapNum));

            if (heightOnScreen < hiddenY[i] && hiddenY[i] > -1) {
                ls->lines[lineCount][0] = i;
                ls->lines[lineCount][1] = heightOnScreen;
                ls->lines[lineCount][2] = hiddenY[i];
                ls->lines[lineCount][3] = colorR;
                ls->lines[lineCount][4] = colorG;
                ls->lines[lineCount][5] = colorB;

                hiddenY[i] = heightOnScreen;
                lineCount += 1;
            }

            plx += dx;
            ply += dy;
        }

        z += deltaZ;
        deltaZ += ls->quality;
    }

    ls->numLines = lineCount;

    return;
}
