import math
import random

import pygame

from config import *
from entities import *
from game_backed import GameBackedManager
from atlas import default_atlas_index


class AssetManager(GameBackedManager):
    def __init__(self, game):
        super().__init__(game)
        self.atlas_index = default_atlas_index()
        self.spin_fps = {}

    def _load_spin_frames(self, name, pattern):
        """Load a collectible spin set from the packed atlas or its frame dir.

        Atlas sets ship the reduced web-10fps frames; ``spin_fps`` records the
        manifest playback rate so the renderer can keep the native spin
        duration. Missing atlases and missing dirs both degrade to an empty
        list (the renderer then falls back to its static icon path).
        """
        sprite_path = f"assets/sprites/collectibles/{name}_spin"
        entry = self.atlas_index.entry(sprite_path)
        if entry is not None:
            frames = self.atlas_index.load_frames(sprite_path)
            if frames:
                self.spin_fps[name] = entry.get("profile_fps") or ITEM_SPIN_FPS
                return frames
        frame_dir = BASE_DIR / sprite_path
        if not frame_dir.exists():
            return []
        frames = []
        for path in sorted(frame_dir.glob(pattern)):
            try:
                frames.append(pygame.image.load(path).convert_alpha())
            except pygame.error:
                return []
        return frames

    def get_font(self, size, bold=False, italic=False):
        key = (int(size), bool(bold), bool(italic))
        cached = self.font_cache.get(key)
        if cached is not None:
            return cached
        path = FONT_FILES.get((bool(bold), bool(italic)), FONT_FILES[(False, False)])
        try:
            font = pygame.font.Font(str(path), int(size))
        except (FileNotFoundError, OSError, pygame.error):
            font = pygame.font.SysFont("georgia", int(size), bold=bool(bold), italic=bool(italic))
        self.font_cache[key] = font
        return font
    def load_hud_corner_ornaments(self):
        path = BASE_DIR / "assets/sprites/hud/wood_corner_ornament_180.png"
        if not path.exists():
            return {}
        try:
            top_right = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return {}
        top_right = pygame.transform.smoothscale(
            top_right,
            (max(1, top_right.get_width() // 2), max(1, top_right.get_height() // 2)),
        )
        return {
            "top_left": pygame.transform.flip(top_right, True, False),
            "top_right": top_right,
            "bottom_left": pygame.transform.flip(top_right, True, True),
            "bottom_right": pygame.transform.flip(top_right, False, True),
        }
    def load_options_gear_icon(self):
        path = BASE_DIR / "assets/sprites/hud/stone_gear.png"
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (30, 30))
    def load_lumen_icon(self):
        path = BASE_DIR / "assets/sprites/hud/lumen.png"
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (34, 34))
    def load_lumen_spin_frames(self):
        return self._load_spin_frames("lumen", "lumen_*.png")
    def load_lumen_front_frame(self):
        path = BASE_DIR / "assets/sprites/collectibles/lumen_front/lumen_00.png"
        if not path.exists():
            return []
        try:
            return [pygame.image.load(path).convert_alpha()]
        except pygame.error:
            return []
    def load_root_spin_frames(self):
        return self._load_spin_frames("root", "root_*.png")
    def load_root_icon(self):
        path = BASE_DIR / "assets/sprites/hud/root_icon.png"
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (36, 36))
    def load_shell_icon(self):
        path = BASE_DIR / "assets/sprites/hud/glass_snail_shell.png"
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (36, 34))
    def load_crystal_spin_frames(self):
        return self._load_spin_frames("crystal", "crystal_*.png")
    def load_shell_spin_frames(self):
        return self._load_spin_frames("shell", "shell_*.png")
    def load_crystal_icon(self):
        path = BASE_DIR / "assets/sprites/hud/quartz_crystal.png"
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (28, 40))
    def load_acorn_spin_frames(self):
        return self._load_spin_frames("acorn", "acorn_*.png")
    def load_acorn_icon(self):
        path = BASE_DIR / "assets/sprites/hud/acorn.png"
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (38, 34))
    def load_amber_spin_frames(self):
        return self._load_spin_frames("amber", "amber_*.png")
    def load_amber_icon(self):
        path = BASE_DIR / "assets/sprites/hud/amber_shard.png"
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (28, 40))
    def load_ui_texture(self, filename):
        path = BASE_DIR / f"assets/sprites/hud/patterns/{filename}"
        if not path.exists():
            return None
        try:
            return pygame.image.load(path).convert()
        except pygame.error:
            return None
    def load_top_stone_bar(self):
        if self.ui_stone_texture is None:
            return None
        return self.make_stone_bar(SCREEN_WIDTH, 6, 4)
    def make_stone_bar(self, width, top_height, shadow_height):
        if self.ui_stone_texture is None or width <= 0:
            return None
        source = self.ui_stone_texture
        bar = pygame.Surface((width, top_height + shadow_height), pygame.SRCALPHA)
        source_width = source.get_width()
        for x in range(0, width, source_width):
            strip_width = min(source_width, width - x)
            bar.blit(source, (x, 0), pygame.Rect(0, 0, strip_width, top_height))
            shadow = source.subsurface(pygame.Rect(0, top_height, strip_width, shadow_height)).copy()
            shadow.fill((92, 88, 80), special_flags=pygame.BLEND_RGB_MULT)
            bar.blit(shadow, (x, top_height))
        return bar
    def load_title_mushroom_texture(self):
        path = BASE_DIR / "assets/sprites/hud/patterns/mushroom_grain_512.png"
        if not path.exists():
            return None
        try:
            return pygame.image.load(path).convert()
        except pygame.error:
            return None
    def render_textured_title_text(self, font, text, texture_offset=(0, 0)):
        if self.title_mushroom_texture is None:
            return None
        mask = font.render(text, True, (255, 255, 255))
        width, height = mask.get_size()
        if width <= 0 or height <= 0:
            return mask.convert_alpha()
        key = (id(font), text, width, height, texture_offset)
        cached = self.title_texture_cache.get(key)
        if cached is not None:
            return cached
        texture = self.title_mushroom_texture
        textured = pygame.Surface((width, height), pygame.SRCALPHA)
        texture_width, texture_height = texture.get_size()
        offset_x, offset_y = texture_offset
        start_x = -(offset_x % texture_width)
        start_y = -(offset_y % texture_height)
        for y in range(start_y, height, texture_height):
            for x in range(start_x, width, texture_width):
                textured.blit(texture, (x, y))
        textured.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.title_texture_cache[key] = textured
        return textured
    def load_mycelial_overlay(self):
        path = BASE_DIR / "assets/sprites/mycelial_center_overlay.png"
        if not path.exists():
            return None
        return pygame.image.load(path).convert_alpha()
    def load_puddle_image(self):
        for path in (
            BASE_DIR / "assets/sprites/puddle_v2.png",
            BASE_DIR / "assets/sprites/puddle_v1.png",
        ):
            if path.exists():
                return pygame.image.load(path).convert_alpha()
        return None
    def load_pebble_sprites(self):
        frame_dir = BASE_DIR / "assets/sprites/polyhaven_pebbles_v1"
        if not frame_dir.exists():
            return []
        return [pygame.image.load(path).convert_alpha() for path in sorted(frame_dir.glob("pebble_*.png"))]
    def load_leaf_sprites(self):
        frame_dir = BASE_DIR / "assets/sprites/leaf_dead_026_v1_variants"
        if not frame_dir.exists():
            return []
        return [pygame.image.load(path).convert_alpha() for path in sorted(frame_dir.glob("*.png"))]
    def load_fern_sprites(self):
        frame_dir = BASE_DIR / "assets/sprites/fern_frond_v1_variants"
        if not frame_dir.exists():
            return []
        return [pygame.image.load(path).convert_alpha() for path in sorted(frame_dir.glob("*.png"))]
    def make_edge_pebbles(self):
        if not self.pebble_sprites:
            return []

        rng = random.Random(137)
        decals = []
        outer_count = 250
        inner_count = 95
        for index in range(outer_count):
            angle = index * math.tau / outer_count + rng.uniform(-0.028, 0.028)
            radius = CAVE_RADIUS + rng.uniform(-70, 46) + math.sin(angle * 5.0) * 18
            image = self.prepare_pebble_image(
                rng.choice(self.pebble_sprites),
                scale=rng.uniform(0.38, 0.82),
                angle=rng.uniform(0, 360),
                tint=rng.choice(((0.62, 0.66, 0.68), (0.55, 0.58, 0.57), (0.66, 0.61, 0.54), (0.48, 0.52, 0.55))),
                alpha=rng.randint(184, 238),
            )
            decals.append(PebbleDecal(math.cos(angle) * radius, math.sin(angle) * radius, image))

        for index in range(inner_count):
            angle = index * math.tau / inner_count + rng.uniform(-0.045, 0.045)
            radius = CAVE_RADIUS - rng.uniform(95, 225) + math.sin(angle * 7.0 + 0.8) * 25
            image = self.prepare_pebble_image(
                rng.choice(self.pebble_sprites),
                scale=rng.uniform(0.22, 0.48),
                angle=rng.uniform(0, 360),
                tint=rng.choice(((0.78, 0.78, 0.73), (0.66, 0.70, 0.69), (0.74, 0.68, 0.58), (0.58, 0.62, 0.60))),
                alpha=rng.randint(132, 196),
            )
            decals.append(PebbleDecal(math.cos(angle) * radius, math.sin(angle) * radius, image, loose_material=True))

        return sorted(decals, key=lambda pebble: pebble.z)
    def make_edge_leaves(self):
        if not self.leaf_sprites:
            return []

        rng = random.Random(181)
        decals = []
        count = 100
        for index in range(count):
            angle = index * math.tau / count + rng.uniform(-0.04, 0.04)
            radius = CAVE_RADIUS + rng.uniform(-92, 70) + math.sin(angle * 6.0 + 1.3) * 30
            image = self.prepare_leaf_image(
                rng.choice(self.leaf_sprites),
                scale=rng.uniform(0.18, 0.48),
                angle=rng.uniform(0, 360),
                tint=rng.choice(((0.62, 0.52, 0.38), (0.48, 0.43, 0.32), (0.56, 0.47, 0.28), (0.42, 0.45, 0.35))),
                alpha=rng.randint(128, 198),
            )
            decals.append(EdgeLeafDecal(math.cos(angle) * radius, math.sin(angle) * radius, image))
        return sorted(decals, key=lambda leaf: leaf.z)
    def prepare_pebble_image(self, source, scale, angle, tint, alpha):
        width = max(8, round(source.get_width() * scale))
        height = max(8, round(source.get_height() * scale))
        image = pygame.transform.smoothscale(source, (width, height))
        image = pygame.transform.rotate(image, angle)
        image.fill((round(255 * tint[0]), round(255 * tint[1]), round(255 * tint[2]), alpha), special_flags=pygame.BLEND_RGBA_MULT)
        return image
    def make_concentrate_rock_image(self):
        if not self.pebble_sprites:
            return None
        source = self.pebble_sprites[-1]
        return self.prepare_pebble_image(
            source,
            scale=0.78,
            angle=-14,
            tint=(0.58, 0.60, 0.57),
            alpha=255,
        )
    def make_pebble_waypoints(self):
        waypoints = []
        for index in range(5):
            angle = math.radians(-54 + index * 72)
            pos = pygame.Vector2(math.cos(angle) * PEBBLE_WAYPOINT_RADIUS, math.sin(angle) * PEBBLE_WAYPOINT_RADIUS)
            element, color = ELEMENTS[index]
            waypoints.append(PebbleWaypoint(pos, element, color))
        return waypoints
    def make_companion_waypoints(self):
        waypoints = []
        for index, primary in enumerate(self.pebble_waypoints):
            radial = primary.pos.normalize() if primary.pos.length_squared() else pygame.Vector2(1, 0)
            tangent = pygame.Vector2(-radial.y, radial.x)
            for side in (-1, 1):
                pos = primary.pos + tangent * side * 118 + radial * 76
                waypoints.append(PebbleWaypoint(pos, primary.element, primary.color))
        return waypoints
    def make_transit_destinations(self):
        destinations = [self.spawn.copy()]
        destinations.extend(waypoint.pos.copy() for waypoint in self.pebble_waypoints)
        destinations.append(self.right_outlet_pos + pygame.Vector2(-45, 80))
        return destinations
    def make_concentrate_pebbles(self):
        if not self.pebble_sprites:
            return []
        rng = random.Random(233)
        pebbles = []
        for index in range(CONCENTRATE_PEBBLE_COUNT):
            angle = math.radians(-54 + index * 360 / CONCENTRATE_PEBBLE_COUNT + rng.uniform(-8, 8))
            radius = CAVE_RADIUS - rng.uniform(190, 285)
            image = self.prepare_pebble_image(
                self.pebble_sprites[index % len(self.pebble_sprites)],
                scale=rng.uniform(0.68, 1.08),
                angle=rng.uniform(0, 360),
                tint=rng.choice(((0.78, 0.78, 0.73), (0.68, 0.71, 0.69), (0.72, 0.66, 0.56))),
                alpha=238,
            )
            pebbles.append(ConcentratePebble(index, pygame.Vector2(math.cos(angle) * radius, math.sin(angle) * radius), image))
        return pebbles
    def make_fern_fronds(self):
        if not self.fern_sprites:
            return []
        rng = random.Random(311)
        fronds = []
        for index in range(FERN_FROND_COUNT):
            angle = math.radians(index * 360 / FERN_FROND_COUNT + rng.uniform(-4.5, 4.5))
            radius = CAVE_RADIUS - rng.uniform(110, 235)
            source = self.fern_sprites[index % len(self.fern_sprites)]
            image = source.copy()
            image.set_alpha(rng.randint(178, 232))
            fronds.append(FernFrond(index, pygame.Vector2(math.cos(angle) * radius, math.sin(angle) * radius), image))
        return fronds
    def prepare_leaf_image(self, source, scale, angle, tint, alpha):
        width = max(8, round(source.get_width() * scale))
        height = max(8, round(source.get_height() * scale))
        image = pygame.transform.smoothscale(source, (width, height))
        image = pygame.transform.rotate(image, angle)
        image.fill((round(255 * tint[0]), round(255 * tint[1]), round(255 * tint[2]), alpha), special_flags=pygame.BLEND_RGBA_MULT)
        return image
    def make_channel_cover_leaves(self):
        if not self.leaf_sprites:
            return []
        junction = self.right_channel_paths()[0]
        rock_offsets = (pygame.Vector2(-18, -8), pygame.Vector2(22, 12))
        target_offsets = (pygame.Vector2(-92, -18), pygame.Vector2(-22, 26))
        angles = (-18, 32)
        leaves = []
        for index in range(2):
            image = self.prepare_leaf_image(
                self.leaf_sprites[index % len(self.leaf_sprites)],
                scale=2.88,
                angle=angles[index],
                tint=(0.78, 0.58, 0.34),
                alpha=238,
            )
            leaves.append(ChannelCoverLeaf(self.right_outlet_pos + rock_offsets[index], junction + target_offsets[index], image))
        return leaves
    def make_leaf_decals(self):
        images = self.leaf_sprites[:5]
        if len(images) < 5:
            return []

        decals = []
        radius = CAVE_RADIUS * 0.5
        for index, image in enumerate(images):
            angle = -math.pi / 2 + index * math.tau / 5
            decals.append(LeafDecal(math.cos(angle) * radius, math.sin(angle) * radius, image, self.make_leaf_mycelial_image(index), [None, None]))
        return decals
    def make_leaf_mycelial_image(self, index):
        if not self.mycelial_overlay:
            return None
        scale = 0.68
        width = max(8, round(self.mycelial_overlay.get_width() * scale))
        height = max(8, round(self.mycelial_overlay.get_height() * scale))
        image = pygame.transform.smoothscale(self.mycelial_overlay, (width, height))
        image = pygame.transform.rotate(image, 17 + index * 41)
        return image
