import pygame

from config import *


class MushroomSprites:
    FRAME_SIZE = 192
    VARIANT_BASES = list(MUSHROOM_ASPECT_PROFILES)
    SPECIES_PREFIXES = {
        "Detailed": "meshy_mushroom",
        "Psathyrella": "psathyrella",
        "Amanita": "amanita",
        "Puffball": "puffball",
        "Earthstar": "earthstar",
        "Mycena": "mycena",
        "Mycena Glow": "mycena_glow",
        "Entoloma": "entoloma",
    }
    SPECIES_FOLDERS = ["idle", "walk", "pulse_start", "pulse_loop", "pulse_end", "emerge", "burrow"]
    CLASSIC_VARIANT_BASES = [
        "mushroom_fruit_v3_var01",
        "mushroom_fruit_v3_var02",
        "mushroom_fruit_v3_var03",
        "mushroom_fruit_v3_var04",
        "mushroom_fruit_v3_var05",
        "mushroom_fruit_v3_var06",
        "mushroom_fruit_v3_var07",
        "mushroom_fruit_v3_var08",
    ]
    CLASSIC_VARIANT_MAP = {
        "wide": "mushroom_fruit_v3_var03",
        "neutral": "mushroom_fruit_v3_var01",
        "tall": "mushroom_fruit_v3_var07",
    }
    ANIMATION_FOLDERS = {
        "idle": "meshy_mushroom_idle_frames",
        "walk": "meshy_mushroom_walk_frames",
        "pulse_start": "meshy_mushroom_pulse_start_frames",
        "pulse_loop": "meshy_mushroom_pulse_loop_frames",
        "pulse_end": "meshy_mushroom_pulse_end_frames",
        "emerge": "meshy_mushroom_emerge_frames",
        "burrow": "meshy_mushroom_burrow_frames",
    }
    ANIMATION_META = {
        "idle": {"fps": MUSHROOM_ANIMATION_FPS, "loop": True},
        "walk": {"fps": MUSHROOM_ANIMATION_FPS, "loop": True},
        "pulse_start": {"fps": MUSHROOM_ANIMATION_FPS, "loop": False},
        "pulse_loop": {"fps": MUSHROOM_ANIMATION_FPS, "loop": True},
        "pulse_end": {"fps": MUSHROOM_ANIMATION_FPS, "loop": False},
        "emerge": {"fps": MUSHROOM_ANIMATION_FPS, "loop": False},
        "burrow": {"fps": MUSHROOM_ANIMATION_FPS, "loop": False},
    }
    CLASSIC_ANIMATION_MAP = {
        "idle": "idle",
        "walk": "walk",
        "pulse_start": "pulse",
        "pulse_loop": "pulse",
        "pulse_end": "pulse",
        "emerge": "pulse",
        "burrow": "pulse",
    }
    CLASSIC_ANIMATION_META = {
        "idle": {"fps": 7, "loop": True},
        "walk": {"fps": 12, "loop": True},
        "hop": {"fps": 10, "loop": True},
        "pulse": {"fps": 12, "loop": True},
    }

    def __init__(self):
        self.animations = {}
        self.variant_animations = {}
        self.classic_variant_animations = {}
        self.loaded_variant = "neutral"
        self.sprite_style = SPRITE_STYLE_OPTIONS[0]
        self.scale_cache = {}
        self.regen_sprites = []
        self._load_species_animations(self.SPECIES_PREFIXES[self.sprite_style])

    @property
    def available(self):
        return bool(self.animations)

    def load_variant(self, variant):
        return self.animations

    def _load_species_animations(self, prefix):
        self.animations = {}
        for folder in self.SPECIES_FOLDERS:
            name = f"{prefix}_{folder}_frames"
            frames = self.load_frames(name)
            if frames:
                self.animations[folder] = frames
        self._load_regen_sprites(prefix)

    def _load_regen_sprites(self, prefix):
        regen_dir = BASE_DIR / f"assets/sprites/{prefix}_regen_mini"
        if regen_dir.exists():
            self.regen_sprites = [pygame.image.load(path).convert_alpha()
                                  for path in sorted(regen_dir.glob("regen_mini_*.png"))]
        else:
            self.regen_sprites = []

    def set_style(self, style):
        if style not in SPRITE_STYLE_OPTIONS and style not in self.SPECIES_PREFIXES:
            style = SPRITE_STYLE_OPTIONS[0]
        if self.sprite_style != style:
            self.sprite_style = style
            self.scale_cache.clear()
            if style in self.SPECIES_PREFIXES:
                self._load_species_animations(self.SPECIES_PREFIXES[style])

    def cycle_style(self, direction=1):
        current = self.sprite_style if self.sprite_style in SPRITE_STYLE_OPTIONS else SPRITE_STYLE_OPTIONS[0]
        next_index = (SPRITE_STYLE_OPTIONS.index(current) + direction) % len(SPRITE_STYLE_OPTIONS)
        self.set_style(SPRITE_STYLE_OPTIONS[next_index])

    def classic_variant_for(self, variant):
        if variant in self.CLASSIC_VARIANT_BASES:
            return variant
        return self.CLASSIC_VARIANT_MAP.get(variant, self.CLASSIC_VARIANT_MAP["neutral"])

    def load_classic_variant(self, variant):
        variant = self.classic_variant_for(variant)
        cached = self.classic_variant_animations.get(variant)
        if cached:
            return cached
        animations = {}
        for animation in ("idle", "walk", "hop", "pulse"):
            frames = self.load_frames(f"{variant}_{animation}")
            if not frames:
                return None
            animations[animation] = frames
        self.classic_variant_animations[variant] = animations
        return animations

    def load_animation(self, name, preferred_base, fallback_base):
        for base_name in (preferred_base, fallback_base):
            frames = self.load_frames(base_name)
            if frames:
                self.animations[name] = frames
                return

    def load_frames(self, base_name):
        frame_dir = BASE_DIR / f"assets/sprites/{base_name}"
        if not frame_dir.exists():
            frame_dir = BASE_DIR / f"assets/sprites/{base_name}_frames"
        if frame_dir.exists():
            frames = [pygame.image.load(path).convert_alpha() for path in sorted(frame_dir.glob("*.png"))]
            if frames:
                if "walk" in base_name:
                    frames = frames[::2]
                return frames

        sheet_path = BASE_DIR / f"assets/sprites/{base_name}.png"
        if not sheet_path.exists():
            return []
        sheet = pygame.image.load(sheet_path).convert_alpha()
        width, height = sheet.get_size()
        frame_count = width // self.FRAME_SIZE
        frames = []
        for index in range(frame_count):
            rect = pygame.Rect(index * self.FRAME_SIZE, 0, self.FRAME_SIZE, height)
            frame = pygame.Surface((self.FRAME_SIZE, height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            frames.append(frame)
        return frames

    def frame_index(self, name, time, fps=None, variant=None, progress=None):
        if self.sprite_style == "Classic":
            classic_animation = self.CLASSIC_ANIMATION_MAP.get(name, "idle")
            animations = self.load_classic_variant(variant)
            if not animations:
                return None, None
            frames = animations.get(classic_animation) or animations.get("idle")
            meta = self.CLASSIC_ANIMATION_META.get(classic_animation, self.CLASSIC_ANIMATION_META["idle"])
        else:
            frames = self.animations.get(name) or self.animations.get("idle")
            meta = self.ANIMATION_META.get(name, self.ANIMATION_META["idle"])
        if not frames:
            return None, None
        if progress is not None:
            index = round(max(0.0, min(1.0, progress)) * (len(frames) - 1))
        else:
            fps = fps or meta["fps"]
            index = int(time * fps)
            if meta.get("loop", True):
                index %= len(frames)
            else:
                index = min(index, len(frames) - 1)
        return frames, index

    def frame(self, name, time, fps=None, variant=None, progress=None):
        frames, index = self.frame_index(name, time, fps, variant, progress)
        if frames is None:
            return None
        return frames[index]

    def scaled_frame(self, name, time, width, height, fps=None, variant=None, progress=None):
        frames, frame_index = self.frame_index(name, time, fps, variant, progress)
        if frames is None:
            return None
        width = max(1, round(width))
        height = max(1, round(height))
        cache_key = (self.sprite_style, variant, name, frame_index, width, height)
        scaled = self.scale_cache.get(cache_key)
        if scaled is None:
            scaled = pygame.transform.smoothscale(frames[frame_index], (width, height))
            self.scale_cache[cache_key] = scaled
            if len(self.scale_cache) > 1800:
                self.scale_cache.pop(next(iter(self.scale_cache)))
        return scaled


