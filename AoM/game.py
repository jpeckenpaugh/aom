import asyncio
import math
import random
import sys

import pygame

from assets import AssetManager
from autoguide import AutoGuide
from camera import Camera
from config import *
from entities import *
from input import InputHandler
from npcs import NPCManager
from phases import PhaseManager
from player import Player
from rendering import Renderer
from sprites import MushroomSprites
from ui import UIManager
from utils import *


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED)
        pygame.display.set_caption("Age of Mycology")
        self.clock = pygame.time.Clock()
        self.font_cache = {}
        self.title_texture_cache = {}
        self.assets = AssetManager(self)
        self.ui = UIManager(self)
        self.input = InputHandler(self)
        self.autoguide = AutoGuide(self)
        self.phases = PhaseManager(self)
        self.npcs = NPCManager(self)
        self.renderer = Renderer(self)
        self.font = self.assets.get_font(24)
        self.small_font = self.assets.get_font(18)
        self.title_font = self.assets.get_font(72, bold=True)
        self.title_small_font = self.assets.get_font(28)
        self.hud_corner_ornaments = self.assets.load_hud_corner_ornaments()
        self.options_gear_icon = self.assets.load_options_gear_icon()
        self.lumen_icon = self.assets.load_lumen_icon()
        self.lumen_spin_frames = self.assets.load_lumen_spin_frames()
        self.lumen_front_frame = self.assets.load_lumen_front_frame()
        self.root_spin_frames = self.assets.load_root_spin_frames()
        self.root_icon = self.assets.load_root_icon()
        self.shell_spin_frames = self.assets.load_shell_spin_frames()
        self.shell_icon = self.assets.load_shell_icon()
        self.crystal_spin_frames = self.assets.load_crystal_spin_frames()
        self.crystal_icon = self.assets.load_crystal_icon()
        self.acorn_spin_frames = self.assets.load_acorn_spin_frames()
        self.acorn_icon = self.assets.load_acorn_icon()
        self.amber_spin_frames = self.assets.load_amber_spin_frames()
        self.amber_icon = self.assets.load_amber_icon()
        self.ui_stone_texture = self.assets.load_ui_texture("stone_grain_512.png")
        self.ui_wood_texture = self.assets.load_ui_texture("wood_grain_512.png")
        self.top_stone_bar = self.assets.load_top_stone_bar()
        self.title_mushroom_texture = self.assets.load_title_mushroom_texture()
        self.camera = Camera()
        self.sprites = MushroomSprites()
        self.reveal_cache = {}
        self.spawn = pygame.Vector2(0, 0)
        self.puddle_pos = pygame.Vector2(-CAVE_RADIUS * 0.70, 0)
        self.puddle_drop_offset = pygame.Vector2(-18, -2)
        self.right_outlet_pos = pygame.Vector2(self.puddle_pos.x + 126, self.puddle_pos.y + 4)
        self.moss_spawn = pygame.Vector2(self.puddle_pos.x - 185, self.puddle_pos.y + 52)
        self.puddle_image = self.assets.load_puddle_image()
        self.player = Player(self.spawn, self.sprites)
        self.mycelial_overlay = self.assets.load_mycelial_overlay()
        self.floor_pebbles, self.floor_cracks = [], []
        self.pebble_sprites = self.assets.load_pebble_sprites()
        self.leaf_sprites = self.assets.load_leaf_sprites()
        self.fern_sprites = self.assets.load_fern_sprites()
        self.edge_pebbles = self.assets.make_edge_pebbles()
        self.edge_leaves = self.assets.make_edge_leaves()
        self.concentrate_rock = ConcentrateRock(self.right_outlet_pos.copy())
        self.concentrate_rock_image = self.assets.make_concentrate_rock_image()
        self.channel_cover_leaves = self.assets.make_channel_cover_leaves()
        self.pebble_waypoints = self.assets.make_pebble_waypoints()
        self.companion_waypoints = self.assets.make_companion_waypoints()
        self.concentrate_pebbles = self.assets.make_concentrate_pebbles()
        self.fern_fronds = self.assets.make_fern_fronds()
        self.selected_pebble = None
        self.selected_waypoint = None
        self.selected_waypoint_group = "primary"
        self.transit_destinations = self.assets.make_transit_destinations()
        self.selected_transit_destination = 0
        self.transit_origin = None
        self.transit_target = None
        self.transit_time = 0
        self.transit_used = False
        self.transit_unlocked_announced = False
        self.spawn_npcs_after_transit = False
        self.transit_prompt_open = False
        self.transit_targeting = False
        self.transit_button_rect = pygame.Rect(0, 0, 0, 0)
        self.npc_mushrooms = []
        self.player.sprite_variant = "neutral"
        self.collect_pebbles_02_complete = False
        self.collect_ferns_03_complete = False
        self.charge_stones_04_complete = False
        self.leaf_decals = self.assets.make_leaf_decals()
        self.leaf_quest_lumens = []
        self.lumens = self.make_lumens()
        self.lumen_count = 0
        self.root_count = 0
        self.shell_count = 0
        self.crystal_count = 0
        self.acorn_count = 0
        self.amber_count = 0
        self.mycelial_lumen_ready_time = 0.0
        self.growth_state = 0
        self.phase = "explore"
        self.charge_progress = 0
        self.cinematic_time = 0
        self.drop_timer = 1.4
        self.drop_active = False
        self.drop_progress = 0.0
        self.ripples = []
        self.elemental_spells = []
        self.elemental_cast_counts = {element: 0 for element, _ in ELEMENTS}
        self.concentrating = False
        self.concentrate_mode = None
        self.right_channel_active = False
        self.right_channel_reveal = 0.0
        self.intro_time = 0
        self.debug_overlay = False
        self.last_dt = 0.0
        self.ui_time = 0.0
        self.world_time = 0.0
        self.item_drawer_open = False
        self.item_drawer_t = 0.0
        self.selected_item = None
        self.item_drawer_close_rect = pygame.Rect(0, 0, 0, 0)
        self.resource_icon_rects = {}
        self.inventory_pagination_rects = []
        self.inventory_page = 0
        self.inventory_page_target = 0
        self.inventory_page_anim_t = 0.0
        self.framebuffer_key = FRAMEBUFFER_KEY
        self.framebuffer_warning = ""
        self.visual_quality = "Mobile/Browser" if WEB_BUILD else "High"
        preset = PRESETS[self.visual_quality]
        self.darkness_overlay_enabled = preset["darkness"]
        self.smooth_scaling_enabled = preset["smooth_scaling"]
        self.browser_fps_cap = preset["fps"]
        self.options_open = False
        self.options_fade = 0.0
        self.options_selected = 0
        self.options_tooltip_text = ""
        self.options_tooltip_previous = ""
        self.options_tooltip_fade = 1.0
        self.options_button_rect = pygame.Rect(0, 0, 0, 0)
        self.options_row_rects = []
        self.about_open = False
        self.about_fade = 0.0
        self.about_lines = []
        self.about_rect = pygame.Rect(0, 0, 0, 0)
        self.title_screen = True
        self.title_transition_time = 0.0
        self.title_exiting = False
        self.gameplay_fade = 1.0
        self.title_selected = 0
        self.title_start_rect = pygame.Rect(0, 0, 0, 0)
        self.title_options_rect = pygame.Rect(0, 0, 0, 0)
        self.title_exit_rect = pygame.Rect(0, 0, 0, 0)
        self.confirm_action = None
        self.confirm_display_action = None
        self.confirm_payload = None
        self.confirm_fade = 0.0
        self.end_game_fade_active = False
        self.end_game_fade_time = 0.0
        self.debug_draw_count = 0
        self.confirm_rect = pygame.Rect(0, 0, 0, 0)
        self.confirm_yes_rect = pygame.Rect(0, 0, 0, 0)
        self.confirm_no_rect = pygame.Rect(0, 0, 0, 0)
        self.confirm_selected = 1
        self.guidance_word = None
        self.guidance_time = 0.0
        self.guidance_seen_words = set()
        self.auto_guide_enabled = False
        self.auto_guide_speed_mode = "Off"
        self.auto_guide_idle_time = 0.0
        self.auto_guide_prompt_shown = False
        self.auto_guide_prompt_time = 0.0
        self.auto_guide_prompt_fade = 0.0
        self.auto_guide_prompt_countdown_active = False
        self.auto_guide_prompt_selected = 0
        self.auto_guide_prompt_rect = pygame.Rect(0, 0, 0, 0)
        self.auto_guide_start_rect = pygame.Rect(0, 0, 0, 0)
        self.auto_guide_dismiss_rect = pygame.Rect(0, 0, 0, 0)
        self.auto_guide_rest_timer = 0.0
        self.auto_guide_last_target = None
        self.auto_guide_last_rest_kind = "move"
        self.auto_guide_follow_target = None
        self.auto_guide_follow_anchor = None
        self.auto_guide_follow_timer = 0.0
        self.auto_guide_follow_step = AUTO_GUIDE_FOLLOW_STEP_RANGE[0]
        self.auto_guide_watch_target = None
        self.auto_guide_watch_last_pos = self.player.pos.copy()
        self.auto_guide_watch_last_delta = None
        self.auto_guide_watch_last_distance = None
        self.auto_guide_watch_time = 0.0
        self.auto_guide_watch_flip_count = 0
        self.auto_guide_pebble_id = None
        self.auto_guide_pebble_waypoint_group = None
        self.auto_guide_pebble_waypoint_id = None
        self.auto_guide_fern_id = None
        self.auto_guide_fern_leaf = None
        self.auto_guide_fern_slot = None
        self.auto_guide_stone_group = None
        self.auto_guide_stone_id = None
        self.auto_guide_stone_kind = None
        self.last_mouse_debug = ""
        self.last_mouse_debug_time = 0.0
        self.world_image_cache = {}
        self.sprite_shadow_cache = {}
        self.background_cache = {}
        self.running = True

    def __getattr__(self, name):
        for manager_name in ("assets", "ui", "input", "autoguide", "phases", "npcs", "renderer"):
            manager = self.__dict__.get(manager_name)
            if manager is None:
                continue
            for cls in type(manager).__mro__:
                if name in cls.__dict__:
                    return getattr(manager, name)
        raise AttributeError(name)

    def available_mushroom_variants(self):
        return MushroomSprites.VARIANT_BASES

    def random_mushroom_variant(self):
        return random.choice(self.available_mushroom_variants())

    def mushroom_variant_counts(self):
        variants = self.available_mushroom_variants()
        counts = {variant: 0 for variant in variants}
        player_variant = getattr(self.player, "sprite_variant", None)
        if player_variant in counts:
            counts[player_variant] += 1
        for npc in self.npc_mushrooms:
            if npc.sprite_variant in counts:
                counts[npc.sprite_variant] += 1
        return counts

    def choose_balanced_mushroom_variant(self):
        variants = self.available_mushroom_variants()
        counts = self.mushroom_variant_counts()
        minimum = min(counts[variant] for variant in variants)
        least_used = [variant for variant in variants if counts[variant] == minimum]
        return random.choice(least_used)

    def mushroom_profile_scales(self, variant):
        return MUSHROOM_ASPECT_PROFILES.get(variant, MUSHROOM_ASPECT_PROFILES["neutral"])

    def apply_mushroom_profile(self, mushroom):
        mushroom.width_scale, mushroom.height_scale = self.mushroom_profile_scales(mushroom.sprite_variant)
        mushroom.luminosity = 0.62 + random.random() * 0.18
        return mushroom

    def visual_depth_scale(self, world_pos, far_scale=DEPTH_VISUAL_FAR_SCALE, near_scale=DEPTH_VISUAL_NEAR_SCALE):
        t = (world_pos.y + CAVE_RADIUS) / (CAVE_RADIUS * 2)
        return far_scale + max(0.0, min(1.0, t)) * (near_scale - far_scale)

    def make_lumens(self):
        points = []
        radii = [420, 520, 360, 560, 470, 510, 390, 575, 450, 330]
        for index in range(REQUIRED_LUMEN):
            angle = -math.pi / 2 + index * math.tau / REQUIRED_LUMEN
            wobble = math.sin(index * 1.91) * 0.16
            radius = radii[index]
            points.append((math.cos(angle + wobble) * radius, math.sin(angle + wobble) * radius))
        return [LumenWisp(x, z) for x, z in points]

    def start_guidance_word(self, word):
        if not word or word in self.guidance_seen_words:
            return False
        self.guidance_word = word
        self.guidance_time = 0.0
        self.guidance_seen_words.add(word)
        return True

    def guidance_active(self):
        return self.guidance_word is not None

    def update_guidance_word(self, dt):
        if self.guidance_word is None:
            return
        self.guidance_time += dt
        if self.guidance_time >= GUIDANCE_TOTAL_SECONDS:
            self.guidance_word = None
            self.guidance_time = 0.0

    @property
    def item_drawer_visible(self):
        return self.item_drawer_open or self.item_drawer_t > 0.0

    def open_item_drawer(self, item_key):
        if not item_key:
            return False
        self.selected_item = item_key
        self.item_drawer_open = True
        self.options_open = False
        self.player.moving = False
        self.player.clear_walk_target()
        return True

    def close_item_drawer(self):
        if not self.item_drawer_visible:
            return False
        self.item_drawer_open = False
        return True




















    def reset(self):
        self.player.reset()
        self.npc_mushrooms = []
        self.player.sprite_variant = "neutral"
        self.lumens = self.make_lumens()
        self.lumen_count = 0
        self.root_count = 0
        self.shell_count = 0
        self.crystal_count = 0
        self.acorn_count = 0
        self.amber_count = 0
        self.mycelial_lumen_ready_time = 0.0
        self.growth_state = 0
        self.phase = "explore"
        self.charge_progress = 0
        self.cinematic_time = 0
        self.drop_timer = 1.4
        self.drop_active = False
        self.drop_progress = 0.0
        self.ripples = []
        self.elemental_spells = []
        self.elemental_cast_counts = {element: 0 for element, _ in ELEMENTS}
        self.concentrate_rock = ConcentrateRock(self.right_outlet_pos.copy())
        self.channel_cover_leaves = self.assets.make_channel_cover_leaves()
        self.pebble_waypoints = self.assets.make_pebble_waypoints()
        self.companion_waypoints = self.assets.make_companion_waypoints()
        self.concentrate_pebbles = self.assets.make_concentrate_pebbles()
        self.fern_fronds = self.assets.make_fern_fronds()
        self.leaf_decals = self.assets.make_leaf_decals()
        self.leaf_quest_lumens = []
        self.selected_pebble = None
        self.selected_waypoint = None
        self.selected_waypoint_group = "primary"
        self.transit_destinations = self.assets.make_transit_destinations()
        self.selected_transit_destination = 0
        self.transit_target = None
        self.transit_time = 0
        self.transit_used = False
        self.transit_unlocked_announced = False
        self.spawn_npcs_after_transit = False
        self.guidance_word = None
        self.guidance_time = 0.0
        self.guidance_seen_words = set()
        self.auto_guide_enabled = False
        self.auto_guide_speed_mode = "Off"
        self.auto_guide_idle_time = 0.0
        self.auto_guide_prompt_shown = False
        self.auto_guide_prompt_time = 0.0
        self.auto_guide_prompt_fade = 0.0
        self.auto_guide_prompt_countdown_active = False
        self.auto_guide_prompt_selected = 0
        self.auto_guide_rest_timer = 0.0
        self.auto_guide_last_target = None
        self.auto_guide_last_rest_kind = "move"
        self.auto_guide_follow_target = None
        self.auto_guide_follow_anchor = None
        self.auto_guide_follow_timer = 0.0
        self.auto_guide_follow_step = AUTO_GUIDE_FOLLOW_STEP_RANGE[0]
        self.auto_guide_watch_target = None
        self.auto_guide_watch_last_pos = self.player.pos.copy()
        self.auto_guide_watch_last_delta = None
        self.auto_guide_watch_last_distance = None
        self.auto_guide_watch_time = 0.0
        self.auto_guide_watch_flip_count = 0
        self.auto_guide_pebble_id = None
        self.auto_guide_pebble_waypoint_group = None
        self.auto_guide_pebble_waypoint_id = None
        self.auto_guide_fern_id = None
        self.auto_guide_fern_leaf = None
        self.auto_guide_fern_slot = None
        self.auto_guide_stone_group = None
        self.auto_guide_stone_id = None
        self.auto_guide_stone_kind = None
        self.collect_pebbles_02_complete = False
        self.collect_ferns_03_complete = False
        self.charge_stones_04_complete = False
        self.concentrating = False
        self.concentrate_mode = None
        self.right_channel_active = False
        self.right_channel_reveal = 0.0
        self.intro_time = 0
        self.title_transition_time = 0.0
        self.title_exiting = False
        self.gameplay_fade = 1.0
        self.options_open = False
        self.options_fade = 0.0
        self.options_tooltip_text = ""
        self.options_tooltip_previous = ""
        self.options_tooltip_fade = 1.0
        self.about_open = False
        self.about_fade = 0.0
        self.about_lines = []
        self.confirm_action = None
        self.confirm_display_action = None
        self.confirm_payload = None
        self.confirm_fade = 0.0
        self.end_game_fade_active = False
        self.end_game_fade_time = 0.0
        self.item_drawer_open = False
        self.item_drawer_t = 0.0
        self.selected_item = None
        self.item_drawer_close_rect = pygame.Rect(0, 0, 0, 0)
        self.resource_icon_rects = {}
        self.inventory_pagination_rects = []
        self.inventory_page = 0
        self.inventory_page_target = 0
        self.inventory_page_anim_t = 0.0
        self.world_image_cache.clear()











    def run(self):
        while self.running:
            dt = self.clock.tick(effective_fps(self.browser_fps_cap)) / 1000
            self.last_dt = dt
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    async def run_async(self):
        while self.running:
            dt = self.clock.tick(effective_fps(self.browser_fps_cap)) / 1000
            self.last_dt = dt
            self.handle_events()
            self.update(dt)
            self.draw()
            await asyncio.sleep(0)
        pygame.quit()



















































































    def update(self, dt):
        self.ui_time += dt
        if self.inventory_page_anim_t > 0 and self.inventory_page != self.inventory_page_target:
            self.inventory_page_anim_t += dt / INVENTORY_PAGE_ANIM_SECONDS
            if self.inventory_page_anim_t >= 1.0:
                self.inventory_page_anim_t = 0.0
                self.inventory_page = self.inventory_page_target
        if self.end_game_fade_active:
            self.end_game_fade_time = min(END_GAME_FADE_SECONDS, self.end_game_fade_time + dt)
            if self.end_game_fade_time >= END_GAME_FADE_SECONDS:
                self.finish_end_game_transition()
            return
        target_options_fade = 1.0 if self.options_open else 0.0
        fade_step = dt / MENU_FADE_SECONDS
        if self.options_fade < target_options_fade:
            self.options_fade = min(target_options_fade, self.options_fade + fade_step)
        elif self.options_fade > target_options_fade:
            self.options_fade = max(target_options_fade, self.options_fade - fade_step)
        target_confirm_fade = 1.0 if self.confirm_action is not None else 0.0
        if self.confirm_fade < target_confirm_fade:
            self.confirm_fade = min(target_confirm_fade, self.confirm_fade + fade_step)
        elif self.confirm_fade > target_confirm_fade:
            self.confirm_fade = max(target_confirm_fade, self.confirm_fade - fade_step)
            if self.confirm_fade <= 0:
                self.confirm_display_action = None
        target_about_fade = 1.0 if self.about_open else 0.0
        if self.about_fade < target_about_fade:
            self.about_fade = min(target_about_fade, self.about_fade + fade_step)
        elif self.about_fade > target_about_fade:
            self.about_fade = max(target_about_fade, self.about_fade - fade_step)
        tooltip_step = dt / TOOLTIP_FADE_SECONDS
        if self.options_tooltip_fade < 1.0:
            self.options_tooltip_fade = min(1.0, self.options_tooltip_fade + tooltip_step)
        target_auto_prompt_fade = 1.0 if self.auto_guide_prompt_open() else 0.0
        if self.auto_guide_prompt_fade < target_auto_prompt_fade:
            self.auto_guide_prompt_fade = min(target_auto_prompt_fade, self.auto_guide_prompt_fade + fade_step)
        elif self.auto_guide_prompt_fade > target_auto_prompt_fade:
            self.auto_guide_prompt_fade = max(target_auto_prompt_fade, self.auto_guide_prompt_fade - fade_step)
        if self.title_screen:
            if self.title_exiting:
                self.title_transition_time = max(0.0, self.title_transition_time - dt)
            else:
                self.title_transition_time = min(TITLE_IN_TOTAL_FADE_SECONDS, self.title_transition_time + dt)
            if self.title_exiting and self.title_transition_time <= 0:
                self.finish_start_game()
        if self.title_screen:
            self.last_mouse_debug_time = max(0.0, self.last_mouse_debug_time - dt)
            return
        if self.gameplay_fade < 1.0:
            self.gameplay_fade = min(1.0, self.gameplay_fade + dt / GAMEPLAY_FADE_SECONDS)
        drawer_target = 1.0 if self.item_drawer_open else 0.0
        drawer_step = dt / ITEM_DRAWER_SECONDS
        if self.item_drawer_t < drawer_target:
            self.item_drawer_t = min(drawer_target, self.item_drawer_t + drawer_step)
        elif self.item_drawer_t > drawer_target:
            self.item_drawer_t = max(drawer_target, self.item_drawer_t - drawer_step)
            if self.item_drawer_t <= 0:
                self.selected_item = None
        if self.item_drawer_visible:
            self.concentrating = False
            self.concentrate_mode = None
            self.concentrate_rock.held = False
            self.player.moving = False
            self.player.clear_walk_target()
            self.last_mouse_debug_time = max(0.0, self.last_mouse_debug_time - dt)
            return
        self.world_time += dt
        if self.guidance_active():
            self.update_guidance_word(dt)
            self.concentrating = False
            self.concentrate_mode = None
            self.concentrate_rock.held = False
            self.player.moving = False
            self.player.clear_walk_target()
            self.last_mouse_debug_time = max(0.0, self.last_mouse_debug_time - dt)
            return
        if self.auto_guide_prompt_open():
            self.update_auto_guide_prompt_countdown(dt)
            self.player.moving = False
            self.last_mouse_debug_time = max(0.0, self.last_mouse_debug_time - dt)
            return
        self.intro_time += dt
        self.player.begin_frame()
        try:
            keys = pygame.key.get_pressed()
            if self.controls_enabled:
                if not self.options_open:
                    speed_scale = PLAYER_CHARGE_MOVE_MULTIPLIER if self.player_charge_resistance_active() else 1.0
                    auto_walk_speed_scale = 1.0
                    if self.auto_guide_enabled and self.auto_guide_speed_mode == "Slow":
                        auto_walk_speed_scale = AUTO_GUIDE_SLOW_SPEED_SCALE
                    elif self.auto_guide_enabled and self.auto_guide_speed_mode == "Fast":
                        auto_walk_speed_scale = AUTO_GUIDE_FAST_SPEED_SCALE
                    self.player.update(keys, dt, speed_scale, auto_walk_speed_scale)
                self.update_auto_guide(dt, keys)
                if self.concentrating and not self.options_open:
                    self.update_concentrate_action(dt)
            else:
                self.concentrating = False
                self.concentrate_rock.held = False
                self.player.pulse_timer = 0
                if not self.story_beat_locked:
                    self.update_auto_guide(dt, keys)
            if self.story_beat_locked:
                self.concentrating = False
                self.concentrate_mode = None
                self.concentrate_rock.held = False
                self.player.moving = False
                self.player.clear_walk_target()
                camera_target, camera_zoom, camera_speed = self.camera_target()
                self.camera.update(camera_target, camera_zoom, camera_speed, dt)
                self.last_mouse_debug_time = max(0.0, self.last_mouse_debug_time - dt)
                if self.phase in TRANSIT_UNLOCK_PHASES:
                    self.update_transit(dt)
                else:
                    self.update_feed_cinematic(dt)
                return
            self.concentrate_rock.sway_phase += dt * 2.6
            if self.right_channel_active:
                self.right_channel_reveal = min(1.0, self.right_channel_reveal + dt / RIGHT_CHANNEL_REVEAL_SECONDS)
            for pebble in self.concentrate_pebbles:
                pebble.sway_phase += dt * 2.8
            self.update_npc_mushrooms(dt)
            self.update_npc_channel_states(dt)
            self.update_moving_pebbles(dt)
            self.update_mushroom_terrain_lifts(dt)
            self.update_channel_cover_leaves(dt)
            self.update_moving_ferns(dt)
            self.update_water_beat(dt)
            self.update_elemental_spells(dt)
            self.update_regen_mushrooms(dt)
            self.update_waypoint_visual_charges(dt)
            self.update_leaf_quest_lumens(dt)
            self.last_mouse_debug_time = max(0.0, self.last_mouse_debug_time - dt)
            camera_target, camera_zoom, camera_speed = self.camera_target()
            self.camera.update(camera_target, camera_zoom, camera_speed, dt)
            for lumen in self.lumens:
                lumen.update(dt, self.post_intro_reveal > 0.25 and self.lumen_is_on_screen(lumen))

            if not self.intro_complete:
                return
            if self.phase in (*TRANSIT_UNLOCK_PHASES, "transit_disappear", "transit_pan", "transit_appear"):
                self.update_transit(dt)
                return
            if self.phase in ("feed_complete_focus", "feed_complete_return", "concentrate_unlock"):
                self.update_feed_cinematic(dt)
                return

            for lumen in self.lumens:
                if not lumen.collected and lumen.distance_to(self.player.pos.x, self.player.pos.y) < 62:
                    lumen.collect()
                    self.lumen_count += 1
                    self.player.trigger_pulse()

            self.growth_state = min(4, self.lumen_count // 3)
            all_lumen_collected = self.lumen_count >= REQUIRED_LUMEN
            if all_lumen_collected:
                self.mycelial_lumen_ready_time = min(MYCELIAL_LUMEN_READY_FADE_SECONDS, self.mycelial_lumen_ready_time + dt)
            else:
                self.mycelial_lumen_ready_time = 0.0
            at_mycelial = self.player.pos.distance_to(self.spawn) < MYCELIAL_ACTIVATION_RADIUS
            if self.phase == "explore" and all_lumen_collected and at_mycelial:
                self.charge_progress = min(1, self.charge_progress + dt / CHARGE_SECONDS)
                self.player.request_channel()
                self.player.moving = False
                if self.charge_progress >= 1:
                    self.root_count += 1
                    self.phase = "feed"
                    self.spawn_leaf_quest_lumens()
                    if self.auto_guide_enabled:
                        self.auto_guide_rest_timer = 1.0
            elif self.phase == "explore" and not at_mycelial:
                self.charge_progress = max(0, self.charge_progress - dt * 0.35)
            elif self.phase == "feed":
                self.update_leaf_feeding(dt)
            if self.phase == "transit" and self.collect_ferns_03_complete and not self.charge_stones_04_complete:
                self.update_player_stone_charging(dt)
        finally:
            self.player.update_channel_state(dt)









































































































































































