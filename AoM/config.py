import os
from pathlib import Path

from game_platform import WEB_BUILD, browser_framebuffer_key


BASE_SCREEN_WIDTH = 1280
BASE_SCREEN_HEIGHT = 720
FRAMEBUFFER_OPTIONS = {
    "standard": ("Standard (960x540)", 960, 540),
    "high": ("High (1280x720)", 1280, 720),
}
FRAMEBUFFER_ORDER = ("standard", "high")


FRAMEBUFFER_KEY = browser_framebuffer_key(FRAMEBUFFER_OPTIONS)
native_resolution = os.environ.get("AOM_NATIVE_RESOLUTION", "").strip().lower()
if not WEB_BUILD and native_resolution:
    for key, (_, width, height) in FRAMEBUFFER_OPTIONS.items():
        if native_resolution in (key, str(height), f"{width}x{height}"):
            FRAMEBUFFER_KEY = key
            break
SCREEN_WIDTH = FRAMEBUFFER_OPTIONS[FRAMEBUFFER_KEY][1]
SCREEN_HEIGHT = FRAMEBUFFER_OPTIONS[FRAMEBUFFER_KEY][2]
FPS = 60
BROWSER_FPS = 30
BROWSER_FPS_OPTIONS = (10, 30, 60)
WEB_FIXED_FPS = 10


def effective_fps(fps):
    """Resolve a requested frame cap for the current build.

    The web (PygBag) build ships the reduced 10 fps frame set, so it is pinned to
    ``WEB_FIXED_FPS`` regardless of the requested value; native builds keep the
    requested cap.
    """
    return WEB_FIXED_FPS if WEB_BUILD else fps


# AOM-34: the web-10fps build ships packed grid atlases (tools/pack_web_atlas.py)
# instead of per-frame PNG dirs. The loader consults ``assets/atlas/manifest.json``
# only on the web build; native builds keep the source frame dirs and the
# horizontal-strip fallback, so their frames and playback rate are unchanged.
WEB_ATLAS_ENABLED = WEB_BUILD


MENU_FADE_SECONDS = 1.0
GAMEPLAY_FADE_SECONDS = 1.0
TITLE_IN_BACKGROUND_FADE_SECONDS = 1.0
TITLE_IN_TEXT_FADE_SECONDS = 2.0
TITLE_IN_MENU_FADE_SECONDS = 2.0
TITLE_IN_TOTAL_FADE_SECONDS = TITLE_IN_BACKGROUND_FADE_SECONDS + TITLE_IN_TEXT_FADE_SECONDS + TITLE_IN_MENU_FADE_SECONDS
TITLE_OUT_BACKGROUND_FADE_SECONDS = 1.0
TITLE_OUT_TEXT_FADE_SECONDS = 1.0
TITLE_OUT_MENU_FADE_SECONDS = 1.0
TITLE_OUT_TOTAL_FADE_SECONDS = TITLE_OUT_BACKGROUND_FADE_SECONDS + TITLE_OUT_TEXT_FADE_SECONDS + TITLE_OUT_MENU_FADE_SECONDS
END_GAME_FADE_SECONDS = 2.0
TOOLTIP_FADE_SECONDS = 0.26
GUIDANCE_FADE_IN_SECONDS = 0.65
GUIDANCE_HOLD_SECONDS = 1.25
GUIDANCE_FADE_OUT_SECONDS = 0.75
GUIDANCE_TOTAL_SECONDS = GUIDANCE_FADE_IN_SECONDS + GUIDANCE_HOLD_SECONDS + GUIDANCE_FADE_OUT_SECONDS
ITEM_DRAWER_SECONDS = 0.28
ITEM_DRAWER_HEIGHT = 360
ITEM_SPIN_FPS = 16
INVENTORY_PAGE_COUNT = 4
INVENTORY_PAGE_ANIM_SECONDS = 0.3
INVENTORY_PAGINATION_WIDTH = 30
INVENTORY_PAGE_GRID_WIDTH = 320
INVENTORY_SECTION_WIDTH = INVENTORY_PAGINATION_WIDTH + INVENTORY_PAGE_GRID_WIDTH
BASE_DIR = Path(__file__).resolve().parent
FONT_DIR = BASE_DIR / "assets" / "fonts" / "merriweather"
FONT_FILES = {
    (False, False): FONT_DIR / "Merriweather-Regular.ttf",
    (True, False): FONT_DIR / "Merriweather-Bold.ttf",
    (False, True): FONT_DIR / "Merriweather-Italic.ttf",
    (True, True): FONT_DIR / "Merriweather-BoldItalic.ttf",
}
BROWSER_SURFACE_BUCKET = 24
BROWSER_MAX_GLOW_SIZE = 720
BROWSER_MAX_REVEAL_RADIUS = 680
BROWSER_WORLD_CACHE_LIMIT = 320
BROWSER_WORLD_CACHE_MAX_PIXELS = 140_000
SPRITE_SHADOW_CACHE_LIMIT = 180
NATIVE_WORLD_CACHE_LIMIT = 900
NATIVE_WORLD_CACHE_MAX_PIXELS = 260_000
BACKGROUND_CACHE_LIMIT = 18
BACKGROUND_CAMERA_BUCKET = 1
BACKGROUND_ZOOM_BUCKET = 0.005
WORLD_CULL_MARGIN = 240
NPC_ANIMATION_FPS = 30
FRAMEBUFFER_OPTIONS_ROWS = ("Framebuffer:",) if WEB_BUILD else ()
FPS_OPTIONS_ROWS = () if WEB_BUILD else ("FPS Cap",)
BACK_OPTIONS_ROWS = ("Close",)
GRAPHICS_OPTIONS_ROWS = FPS_OPTIONS_ROWS + ("Darkness Overlay", "Smooth Scaling", "Sprite Style") + FRAMEBUFFER_OPTIONS_ROWS
TITLE_OPTIONS_ROWS = (
    "PRESET",
    "Preset",
    "GRAPHICS",
    *GRAPHICS_OPTIONS_ROWS,
    "TOOLS",
    "Debug Overlay",
    "About",
    "",
    *BACK_OPTIONS_ROWS,
)
GAME_OPTIONS_ROWS = (
    "PRESET",
    "Preset",
    "GRAPHICS",
    *GRAPHICS_OPTIONS_ROWS,
    "GAME",
    "Auto Play",
    "TOOLS",
    "Debug Overlay",
    "About",
    "Auto Win",
    "Time Speed",
    "SYSTEM",
    "End Game",
    *BACK_OPTIONS_ROWS,
)
OPTION_SECTION_ROWS = ("PRESET", "GRAPHICS", "GAME", "TOOLS", "SYSTEM", "")
PRESETS = {
    "Mobile/Browser": {"fps": 10, "darkness": False, "smooth_scaling": False, "sprite_style": "Amanita", "framebuffer": "standard"},
    "Low": {"fps": 10, "darkness": False, "smooth_scaling": False, "sprite_style": "Puffball", "framebuffer": "standard"},
    "Balanced": {"fps": 30, "darkness": False, "smooth_scaling": False, "sprite_style": "Amanita", "framebuffer": "standard"},
    "High": {"fps": 30, "darkness": True, "smooth_scaling": True, "sprite_style": "Entoloma", "framebuffer": "high"},
    "Ultra": {"fps": 60, "darkness": True, "smooth_scaling": True, "sprite_style": "Mycena Glow", "framebuffer": "high"},
}
PRESET_ORDER = ("Mobile/Browser", "Low", "Balanced", "High", "Ultra")
SPRITE_STYLE_OPTIONS = ("Amanita", "Earthstar", "Entoloma", "Mycena", "Mycena Glow", "Psathyrella", "Puffball")

CAVE_RADIUS = 1240
PLAYER_MARGIN = 42
DEPTH_SCALE = 0.72
GROUND_ORIGIN_Y = SCREEN_HEIGHT // 2
REQUIRED_LUMEN = 10
CHARGE_SECONDS = 2.0
MYCELIAL_LUMEN_READY_FADE_SECONDS = 0.5
MYCELIAL_ACTIVATION_RADIUS = 100
LEAF_FEED_SECONDS = 3.0
LEAF_ACTIVATION_RADIUS = 170
LEAF_LUMEN_TRAVEL_SECONDS = 1.55
LEAF_LUMEN_STAGGER_SECONDS = 0.16
FEED_COMPLETE_FOCUS_SECONDS = 3.0
FEED_COMPLETE_RETURN_SECONDS = 2.4
CONCENTRATE_UNLOCK_SECONDS = 2.4
INTRO_MYCELIAL_PULSE = 1.0
INTRO_MUSHROOM_PULSE = 1.0
INTRO_LIGHT_FADE = 1.25
INTRO_MUSHROOM_GROW = 0.85
INTRO_DURATION = INTRO_MYCELIAL_PULSE + INTRO_MUSHROOM_PULSE + INTRO_LIGHT_FADE + INTRO_MUSHROOM_GROW
INTRO_WORLD_REVEAL_SECONDS = 1.25

PLAYER_SPEED_X = 300
PLAYER_SPEED_Z = 220
PLAYER_CHARGE_MOVE_MULTIPLIER = 0.5
CLICK_WALK_STOP_RADIUS = 12
CLICK_ACTION_SCREEN_RADIUS = 54
CLICK_TRANSIT_DISTANCE = 470
AUTO_GUIDE_SPEED_OPTIONS = ("Off", "Slow", "Fast")
AUTO_GUIDE_SLOW_SPEED_SCALE = 0.5
AUTO_GUIDE_FAST_SPEED_SCALE = 1.0
AUTO_GUIDE_EASE_DISTANCE_FRACTION = 0.2
AUTO_GUIDE_EASE_START_SCALE = 0.35
AUTO_GUIDE_EASE_STOP_SCALE = 0.25
AUTO_GUIDE_IDLE_SECONDS = 10.0
AUTO_GUIDE_PROMPT_SECONDS = 10.0
AUTO_GUIDE_REST_MIN_SECONDS = 1.4
AUTO_GUIDE_REST_MAX_SECONDS = 3.8
AUTO_GUIDE_NO_ACTION_RETRY_SECONDS = 5.0
AUTO_GUIDE_INTERACTION_STANDOFF = 104
AUTO_GUIDE_FOLLOW_SECONDS_RANGE = (0.36, 0.86)
AUTO_GUIDE_FOLLOW_STEP_RANGE = (36, 66)
AUTO_GUIDE_STUCK_RECOVERY_SECONDS = 0.5
AUTO_GUIDE_STUCK_WINDOW_SECONDS = 0.7
AUTO_GUIDE_STUCK_DISTANCE_EPSILON = 3.0
AUTO_GUIDE_STUCK_FLIP_COUNT = 3
AUTO_GUIDE_STUCK_HARD_LIMIT_SECONDS = 1.35
GRAVITY = 1500
CONCENTRATE_RANGE = 190
CONCENTRATE_ROCK_LIFT_HEIGHT = 42
DRAIN_BLOCK_RADIUS = 120
PEBBLE_WAYPOINT_RADIUS = CAVE_RADIUS * 0.5
CONCENTRATE_PEBBLE_RANGE = 175
CONCENTRATE_PEBBLE_LIFT_HEIGHT = 34
PEBBLE_GLIDE_SECONDS = 2.65
CONCENTRATE_PEBBLE_COUNT = 20
PEBBLE_TERRAIN_RADIUS = 62
PEBBLE_TERRAIN_MAX_LIFT = 13
PEBBLE_TERRAIN_FOLLOW_SPEED = 9.0
FERN_FROND_COUNT = 40
FERN_GLIDE_SECONDS = 3.1
FERN_LIFT_HEIGHT = 26
CHANNEL_COVER_LEAF_GLIDE_SECONDS = 1.15
STONE_CHARGE_RATE = 0.2
STONE_CHARGE_RADIUS = 112
NPC_REST_MIN_SECONDS = 2.0
NPC_REST_MAX_SECONDS = 5.0
NPC_TRANSIT_DISTANCE = 470
NPC_TRANSIT_SHRINK_SECONDS = 0.45
NPC_TRANSIT_GROW_SECONDS = 0.55
SPELL_SPEED = 520
SPELL_LIFETIME = 1.45
SPELL_CHARGE_RADIUS = 118
SPELL_ABSORB_SECONDS = 0.75
SPELL_CASTS_PER_LEVEL = 3
SPELL_MAX_LEVEL = 5
NPC_GROWTH_CYCLES_TO_DIVIDE = 10
MAX_NPC_MUSHROOMS = 5
NPC_DIVIDE_SECONDS = 1.3
REGEN_SHRINK_SECONDS = 0.75
REGEN_MINI_MUSHROOM_COUNT = 3
TRANSIT_SHRINK_SECONDS = 0.72
TRANSIT_PAN_SECONDS = 1.05
TRANSIT_GROW_SECONDS = 0.86
TRANSIT_UNLOCK_FOCUS_SECONDS = 3.0
TRANSIT_UNLOCK_SECONDS = 3.0
TRANSIT_UNLOCK_RETURN_SECONDS = 3.0
TRANSIT_UNLOCK_PHASES = ("transit_unlock_focus", "transit_unlock", "transit_unlock_return")
NPC_GROW_SECONDS = 0.9
LUMEN_GROW_SECONDS = 0.75
LUMEN_SHRINK_SECONDS = 0.42
RIGHT_CHANNEL_REVEAL_SECONDS = 12.8
MUSHROOM_ANIMATION_FPS = 30
MUSHROOM_PULSE_SECONDS = 0.55
MUSHROOM_PULSE_EDGE_SECONDS = 0.18
DEPTH_VISUAL_FAR_SCALE = 0.96
DEPTH_VISUAL_NEAR_SCALE = 1.04
PLAYER_DEPTH_VISUAL_FAR_SCALE = 0.98
PLAYER_DEPTH_VISUAL_NEAR_SCALE = 1.02

BG = (3, 6, 12)
DARKNESS = (1, 4, 9)
CAVE_FLOOR = (29, 34, 38)
CAVE_FLOOR_FAR = (18, 22, 28)
CAVE_LINE = (62, 69, 72)
GRAVEL_DARK = (24, 28, 31)
GRAVEL_MID = (41, 46, 49)
GRAVEL_LIGHT = (70, 75, 74)
CRACK = (14, 17, 20)
MYCELIUM = (85, 232, 255)
MYCELIUM_FAINT = (175, 192, 190)
MYCELIUM_FAINT_DIM = (112, 128, 128)
WOOD_GRAIN = (166, 96, 42)
WOOD_GRAIN_DARK = (94, 48, 19)
WOOD_GRAIN_LIGHT = (214, 141, 72)
LUMEN = (185, 200, 198)
LUMEN_CORE = (226, 234, 230)
TEXT = (219, 238, 244)
QUEST = (181, 255, 219)
WATER = (176, 215, 226)
WATER_CORE = (226, 244, 248)
WATER_DARK = (46, 78, 84)
MOSS_GREEN = (63, 87, 55)
MOSS_BROWN = (86, 68, 42)
CAP = (44, 124, 185)
STEM = (218, 230, 220)

ELEMENTS = (
    ("earth", (154, 202, 112)),
    ("water", (96, 198, 245)),
    ("air", (210, 228, 232)),
    ("fire", (248, 124, 64)),
    ("light", (246, 230, 142)),
)

MUSHROOM_ASPECT_PROFILES = {
    "wide": (1.12, 0.95),
    "neutral": (1.0, 1.0),
    "tall": (0.93, 1.1),
}


RADIAL_GLOW_CACHE = {}
ELLIPTICAL_RING_CACHE = {}

# ===== v0.2 PROGRESSION (see docs/v0.2-spec.md Section 1) =====
MAX_CIVS = 3
LEVELS_PER_CIV = 5
ASCENSION_REQUIRED_LEVEL = LEVELS_PER_CIV
PRESTIGE_UNLOCK_CIVS_AT_ASCENSIONS = 1     # first ascension unlocks civs #2 & #3
ASCENSION_ECHO_REWARD = 1
ASCENSION_ECHO_CAP = 15
CYCLE_DIFFICULTY_STEP = 0.10               # +10% enemy power per Cycle

CIV_ORDER = ("amanita", "entoloma", "mycena_glow")   # unlock order; amanita ships first
CIV_DEFS = {
    "amanita":     {"name": "Amanita Wardens",      "aspect": "wide",    "style": "Amanita",     "affinity": "spore_hearth"},
    "entoloma":    {"name": "Entoloma Decomposers", "aspect": "neutral", "style": "Entoloma",    "affinity": "decomposer_terrace"},
    "mycena_glow": {"name": "Mycena Glowweavers",   "aspect": "tall",    "style": "Mycena Glow", "affinity": "elemental_ley_ring"},
}

# ===== v0.2 CLASSES (see Section 2.2) =====
CLASSES = ("forager", "vanguard", "chanter")
CLASS_UNLOCK_LEVEL = {"forager": 1, "vanguard": 3, "chanter": 4}
CLASS_STATS = {
    "forager":  {"atk": 4,  "hp": 20, "speed": 1.20, "gather": 1.00},
    "vanguard": {"atk": 8,  "hp": 60, "speed": 0.80, "gather": 0.40},
    "chanter":  {"atk": 12, "hp": 18, "speed": 1.00, "gather": 0.50},
}
CIV_CLASS_MODS = {   # (hp_mult, atk_mult, gather_mult)
    "amanita":     {"forager": (1.00, 1.00, 1.00), "vanguard": (1.15, 1.10, 1.00), "chanter": (1.00, 1.00, 1.00)},
    "entoloma":    {"forager": (1.15, 1.00, 1.25), "vanguard": (0.95, 0.95, 1.00), "chanter": (0.90, 0.90, 1.00)},
    "mycena_glow": {"forager": (1.00, 1.00, 0.90), "vanguard": (0.90, 0.90, 1.00), "chanter": (1.00, 1.20, 1.00)},
}
CIV_CLASS_NAMES = {   # cosmetic role names per civ (Section 2.2)
    "amanita":     {"forager": "Gillbearer",   "vanguard": "Capguard",   "chanter": "Earthchanter"},
    "entoloma":    {"forager": "Composter",    "vanguard": "Bulwark",    "chanter": "Sporewright"},
    "mycena_glow": {"forager": "Glimmerkin",   "vanguard": "Wardflame",  "chanter": "Lumensinger"},
}

# ===== v0.2 COMBAT (auto-resolve, see Section 3) =====
COMBAT_AUTO_RESOLVE = True
COMBAT_RNG_SEED = 1337
COMBAT_NOISE = 0.10            # set 0.0 in tests for a fully deterministic outcome
COMBAT_WIN_THRESHOLD = 0.5
WINNER_LOSS_COEF = 0.15
WINNER_LOSS_MAX = 0.45
LOSER_LOSS_BASE = 0.60
LOSER_LOSS_MAX = 1.00
FACTION_STAT_MULT = 1.0
VETERANCY_BONUS = 0.10         # +10% power per veterancy rank
TERRAIN_MULT = {"open": 1.10, "farmland": 1.10, "ley": 1.10}   # applies to matching role
TERRAIN_ROLE = {"open": "vanguard", "farmland": "forager", "ley": "chanter"}
ENCOUNTER_AUTO_RESOLVE_SECONDS = 3.0   # delay before a pending encounter self-resolves
AUTO_WIN_DEFAULT = False       # testing affordance, TOOLS/Options + F10
# Accelerated time mode: a testing affordance that scales *simulation* dt only
# (economy, encounter/beat timers, auto-guide). Render/UI/menu stay real-time.
TIME_SPEED_OPTIONS = (1, 2, 4, 8)
TIME_SPEED_DEFAULT = 1

# ===== v0.2 ELEMENTS (see Section 6) =====
ELEMENT_MECHANICS = {
    "earth": "root", "water": "heal", "air": "knockback",
    "fire": "burn", "light": "reveal",
}
COUNTERS = {"fire": "water", "water": "earth", "earth": "air",
            "air": "fire", "light": None}
ELEMENT_ADVANTAGE_MULT = 1.25
ELEMENT_DISADVANTAGE_MULT = 0.80

# ===== v0.2 BUILDINGS (ids only; cost/effect tables in economy.py, Section 5.1) =====
BUILDINGS = ("spore_hearth", "decomposer_terrace", "hyphal_barracks",
             "mycowatch_spire", "spore_library", "chitin_works",
             "wellspring_works", "spore_bazaar", "elemental_ley_ring",
             "symbiosis_bower")
BUILDING_UNLOCK_LEVEL = {
    "spore_hearth": 1, "decomposer_terrace": 1, "hyphal_barracks": 2,
    "mycowatch_spire": 2, "spore_library": 3, "chitin_works": 3,
    "wellspring_works": 4, "spore_bazaar": 4, "elemental_ley_ring": 5,
    "symbiosis_bower": 5,
}

# ===== v0.2 RESOURCES (see Section 4) =====
RESOURCES = ("lumen", "root", "shell", "crystal", "acorn", "amber")
RESOURCE_NAMES = {
    "lumen": "Lumen", "root": "Root Token", "shell": "Glass Shell",
    "crystal": "Crystal", "acorn": "Acorn", "amber": "Amber Shard",
}
RESOURCE_CAPS = {"lumen": 120, "root": 80, "shell": 60,
                 "crystal": 60, "acorn": 80, "amber": 40}
RESOURCE_START = {key: 0 for key in RESOURCES}
RESOURCE_ICON_ASSETS = {
    "lumen": "hud/lumen.png", "root": "hud/root_icon.png",
    "shell": "hud/glass_snail_shell.png", "crystal": "hud/quartz_crystal.png",
    "acorn": "hud/acorn.png", "amber": "hud/amber_shard.png",
}

# Faucet rates (units/second unless noted)
GROVE_LUMEN_RATE = 0.50        # Ley Ring L1 passive
FARM_ACORN_RATE = 0.20         # Decomposer Terrace L1 passive
LIBRARY_CRYSTAL_RATE = 0.10    # Spore Library L1 passive
SPIRE_ROOT_INTERVAL = 60.0     # 1 Root per 60s while a foe is visible
COMBAT_SHELL_REWARD_MULT = 1.0
BAZAAR_AMBER_RATE = 0.15       # Spore Bazaar L1 passive

# Drain rates
BUILDING_UPKEEP_LUMEN = {"spore_hearth": 0.05, "decomposer_terrace": 0.05,
                         "hyphal_barracks": 0.10, "mycowatch_spire": 0.08}
POP_ACORN_UPKEEP_PER_UNIT = 0.01   # acorn/s per living unit
SPELL_LUMEN_COST = 2               # per elemental cast

# ===== v0.2 PHASE 2 (AOM-47): build menu / auto-build / banner =====
BUILD_MENU_HEIGHT = 300
BUILD_GHOST_ALPHA = 140
BUILD_MAX_RADIUS = CAVE_RADIUS - PLAYER_MARGIN - 120
BUILD_MIN_SPACING = 120
BUILD_NUDGE_STEP = 24
BUILD_GROW_SECONDS = 0.45
BUILD_PLACEMENT_FEEDBACK_SECONDS = 1.2

# Deterministic Auto Play construction order (economy-rationale: fund the next
# unlock first). See docs/v0.2-spec.md Section 9.2.
AUTO_BUILD_ORDER = ("decomposer_terrace", "spore_hearth",
                    "mycowatch_spire", "hyphal_barracks",
                    "spore_library", "chitin_works",
                    "wellspring_works", "spore_bazaar",
                    "elemental_ley_ring", "symbiosis_bower")
AUTO_BUILD_COOLDOWN = 1.5
AUTO_BUILD_START_RADIUS = 150
AUTO_BUILD_SPACING = 130
AUTO_BUILD_GOLDEN_ANGLE = 2.399963229728653

ENCOUNTER_BANNER_SECONDS = 4.0

# Existing sprites only (Section 9.1.2). Paths are relative to ``AoM/assets/``.
# ``spore_bazaar`` uses the HUD acorn icon because the proposed
# ``commons_forest_props_v1/acorn`` decal does not exist in the runtime assets;
# no new model/art is generated (board constraint).
BUILDING_DECAL_ASSETS = {
    "spore_hearth":       "sprites/polyhaven_pebbles_v1/pebble_00.png",
    "decomposer_terrace": "sprites/commons_forest_props_v1/fern/fern_00.png",
    "hyphal_barracks":    "sprites/polyhaven_pebbles_v1/pebble_01.png",
    "mycowatch_spire":    "sprites/polyhaven_pebbles_v1/pebble_02.png",
    "spore_library":      "sprites/commons_forest_props_v1/pinecone/pinecone_00.png",
    "chitin_works":       "sprites/hud/glass_snail_shell.png",
    "wellspring_works":   "sprites/polyhaven_pebbles_v1/pebble_03.png",
    "spore_bazaar":       "sprites/hud/acorn.png",
    "elemental_ley_ring": "sprites/hud/quartz_crystal.png",
    "symbiosis_bower":    "sprites/commons_forest_props_v1/pine_needles/pine_needles_00.png",
}
