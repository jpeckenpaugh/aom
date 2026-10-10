import pygame

from config import *


class Camera:
    def __init__(self):
        self.x = 0
        self.z = 0
        self.zoom = 1.0

    def update(self, target_pos, target_zoom=1.0, speed=0.08, dt=None):
        if dt is not None:
            speed = 1 - (1 - speed) ** (dt * FPS)
        self.x += (target_pos.x - self.x) * speed
        self.z += (target_pos.y - self.z) * speed
        self.zoom += (target_zoom - self.zoom) * speed

    def project(self, x, z, height=0):
        screen_x = SCREEN_WIDTH / 2 + (x - self.x) * self.zoom
        screen_y = GROUND_ORIGIN_Y + ((z - self.z) * DEPTH_SCALE - height) * self.zoom
        return pygame.Vector2(screen_x, screen_y)

    def unproject(self, screen_x, screen_y, height=0):
        world_x = self.x + (screen_x - SCREEN_WIDTH / 2) / self.zoom
        world_z = self.z + ((screen_y - GROUND_ORIGIN_Y) / self.zoom + height) / DEPTH_SCALE
        return pygame.Vector2(world_x, world_z)

