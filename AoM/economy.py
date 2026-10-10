"""v0.2 economy, progression, classes, and auto-resolve combat.

This module is deliberately pygame-free: it holds pure data objects and pure
functions so the v0.2 simulation layer is deterministic, headless-testable, and
reusable from ``Game`` without dragging in rendering.

Design lenses applied by name (see agent brief / docs/v0.2-spec.md):
- *Determinism & headless driveability*: ``resolve_encounter`` is a pure
  function; its RNG is caller-supplied so a seeded run reproduces exactly.
- *God-object to systems (ECS-lite)*: state lives in small dataclasses rather
  than on the ~230-attribute ``Game``.
- *Save/load round-trip integrity*: every state object is a plain dataclass of
  primitives, so a later JSON save needs no custom encoder.
- *Null-object / safe defaults*: missing/partial state degrades to a no-op
  rather than raising.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from config import (
    ASCENSION_REQUIRED_LEVEL,
    BAZAAR_AMBER_RATE,
    BUILDING_UNLOCK_LEVEL,
    CIV_CLASS_MODS,
    CIV_CLASS_NAMES,
    CIV_ORDER,
    CLASSES,
    CLASS_STATS,
    CLASS_UNLOCK_LEVEL,
    COMBAT_NOISE,
    COMBAT_RNG_SEED,
    COMBAT_WIN_THRESHOLD,
    COUNTERS,
    CYCLE_DIFFICULTY_STEP,
    ELEMENT_ADVANTAGE_MULT,
    ELEMENT_DISADVANTAGE_MULT,
    FACTION_STAT_MULT,
    FARM_ACORN_RATE,
    GROVE_LUMEN_RATE,
    LEVELS_PER_CIV,
    LIBRARY_CRYSTAL_RATE,
    LOSER_LOSS_BASE,
    LOSER_LOSS_MAX,
    MAX_CIVS,
    POP_ACORN_UPKEEP_PER_UNIT,
    PRESTIGE_UNLOCK_CIVS_AT_ASCENSIONS,
    RESOURCES,
    RESOURCE_CAPS,
    RESOURCE_START,
    SPIRE_ROOT_INTERVAL,
    TERRAIN_MULT,
    TERRAIN_ROLE,
    VETERANCY_BONUS,
    WINNER_LOSS_COEF,
    WINNER_LOSS_MAX,
    BUILDING_UPKEEP_LUMEN,
)


def clamp(value, low, high):
    return max(low, min(high, value))


# --------------------------------------------------------------------------- #
# Resources
# --------------------------------------------------------------------------- #

@dataclass
class ResourceState:
    """The six v0.2 resources with caps, faucets, and drains."""

    amounts: dict = field(default_factory=lambda: dict(RESOURCE_START))

    def get(self, key):
        return self.amounts.get(key, 0)

    def add(self, key, amount):
        """Add ``amount`` (may be negative), clamped to ``[0, cap]``."""
        if key not in RESOURCE_CAPS:
            return
        self.amounts[key] = clamp(self.amounts.get(key, 0) + amount, 0, RESOURCE_CAPS[key])

    def can_afford(self, cost):
        return all(self.amounts.get(key, 0) >= amount for key, amount in (cost or {}).items())

    def spend(self, key, amount) -> bool:
        """Spend ``amount`` of ``key``; return False (and change nothing) if short."""
        if amount <= 0:
            return True
        if self.amounts.get(key, 0) < amount:
            return False
        self.amounts[key] -= amount
        return True

    def spend_cost(self, cost) -> bool:
        """Spend a multi-resource cost atomically; return False if unaffordable."""
        cost = cost or {}
        if not self.can_afford(cost):
            return False
        for key, amount in cost.items():
            self.amounts[key] = self.amounts.get(key, 0) - amount
        return True

    def grant(self, reward):
        for key, amount in (reward or {}).items():
            self.add(key, amount)

    def tick(self, dt, rates):
        """Apply per-second ``rates`` (resource -> delta/second) for ``dt`` seconds."""
        for key, rate in (rates or {}).items():
            if rate:
                self.add(key, rate * dt)


# --------------------------------------------------------------------------- #
# Classes and armies
# --------------------------------------------------------------------------- #

@dataclass
class ClassStack:
    role: str          # forager | vanguard | chanter
    element: str = "earth"
    count: int = 1
    veterancy: int = 0


@dataclass
class Army:
    civ_id: str = CIV_ORDER[0]
    stacks: list = field(default_factory=list)

    def add(self, role, element="earth", count=1, veterancy=0):
        self.stacks.append(ClassStack(role=role, element=element, count=count, veterancy=veterancy))
        return self

    def count(self):
        return sum(max(0, stack.count) for stack in self.stacks)

    def dominant_element(self):
        totals = {}
        for stack in self.stacks:
            if stack.count > 0:
                totals[stack.element] = totals.get(stack.element, 0) + stack.count
        if not totals:
            return "light"
        return max(totals.items(), key=lambda item: item[1])[0]

    def power(self, opponent=None, terrain="open", power_mult=1.0):
        opponent_element = opponent.dominant_element() if opponent is not None else "light"
        terrain_role = TERRAIN_ROLE.get(terrain)
        total = 0.0
        for stack in self.stacks:
            if stack.count <= 0:
                continue
            stats = CLASS_STATS.get(stack.role)
            if stats is None:
                continue
            _, atk_mult, _ = CIV_CLASS_MODS.get(self.civ_id, {}).get(stack.role, (1.0, 1.0, 1.0))
            element_mult = element_multiplier(stack.element, opponent_element)
            veterancy_mult = 1.0 + VETERANCY_BONUS * stack.veterancy
            terrain_mult = TERRAIN_MULT.get(terrain, 1.0) if stack.role == terrain_role else 1.0
            total += (
                stack.count
                * stats["atk"]
                * atk_mult
                * element_mult
                * veterancy_mult
                * terrain_mult
            )
        return total * power_mult * FACTION_STAT_MULT


def element_multiplier(attacker_element, defender_element):
    """Return the element counter multiplier from Section 6.2 of the spec."""
    if defender_element is None:
        return 1.0
    if COUNTERS.get(attacker_element) == defender_element:
        return ELEMENT_ADVANTAGE_MULT
    if COUNTERS.get(defender_element) == attacker_element:
        return ELEMENT_DISADVANTAGE_MULT
    return 1.0


def assign_class(target, role, civ_id):
    """Apply ``CLASS_STATS x CIV_CLASS_MODS`` for ``role``/``civ_id``.

    Works on a ``ClassStack`` (mutates it), any object with matching attributes,
    or a plain ``dict``. Returns the resolved stat dict either way.
    """
    hp_mult, atk_mult, gather_mult = CIV_CLASS_MODS.get(civ_id, {}).get(role, (1.0, 1.0, 1.0))
    stats = CLASS_STATS.get(role, {"atk": 1.0, "hp": 1.0, "speed": 1.0, "gather": 1.0})
    resolved = {
        "role": role,
        "civ": civ_id,
        "name": CIV_CLASS_NAMES.get(civ_id, {}).get(role, role.title()),
        "atk": stats["atk"] * atk_mult,
        "hp": stats["hp"] * hp_mult,
        "speed": stats["speed"],
        "gather": stats["gather"] * gather_mult,
    }
    if target is not None:
        for key, value in resolved.items():
            if isinstance(target, dict):
                target[key] = value
            else:
                setattr(target, key, value)
    return resolved


def choose_balanced_class(available=CLASSES, counts=None):
    """Pick the least-represented class (mirrors choose_balanced_mushroom_variant)."""
    available = tuple(available)
    if not available:
        return None
    counts = counts or {}
    minimum = min(counts.get(role, 0) for role in available)
    least_used = [role for role in available if counts.get(role, 0) == minimum]
    return random.choice(least_used)


# --------------------------------------------------------------------------- #
# Buildings
# --------------------------------------------------------------------------- #

# v1 costs in the six resources (Section 5.1). Effects are descriptive data;
# ``building_faucet_rates``/``building_drains`` turn them into economy rates.
BUILDING_COST = {
    "spore_hearth": {"root": 3, "acorn": 2},
    "decomposer_terrace": {"root": 2, "lumen": 1},
    "hyphal_barracks": {"root": 5, "shell": 3},
    "mycowatch_spire": {"root": 4, "crystal": 1},
    "spore_library": {"crystal": 3, "root": 4},
    "chitin_works": {"shell": 5, "lumen": 2},
    "wellspring_works": {"root": 4, "crystal": 2},
    "spore_bazaar": {"amber": 3, "root": 4},
    "elemental_ley_ring": {"crystal": 4, "lumen": 3},
    "symbiosis_bower": {"amber": 4, "root": 3},
}

# civ doctrine multipliers for building output (Section 5.2). (faucet_mult)
BUILDING_CIV_MODS = {
    "amanita": {"spore_hearth": 1.10, "hyphal_barracks": 1.10, "mycowatch_spire": 1.10, "chitin_works": 1.10, "spore_bazaar": 1.10},
    "entoloma": {"decomposer_terrace": 1.25, "spore_library": 1.15, "wellspring_works": 1.25, "elemental_ley_ring": 0.85},
    "mycena_glow": {"spore_library": 1.25, "elemental_ley_ring": 1.25, "decomposer_terrace": 0.85},
}


def building_unlocked(building_id, level):
    """True when ``building_id`` is available at civilization ``level``."""
    return BUILDING_UNLOCK_LEVEL.get(building_id, 999) <= level


def building_faucet_rates(civ_id, built, cycle=1):
    """Per-second resource faucet rates from the built buildings of one civ."""
    built = built or {}
    rates = {key: 0.0 for key in RESOURCES}
    mods = BUILDING_CIV_MODS.get(civ_id, {})

    def mult(building_id):
        return mods.get(building_id, 1.0)

    if built.get("elemental_ley_ring"):
        rates["lumen"] += GROVE_LUMEN_RATE * mult("elemental_ley_ring")
    if built.get("decomposer_terrace"):
        rates["acorn"] += FARM_ACORN_RATE * mult("decomposer_terrace")
    if built.get("spore_library"):
        rates["crystal"] += LIBRARY_CRYSTAL_RATE * mult("spore_library")
    if built.get("spore_bazaar"):
        rates["amber"] += BAZAAR_AMBER_RATE * mult("spore_bazaar")
    if built.get("mycowatch_spire"):
        rates["root"] += 1.0 / SPIRE_ROOT_INTERVAL
    return rates


def building_drains(civ_id, built, living_units=0):
    """Per-second resource drains, returned as positive magnitudes."""
    built = built or {}
    drains = {key: 0.0 for key in RESOURCES}
    for building_id, rate in BUILDING_UPKEEP_LUMEN.items():
        if built.get(building_id):
            drains["lumen"] += rate
    drains["acorn"] += POP_ACORN_UPKEEP_PER_UNIT * max(0, living_units)
    return drains


def net_resource_rates(civ_id, built, living_units=0, cycle=1):
    """Faucets minus drains, as a resource -> delta/second mapping."""
    rates = building_faucet_rates(civ_id, built, cycle)
    drains = building_drains(civ_id, built, living_units)
    return {key: rates.get(key, 0.0) - drains.get(key, 0.0) for key in RESOURCES}


# --------------------------------------------------------------------------- #
# Encounters and auto-resolve combat
# --------------------------------------------------------------------------- #

@dataclass
class Encounter:
    id: str
    level: int
    enemy: Army
    terrain: str = "open"
    reward: dict = field(default_factory=dict)
    boss: bool = False
    capstone: bool = False
    enemy_power_mult: float = 1.0


# (role, element, count, veterancy) stacks per encounter (Section 3.2).
ENCOUNTERS = {
    "skirmish_1": {
        "level": 2, "terrain": "farmland",
        "stacks": [("forager", "earth", 3, 0)],
        "reward": {"root": 2, "acorn": 1},
        "boss": False, "capstone": False,
    },
    "swarm_3": {
        "level": 3, "terrain": "open",
        "stacks": [("forager", "earth", 5, 0), ("vanguard", "earth", 1, 0)],
        "reward": {"root": 2, "amber": 1},
        "boss": False, "capstone": False,
    },
    "hold_4": {
        "level": 4, "terrain": "ley",
        "stacks": [("vanguard", "fire", 3, 0), ("chanter", "water", 2, 0)],
        "reward": {"crystal": 2, "shell": 1},
        "boss": False, "capstone": False,
    },
    "boss_5": {
        "level": 5, "terrain": "open",
        "stacks": [("forager", "earth", 2, 0), ("vanguard", "fire", 2, 0),
                   ("chanter", "water", 1, 0), ("forager", "air", 1, 0),
                   ("vanguard", "earth", 1, 3)],
        "reward": {"shell": 4, "amber": 2, "root": 3},
        "boss": True, "capstone": True,
    },
}


def make_encounter(encounter_id, cycle=1, enemy_civ="wild"):
    """Build an ``Encounter`` from the table, scaled by the current cycle."""
    spec = ENCOUNTERS.get(encounter_id)
    if spec is None:
        return None
    enemy = Army(civ_id=enemy_civ)
    for role, element, count, veterancy in spec["stacks"]:
        enemy.add(role, element, count, veterancy)
    return Encounter(
        id=encounter_id,
        level=spec["level"],
        enemy=enemy,
        terrain=spec["terrain"],
        reward=dict(spec["reward"]),
        boss=spec.get("boss", False),
        capstone=spec.get("capstone", False),
        enemy_power_mult=1.0 + CYCLE_DIFFICULTY_STEP * max(0, cycle - 1),
    )


def encounter_for_level(level):
    for encounter_id, spec in ENCOUNTERS.items():
        if spec["level"] == level:
            return encounter_id
    return None


def resolve_encounter(army, encounter, auto_win=False, rng=None):
    """Resolve an encounter deterministically; return a result dict.

    Result keys: ``win``, ``player_loss_frac``, ``enemy_loss_frac``,
    ``reward``, ``player_power``, ``enemy_power``, ``auto_win``.
    """
    rng = rng if rng is not None else random.Random(COMBAT_RNG_SEED)
    player_power = army.power(encounter.enemy, encounter.terrain)
    enemy_power = encounter.enemy.power(army, encounter.terrain, encounter.enemy_power_mult)
    reward = dict(encounter.reward)

    if auto_win:
        return {
            "win": True,
            "player_loss_frac": 0.0,
            "enemy_loss_frac": 1.0,
            "reward": reward,
            "player_power": player_power,
            "enemy_power": enemy_power,
            "auto_win": True,
        }

    noise = 1.0 + rng.uniform(-COMBAT_NOISE, COMBAT_NOISE)
    total = player_power + enemy_power
    ratio = player_power / total if total > 0 else 0.5
    win = ratio * noise >= COMBAT_WIN_THRESHOLD

    if win:
        player_loss = clamp(WINNER_LOSS_COEF * _safe_div(enemy_power, player_power), 0.0, WINNER_LOSS_MAX)
        enemy_loss = clamp(LOSER_LOSS_BASE + 0.30 * (_safe_div(player_power, enemy_power) - 1.0), LOSER_LOSS_BASE, LOSER_LOSS_MAX)
    else:
        player_loss = clamp(LOSER_LOSS_BASE + 0.30 * (_safe_div(enemy_power, player_power) - 1.0), LOSER_LOSS_BASE, LOSER_LOSS_MAX)
        enemy_loss = clamp(WINNER_LOSS_COEF * _safe_div(player_power, enemy_power), 0.0, WINNER_LOSS_MAX)

    return {
        "win": win,
        "player_loss_frac": player_loss,
        "enemy_loss_frac": enemy_loss,
        "reward": reward,
        "player_power": player_power,
        "enemy_power": enemy_power,
        "auto_win": False,
    }


def _safe_div(numerator, denominator):
    if denominator <= 0:
        return 0.0 if numerator <= 0 else float("inf")
    return numerator / denominator


# --------------------------------------------------------------------------- #
# Progression / prestige loop
# --------------------------------------------------------------------------- #

@dataclass
class CivState:
    civ_id: str
    level: int = 1
    ascended: bool = False
    unlocked_roles: set = field(default_factory=lambda: {"forager"})
    built: dict = field(default_factory=dict)      # building_id -> level


@dataclass
class GameProgress:
    active_civ: str = CIV_ORDER[0]
    civs_unlocked: set = field(default_factory=lambda: {CIV_ORDER[0]})
    ascension_count: int = 0
    mire_echo: int = 0
    cycle: int = 1
    civs: dict = field(default_factory=lambda: {civ_id: CivState(civ_id) for civ_id in CIV_ORDER})

    def active_state(self):
        return self.civs[self.active_civ]


def unlock_roles_for_level(civ):
    for role, unlock_level in CLASS_UNLOCK_LEVEL.items():
        if civ.level >= unlock_level:
            civ.unlocked_roles.add(role)


def reset_civ_progress(civ):
    civ.level = 1
    civ.unlocked_roles = {"forager"}
    civ.built = {}


def ascend(progress):
    """Handle a Level-5 clear: ascension, civ unlock, restart on the next civ."""
    civ = progress.active_state()
    civ.ascended = True
    reset_civ_progress(civ)
    progress.ascension_count += 1
    if progress.ascension_count == PRESTIGE_UNLOCK_CIVS_AT_ASCENSIONS:
        for civ_id in CIV_ORDER[:MAX_CIVS]:
            progress.civs_unlocked.add(civ_id)
    progress.cycle = 1 + progress.ascension_count // max(1, MAX_CIVS)
    unlocked_order = [civ_id for civ_id in CIV_ORDER if civ_id in progress.civs_unlocked]
    if progress.active_civ in unlocked_order:
        index = unlocked_order.index(progress.active_civ)
        progress.active_civ = unlocked_order[(index + 1) % len(unlocked_order)]
    elif unlocked_order:
        progress.active_civ = unlocked_order[0]
    return True


def advance_level(progress, capstone_done):
    """Unlock the next level, or ascend at ``LEVELS_PER_CIV``.

    Returns True when a level was cleared (advanced or ascended).
    """
    if not capstone_done:
        return False
    civ = progress.active_state()
    if civ.level >= ASCENSION_REQUIRED_LEVEL:
        return ascend(progress)
    civ.level += 1
    unlock_roles_for_level(civ)
    return True
