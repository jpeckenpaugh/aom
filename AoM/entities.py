from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from config import *
from utils import make_radial_glow, lumen_timeline_sprite


@dataclass
class LumenWisp:
    x: float
    z: float
    collected: bool = False
    collecting: bool = False
    has_appeared: bool = False
    spawn_age: float = 0.0
    collect_age: float = 0.0

    def __post_init__(self):
        self.phase = (self.x * 0.017 + self.z * 0.031) % math.tau

    @property
    def visible(self):
        return not self.collected or self.collect_age < LUMEN_SHRINK_SECONDS

    @property
    def visual_scale(self):
        if self.collecting:
            t = max(0, min(1, self.collect_age / LUMEN_SHRINK_SECONDS))
            return max(0.01, 1 - (t * t * (3 - 2 * t)))
        t = max(0, min(1, self.spawn_age / LUMEN_GROW_SECONDS))
        return max(0.01, t * t * (3 - 2 * t))

    def update(self, dt, appearing=False):
        if appearing:
            self.has_appeared = True
        if not self.collected and self.has_appeared:
            self.spawn_age += dt
        if self.collecting:
            self.collect_age += dt

    def collect(self):
        self.collected = True
        self.collecting = True
        self.collect_age = 0

    def distance_to(self, x, z):
        return math.hypot(self.x - x, (self.z - z) * 1.25)

    def draw(self, surface, camera, time, growth_state, depth_scale=1.0, sprites=None):
        if not self.visible:
            return
        scale = self.visual_scale * depth_scale
        bob = math.sin(time * 2.3 + self.phase) * 9 * scale
        screen = camera.project(self.x, self.z, 36 + bob)

        if sprites:
            pulse = 0.5 + 0.5 * math.sin(time * 4.0 + self.phase)
            glow = make_radial_glow(round(84 * scale), LUMEN, round((22 + pulse * 8) * scale), 1.95)
            surface.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
            haze = make_radial_glow(round(40 * scale), LUMEN_CORE, round((34 + pulse * 14) * scale), 1.40)
            surface.blit(haze, haze.get_rect(center=(round(screen.x), round(screen.y))))

            if len(sprites) == 1:
                sprite = sprites[0]
            else:
                idx = lumen_timeline_sprite(time, self.phase, len(sprites))
                sprite = sprites[idx]

            t = time
            base = (360 * math.sin(t * 0.12 + self.phase) + 240 * math.sin(t * 0.07 + self.phase * 1.7) + 160 * math.sin(t * 0.19 + self.phase * 0.3))
            drift = 280 * math.sin(t * 0.17 + 0.5 + self.phase)
            lope = 200 * math.sin(t * 0.43 + 2.1 + self.phase * 0.7)
            shiver = 80 * math.sin(t * 1.7 + 0.8 + self.phase * 1.3)
            angle = base + drift + lope + shiver

            rotated = pygame.transform.rotate(sprite, angle)
            w, h = sprite.get_size()
            bbox = int(math.ceil(math.hypot(w, h)))
            if rotated.get_size() != (bbox, bbox):
                canvas = pygame.Surface((bbox, bbox), pygame.SRCALPHA)
                canvas.blit(rotated, rotated.get_rect(center=(bbox // 2, bbox // 2)))
                rendered = canvas
            else:
                rendered = rotated

            target = max(1, round(16 * scale))
            art = pygame.transform.scale(rendered, (target, target))
            surface.blit(art, art.get_rect(center=(round(screen.x), round(screen.y))))
        else:
            pulse = 0.5 + 0.5 * math.sin(time * 4.0 + self.phase)
            glow = make_radial_glow((128 + round(pulse * 28)) * scale, LUMEN, round((18 + pulse * 10) * scale), 1.95)
            surface.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
            haze = make_radial_glow((48 + round(pulse * 12)) * scale, LUMEN_CORE, round((34 + pulse * 14) * scale), 1.45)
            surface.blit(haze, haze.get_rect(center=(round(screen.x), round(screen.y))))
            pygame.draw.circle(surface, (*LUMEN_CORE, round(62 * scale)), screen, max(1, round(4 * scale)))


@dataclass
class FloorPebble:
    x: float
    z: float
    rx: float
    rz: float
    color: tuple[int, int, int]
    alpha: int


@dataclass
class FloorCrack:
    points: list[tuple[float, float]]
    alpha: int


@dataclass
class LeafDecal:
    x: float
    z: float
    image: pygame.Surface
    mycelial_image: pygame.Surface | None = None
    fern_slots: list[int | None] = None
    feed_progress: float = 0.0
    connected: bool = False
    lumen_consumed: bool = False


@dataclass
class LeafQuestLumen:
    leaf_index: int
    start: pygame.Vector2
    target: pygame.Vector2
    delay: float
    progress: float = 0.0
    consumed: bool = False
    consume_age: float = 0.0
    phase: float = 0.0

    @property
    def arrived(self):
        return self.progress >= 1.0

    @property
    def visible(self):
        return not self.consumed or self.consume_age < LUMEN_SHRINK_SECONDS

    @property
    def visual_scale(self):
        if self.consumed:
            t = max(0, min(1, self.consume_age / LUMEN_SHRINK_SECONDS))
            return max(0.01, 1 - (t * t * (3 - 2 * t)))
        return max(0.01, self.progress * self.progress * (3 - 2 * self.progress))

    @property
    def pos(self):
        t = self.progress * self.progress * (3 - 2 * self.progress)
        return self.start.lerp(self.target, t)


@dataclass
class PebbleDecal:
    x: float
    z: float
    image: pygame.Surface
    loose_material: bool = False


@dataclass
class EdgeLeafDecal:
    x: float
    z: float
    image: pygame.Surface


@dataclass
class ChannelCoverLeaf:
    pos: pygame.Vector2
    target: pygame.Vector2
    image: pygame.Surface
    moving: bool = False
    placed: bool = False
    move_start: pygame.Vector2 | None = None
    move_progress: float = 0.0
    sway_phase: float = 0.0


@dataclass
class Ripple:
    x: float
    z: float
    age: float = 0.0
    radius_scale: float = 1.0


@dataclass
class ElementalSpell:
    pos: pygame.Vector2
    direction: pygame.Vector2
    color: tuple[int, int, int]
    element: str
    level: int = 1
    size_scale: float = 1.0
    burst_on_expire: bool = False
    delay: float = 0.0
    age: float = 0.0


@dataclass
class ConcentrateRock:
    pos: pygame.Vector2
    held: bool = False
    lifted: bool = False
    sway_phase: float = 0.0


@dataclass
class PebbleWaypoint:
    pos: pygame.Vector2
    element: str
    color: tuple[int, int, int]
    occupied_by: int | None = None
    claimed_by: int | None = None
    charge: float = 0.0
    visible_charge: float = 0.0
    regen_offsets: list[pygame.Vector2] = field(default_factory=list)


@dataclass
class ConcentratePebble:
    id: int
    pos: pygame.Vector2
    image: pygame.Surface
    held: bool = False
    moving: bool = False
    placed: bool = False
    target_waypoint: int | None = None
    target_group: str = "primary"
    move_start: pygame.Vector2 | None = None
    move_progress: float = 0.0
    sway_phase: float = 0.0
    claimed_by: int | None = None


@dataclass
class FernFrond:
    id: int
    pos: pygame.Vector2
    image: pygame.Surface
    held: bool = False
    moving: bool = False
    placed: bool = False
    target_leaf: int | None = None
    target_slot: int | None = None
    move_start: pygame.Vector2 | None = None
    move_progress: float = 0.0
    sway_phase: float = 0.0
    claimed_by: int | None = None


@dataclass
class NpcMushroom:
    pos: pygame.Vector2
    home: pygame.Vector2
    phase: float
    target: pygame.Vector2
    moving: bool = False
    task: str = "idle"
    pebble_id: int | None = None
    waypoint_id: int | None = None
    waypoint_group: str = "companion"
    fern_id: int | None = None
    leaf_id: int | None = None
    fern_slot: int | None = None
    element_focus: str | None = None
    cast_time: float = 0.0
    spawn_age: float = 0.0
    rest_timer: float = 0.0
    transit_target: pygame.Vector2 | None = None
    transit_time: float = 0.0
    transit_phase: str | None = None
    body_scale: float = 1.0
    growth_cycles: int = 0
    dividing: bool = False
    divide_time: float = 0.0
    pending_division: bool = False
    regen_time: float = 0.0
    sprite_variant: str = "neutral"
    width_scale: float = 1.0
    height_scale: float = 1.0
    luminosity: float = 0.68
    divide_origin: pygame.Vector2 | None = None
    channeling: bool = False
    channel_requested: bool = False
    channel_phase: str | None = None
    channel_time: float = 0.0
    terrain_lift: float = 0.0

