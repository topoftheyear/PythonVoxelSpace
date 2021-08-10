import math
import random
import sys
import time

import ctypes
import cv2
import numpy as np
import pygame
import pygame.gfxdraw

from common.game_object import GameObject
from common.point import Point
from common.settings import Settings
from utils.helpers import *

pygame.init()
settings = Settings()

resolution_width_ratio = settings.res_x / settings.internal_res_x
resolution_height_ratio = settings.res_y / settings.internal_res_y

flags = pygame.DOUBLEBUF
screen = pygame.display.set_mode((settings.res_x, settings.res_y), flags)
pygame.display.set_caption("VoxelSpace")

surface = pygame.Surface((settings.internal_res_x, settings.internal_res_y))
scaled_surface = pygame.Surface(screen.get_size())

clock = pygame.time.Clock()

heightmap = cv2.imread('img/1H.png', 0)
colormap = cv2.imread('img/1C.png', -1)
colormap = cv2.cvtColor(colormap, cv2.COLOR_BGR2RGB)

object_list = dict()

worf = pygame.image.load('img/worf.png').convert_alpha()
worf = pygame.transform.scale(worf, (int(worf.get_width() / settings.res_width_ratio),
                                     int(worf.get_height() / settings.res_height_ratio)))


# establish c function
class LineStruct(ctypes.Structure):
    _fields_ = [
        ('lines', (ctypes.c_int * 6) * 1000000),
        ('numLines', ctypes.c_int),
        ('objects', (ctypes.c_int * 6) * 10000),
        ('numObjects', ctypes.c_int),
        ('heightMap', (ctypes.c_int * 1024) * 1024),
        ('colorMap', ((ctypes.c_int * 3) * 1024) * 1024),
        ('currentX', ctypes.c_float),
        ('currentY', ctypes.c_float),
        ('rotation', ctypes.c_float),
        ('height', ctypes.c_int),
        ('horizon', ctypes.c_float),
        ('scaleHeight', ctypes.c_float),
        ('distance', ctypes.c_int),
        ('screenWidth', ctypes.c_int),
        ('screenHeight', ctypes.c_int),
        ('quality', ctypes.c_float),
    ]


line_calculator = ctypes.CDLL('liblines.dll')
line_calculator.get_lines.argtypes = [ctypes.POINTER(LineStruct)]
line_calculator.get_lines.restype = None

ls = LineStruct()


def main():
    quality = settings.start_quality

    current_position = Point(0, 0)
    speed = 4
    moving_forward = False
    moving_backward = False

    current_rotation = 0
    rotating_right = False
    rotating_left = False

    current_height = 50
    moving_up = False
    moving_down = False

    horizon = 120
    scale_height = 240

    # Set one-time struct variables
    ls.heightMap = heightmap_to_ctypes(ls.heightMap, heightmap)
    ls.colorMap = colormap_to_ctypes(ls.colorMap, colormap)
    ls.screenWidth = surface.get_width()
    ls.screenHeight = surface.get_height()

    # create a few game objects
    for n in range(50):
        x = random.randint(0, 1023)
        y = random.randint(0, 1023)
        obj = GameObject(Point(x, y), heightmap[x, y])
        object_list[obj.id] = obj

    while 1:
        start = time.time()

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                pygame.display.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == settings.rotate_right:
                    rotating_right = True
                if event.key == settings.rotate_left:
                    rotating_left = True
                if event.key == settings.move_forward:
                    moving_forward = True
                if event.key == settings.move_backward:
                    moving_backward = True

                if event.key == settings.move_up:
                    moving_up = True
                if event.key == settings.move_down:
                    moving_down = True

                if event.key == pygame.K_EQUALS:
                    quality -= settings.quality_chunks
                if event.key == pygame.K_MINUS:
                    quality += settings.quality_chunks

                if event.key == pygame.K_ESCAPE:
                    pygame.display.quit()
                    sys.exit()

            if event.type == pygame.KEYUP:
                if event.key == settings.rotate_right:
                    rotating_right = False
                if event.key == settings.rotate_left:
                    rotating_left = False
                if event.key == settings.move_forward:
                    moving_forward = False
                if event.key == settings.move_backward:
                    moving_backward = False

                if event.key == settings.move_up:
                    moving_up = False
                if event.key == settings.move_down:
                    moving_down = False

        quality = max(quality, 0)

        if rotating_right:
            current_rotation -= settings.camera_rotation_speed
        if rotating_left:
            current_rotation += settings.camera_rotation_speed
        current_rotation %= 2 * math.pi

        if moving_forward:
            current_position.move(speed, current_rotation)
        if moving_backward:
            current_position.move(-speed, current_rotation)

        if moving_up:
            current_height += speed
        if moving_down:
            current_height -= speed

        current_position.x = min(current_position.x % 1024, 1023)
        current_position.y = min(current_position.y % 1024, 1023)

        current_height = max(current_height, heightmap[math.floor(current_position.x), math.floor(current_position.y)] + 1)
        current_height = min(current_height, 1000)

        # Set per-frame struct variables
        ls.currentX = current_position.x
        ls.currentY = current_position.y
        ls.rotation = current_rotation
        ls.height = current_height
        ls.horizon = horizon / resolution_width_ratio
        ls.scaleHeight = scale_height / resolution_height_ratio
        ls.distance = settings.view_distance
        ls.quality = quality
        ls.numObjects = len(object_list.keys())
        x = 0
        for obj in object_list.values():
            ls.objects[x][0] = obj.id
            ls.objects[x][1] = obj.position.x
            ls.objects[x][2] = obj.position.y
            ls.objects[x][3] = obj.height
            ls.objects[x][4] = 0
            ls.objects[x][5] = 0

            x += 1

        render()

        pygame.display.update()
        clock.tick(30)

        print(1 / (time.time() - start))


def render():
    surface.fill((135, 206, 235))

    line_calculator.get_lines(ctypes.byref(ls))

    for x in range(ls.numLines):
        line = ls.lines[x]

        pygame.gfxdraw.vline(
            surface,
            line[0],
            line[1],
            line[2],
            [line[3], line[4], line[5]],
        )

    for x in range(ls.numObjects):
        obj = object_list[ls.objects[x][0]]
        pos = [ls.objects[x][4], ls.objects[x][5]]

        if pos[0] == 0 and pos[1] == 0:
            continue

        if pos[0] < 0 or pos[0] >= 1023 and pos[1] < 0 or pos[1] >= 1023:
            continue

        # Scale based on distance from camera
        campy = np.array([ls.currentX, ls.currentY, ls.height])
        objpy = np.array([obj.position.x, obj.position.y, obj.height])
        scale_distance = np.linalg.norm(campy - objpy)
        scale_ratio = (1 / (scale_distance / settings.view_distance)) / (settings.view_distance / 10)
        scaled_obj = worf
        scaled_obj = pygame.transform.scale(scaled_obj, (int(scaled_obj.get_width() * scale_ratio),
                                                         int(scaled_obj.get_height() * scale_ratio)))

        shifted_width = int(pos[0] - (scaled_obj.get_width() / 2))
        shifted_height = int(pos[1] - (scaled_obj.get_height() / 2))

        surface.blit(
            scaled_obj,
            [shifted_width, shifted_height]
        )

    pygame.transform.scale(surface, screen.get_size(), scaled_surface)
    screen.blit(scaled_surface, (0, 0))


if __name__ == '__main__':
    main()


def __main__():
    main()
