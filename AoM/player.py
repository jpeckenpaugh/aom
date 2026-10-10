import pygame

from config import *
from utils import make_radial_glow


class Player:
    def __init__(self, spawn, sprites):
        self.spawn = pygame.Vector2(spawn)
        self.sprites = sprites
        self.sprite_variant = "neutral"
        self.width_scale = 1.0
        self.height_scale = 1.0
        self.reset()

    def reset(self):
        self.pos = pygame.Vector2(self.spawn)
        self.height = 0
        self.vertical_velocity = 0
        self.grounded = True
        self.moving = False
        self.pulse_timer = 0
        self.channeling = False
        self.channel_requested = False
        self.channel_phase = None
        self.channel_time = 0.0
        self.terrain_lift = 0.0
        self.facing = pygame.Vector2(1, 0)
        self.walk_target = None
        self.walk_start_distance = 0.0
        self.walk_target_eased = False

    def set_walk_target(self, target, eased=False):
        self.walk_target = pygame.Vector2(target)
        self.walk_start_distance = self.pos.distance_to(self.walk_target)
        self.walk_target_eased = eased

    def clear_walk_target(self):
        self.walk_target = None
        self.walk_start_distance = 0.0
        self.walk_target_eased = False

    def walk_target_ease_scale(self, distance):
        if not self.walk_target_eased or self.walk_start_distance <= CLICK_WALK_STOP_RADIUS:
            return 1.0
        progress = 1.0 - max(0.0, min(1.0, distance / self.walk_start_distance))
        ramp = AUTO_GUIDE_EASE_DISTANCE_FRACTION
        if progress < ramp:
            t = progress / ramp
            return AUTO_GUIDE_EASE_START_SCALE + (1.0 - AUTO_GUIDE_EASE_START_SCALE) * t
        if progress > 1.0 - ramp:
            t = (progress - (1.0 - ramp)) / ramp
            return 1.0 + (AUTO_GUIDE_EASE_STOP_SCALE - 1.0) * t
        return 1.0

    def update(self, keys, dt, speed_scale=1.0, auto_walk_speed_scale=1.0):
        movement = pygame.Vector2()
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            movement.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            movement.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            movement.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            movement.y += 1

        manual_movement = movement.length_squared() > 0
        walk_target_movement = False
        if manual_movement:
            self.clear_walk_target()
        elif self.walk_target is not None:
            delta = self.walk_target - self.pos
            distance = delta.length()
            direction = delta.normalize() if distance > 0 else pygame.Vector2()
            move_scale = speed_scale * auto_walk_speed_scale * self.walk_target_ease_scale(distance)
            step = pygame.Vector2(
                direction.x * PLAYER_SPEED_X * move_scale * dt,
                direction.y * PLAYER_SPEED_Z * move_scale * dt,
            )
            if distance <= CLICK_WALK_STOP_RADIUS or distance <= step.length():
                self.pos = self.walk_target.copy()
                self.clear_walk_target()
            else:
                movement = direction
                walk_target_movement = True

        self.moving = movement.length_squared() > 0
        if self.moving:
            movement = movement.normalize()
            self.facing = movement.copy()
            move_scale = speed_scale
            if walk_target_movement:
                distance = self.pos.distance_to(self.walk_target)
                move_scale *= auto_walk_speed_scale * self.walk_target_ease_scale(distance)
            self.pos.x += movement.x * PLAYER_SPEED_X * move_scale * dt
            self.pos.y += movement.y * PLAYER_SPEED_Z * move_scale * dt

        max_radius = CAVE_RADIUS - PLAYER_MARGIN
        distance = self.pos.length()
        if distance > max_radius:
            self.pos.scale_to_length(max_radius)

        self.vertical_velocity -= GRAVITY * dt
        self.height += self.vertical_velocity * dt
        if self.height <= 0:
            self.height = 0
            self.vertical_velocity = 0
            self.grounded = True
        else:
            self.grounded = False

        self.pulse_timer = max(0, self.pulse_timer - dt)

    def jump(self):
        return

    def trigger_pulse(self):
        self.pulse_timer = MUSHROOM_PULSE_SECONDS

    def begin_frame(self):
        self.channel_requested = False

    def request_channel(self):
        self.channel_requested = True

    def update_channel_state(self, dt):
        if self.channel_requested:
            if self.channel_phase is None:
                self.channel_phase = "start"
                self.channel_time = 0.0
            elif self.channel_phase == "end":
                self.channel_phase = "start"
                self.channel_time = max(0.0, MUSHROOM_PULSE_EDGE_SECONDS - self.channel_time)
            elif self.channel_phase == "start":
                self.channel_time += dt
                if self.channel_time >= MUSHROOM_PULSE_EDGE_SECONDS:
                    self.channel_phase = "loop"
                    self.channel_time = 0.0
            elif self.channel_phase == "loop":
                self.channel_time += dt
        elif self.channel_phase in ("start", "loop"):
            self.channel_phase = "end"
            self.channel_time = 0.0
        elif self.channel_phase == "end":
            self.channel_time += dt
            if self.channel_time >= MUSHROOM_PULSE_EDGE_SECONDS:
                self.channel_phase = None
                self.channel_time = 0.0
        self.channeling = self.channel_phase is not None

    def draw(self, surface, camera, time, growth_state):
        ground = camera.project(self.pos.x, self.pos.y)
        if self.sprites.available:
            self.draw_sprite(surface, ground, time, growth_state, 1.0, variant=self.sprite_variant)
        else:
            self.draw_geometry(surface, ground, growth_state)

    def draw_sprite(
        self,
        surface,
        ground,
        time,
        growth_state,
        luminosity=1.0,
        body_scale=1.0,
        variant=None,
        animation_override=None,
        animation_progress=None,
        depth_scale=1.0,
        camera_scale=1.0,
        width_scale=None,
        height_scale=None,
        draw_glow=True,
        draw_height=None,
    ):
        if animation_override:
            animation = animation_override
        elif self.channel_phase == "start":
            animation = "pulse_start"
            animation_progress = self.channel_time / MUSHROOM_PULSE_EDGE_SECONDS
        elif self.channel_phase == "loop":
            animation = "pulse_loop"
        elif self.channel_phase == "end":
            animation = "pulse_end"
            animation_progress = self.channel_time / MUSHROOM_PULSE_EDGE_SECONDS
        elif self.pulse_timer > 0:
            elapsed = max(0.0, MUSHROOM_PULSE_SECONDS - self.pulse_timer)
            if elapsed < MUSHROOM_PULSE_EDGE_SECONDS:
                animation = "pulse_start"
                animation_progress = elapsed / MUSHROOM_PULSE_EDGE_SECONDS
            elif self.pulse_timer < MUSHROOM_PULSE_EDGE_SECONDS:
                animation = "pulse_end"
                animation_progress = 1.0 - self.pulse_timer / MUSHROOM_PULSE_EDGE_SECONDS
            else:
                animation = "pulse_loop"
        elif self.moving:
            animation = "walk"
        else:
            animation = "idle"

        variant = variant or self.sprite_variant
        if self.sprites.sprite_style == "Classic":
            profile_width, profile_height = (1.0, 1.0)
            base_size = 88 + growth_state * 4
        else:
            profile_width, profile_height = MUSHROOM_ASPECT_PROFILES.get(variant, MUSHROOM_ASPECT_PROFILES["neutral"])
            base_size = 112 + growth_state * 5
        width_scale = profile_width if width_scale is None else width_scale
        height_scale = profile_height if height_scale is None else height_scale
        body_scale = max(0.012, body_scale)
        visual_width = max(1, round(base_size * body_scale * depth_scale * camera_scale * width_scale))
        visual_height = max(1, round(base_size * body_scale * depth_scale * camera_scale * height_scale))
        scaled = self.sprites.scaled_frame(animation, time, visual_width, visual_height, variant=variant, progress=animation_progress)
        if scaled is None:
            return
        rect = scaled.get_rect()
        sprite_height = self.height if draw_height is None else draw_height
        rect.midbottom = (round(ground.x), round(ground.y - sprite_height * camera_scale) + 8)

        if draw_glow:
            glow_size = round(max(visual_width, visual_height) * (5.2 + growth_state * 0.14))
            alpha = round(min(120, 16 + growth_state * 18 + (28 if self.pulse_timer > 0 or self.channeling else 0)) * luminosity * 0.5)
            glow = make_radial_glow(glow_size, MYCELIUM, alpha)
            surface.blit(glow, glow.get_rect(center=rect.center))
        surface.blit(scaled, rect)

        if self.height > 2:
            shadow = pygame.Surface((max(1, round(54 * camera_scale)), max(1, round(18 * camera_scale))), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
            surface.blit(shadow, shadow.get_rect(center=(round(ground.x), round(ground.y + 3 * camera_scale))))

    def draw_geometry(self, surface, ground, growth_state, body_scale=1.0, visual_height=None):
        sprite_height = self.height if visual_height is None else visual_height
        scale = (1 + growth_state * 0.05) * max(0.012, body_scale)
        pygame.draw.ellipse(surface, (*MYCELIUM, 80), pygame.Rect(0, 0, round(110 * scale), round(80 * scale)).move(round(ground.x - 55 * scale), round(ground.y - 70 * scale)))
        stem = pygame.Rect(0, 0, round(18 * scale), round(38 * scale))
        stem.midbottom = (round(ground.x), round(ground.y - sprite_height))
        pygame.draw.ellipse(surface, STEM, stem)
        cap = pygame.Rect(0, 0, round(54 * scale), round(30 * scale))
        cap.midbottom = (round(ground.x), stem.top + 10)
        pygame.draw.ellipse(surface, CAP, cap)
