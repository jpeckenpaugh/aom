import math

import pygame

from config import *
from entities import *
from game_backed import GameBackedManager
from utils import *


class PhaseManager(GameBackedManager):
    @property
    def intro_complete(self):
        return self.intro_time >= INTRO_DURATION
    @property
    def intro_mushroom_luminosity(self):
        if self.intro_time < INTRO_MYCELIAL_PULSE + INTRO_MUSHROOM_PULSE:
            return 0
        t = (self.intro_time - INTRO_MYCELIAL_PULSE - INTRO_MUSHROOM_PULSE) / INTRO_LIGHT_FADE
        return max(0, min(1, t))
    @property
    def intro_mycelial_visibility(self):
        t = max(0, min(1, self.intro_time / (INTRO_MYCELIAL_PULSE + 0.45)))
        return t * t * (3 - 2 * t)
    @property
    def post_intro_reveal(self):
        if not self.intro_complete:
            return 0.0
        t = max(0, min(1, (self.intro_time - INTRO_DURATION) / INTRO_WORLD_REVEAL_SECONDS))
        return t * t * (3 - 2 * t)
    @property
    def mycelial_art_visibility(self):
        if self.intro_complete:
            return 0.35 + self.post_intro_reveal * 0.65
        return self.intro_mycelial_visibility * 0.35
    def mycelial_art_pulse_strength(self, time):
        strength = 0.0
        intro_pulse = self.intro_mycelial_pulse
        if intro_pulse is not None:
            strength = max(strength, math.sin(intro_pulse * math.pi) * 0.42)
        if self.phase in (*TRANSIT_UNLOCK_PHASES, "feed_complete_focus", "concentrate_unlock", "feed_complete_return"):
            strength = max(strength, 0.18 + 0.22 * (0.5 + 0.5 * math.sin(time * 2.4)))
        if self.lumen_count >= REQUIRED_LUMEN and self.phase == "explore":
            ready = self.mycelial_lumen_ready_fade
            strength = max(strength, ready * (0.12 + 0.18 * (0.5 + 0.5 * math.sin(time * 2.8))))
        return max(0.0, min(1.0, strength))
    @property
    def mycelial_lumen_ready_fade(self):
        t = max(0.0, min(1.0, self.mycelial_lumen_ready_time / MYCELIAL_LUMEN_READY_FADE_SECONDS))
        return t * t * (3 - 2 * t)
    @property
    def intro_mushroom_body_scale(self):
        start = INTRO_MYCELIAL_PULSE + INTRO_MUSHROOM_PULSE + INTRO_LIGHT_FADE * 0.35
        if self.intro_time < start:
            return 0.012
        t = (self.intro_time - start) / INTRO_MUSHROOM_GROW
        t = max(0, min(1, t))
        return t * t * (3 - 2 * t)
    @property
    def intro_mycelial_pulse(self):
        if self.intro_time >= INTRO_MYCELIAL_PULSE:
            return None
        return self.intro_time / INTRO_MYCELIAL_PULSE
    @property
    def intro_mushroom_pulse(self):
        start = INTRO_MYCELIAL_PULSE
        if self.intro_time < start or self.intro_time >= start + INTRO_MUSHROOM_PULSE:
            return None
        return (self.intro_time - start) / INTRO_MUSHROOM_PULSE
    def lumen_is_on_screen(self, lumen):
        screen = self.camera.project(lumen.x, lumen.z, 36)
        margin = 180
        return -margin <= screen.x <= SCREEN_WIDTH + margin and -margin <= screen.y <= SCREEN_HEIGHT + margin
    def cheat_advance_phase(self):
        self.concentrating = False
        self.concentrate_mode = None
        self.selected_pebble = None
        self.selected_waypoint = None
        self.player.pulse_timer = 0
        self.player.channel_phase = None
        self.player.channeling = False
        if not self.intro_complete:
            self.intro_time = INTRO_DURATION + INTRO_WORLD_REVEAL_SECONDS
            return
        if self.phase == "explore":
            for lumen in self.lumens:
                lumen.collected = True
                lumen.collecting = True
                lumen.collect_age = LUMEN_SHRINK_SECONDS
            self.lumen_count = REQUIRED_LUMEN
            self.growth_state = min(4, self.lumen_count // 3)
            self.charge_progress = 1.0
            self.phase = "feed"
            self.spawn_leaf_quest_lumens()
            return
        if self.phase == "feed":
            for leaf in self.leaf_decals:
                leaf.lumen_consumed = True
                leaf.feed_progress = 1.0
                leaf.connected = True
            self.phase = "feed_complete_focus"
            self.cinematic_time = 0
            return
        if self.phase in ("feed_complete_focus", "concentrate_unlock", "feed_complete_return"):
            self.phase = "post_feed"
            self.cinematic_time = 0
            return
        if self.phase == "post_feed" and not self.concentrate_rock.lifted:
            for leaf in self.channel_cover_leaves:
                leaf.pos = leaf.target.copy()
                leaf.moving = False
                leaf.placed = True
                leaf.move_start = None
                leaf.move_progress = 0.0
            self.concentrate_rock.lifted = True
            self.concentrate_rock.held = False
            self.right_channel_active = True
            self.right_channel_reveal = 1.0
            return
        if self.phase == "post_feed":
            self.cheat_place_primary_pebbles()
            self.transit_unlocked_announced = True
            self.phase = "transit_unlock_focus"
            self.transit_time = 0
            return
        if self.phase in TRANSIT_UNLOCK_PHASES:
            self.phase = "transit"
            self.transit_time = 0
            if not self.npc_mushrooms:
                self.spawn_npc_mushrooms()
            return
        if self.phase in ("transit_select", "transit_disappear", "transit_pan", "transit_appear"):
            self.phase = "transit"
            self.transit_time = 0
            self.transit_target = None
            if not self.npc_mushrooms:
                self.spawn_npc_mushrooms()
            return
        if self.phase == "transit":
            if not self.npc_mushrooms:
                self.spawn_npc_mushrooms()
            if not self.collect_pebbles_02_complete:
                self.cheat_place_companion_pebbles()
                self.collect_pebbles_02_complete = True
                return
            if not self.collect_ferns_03_complete:
                self.cheat_place_ferns()
                self.collect_ferns_03_complete = True
                return
            if not self.charge_stones_04_complete:
                self.cheat_charge_all_occupied_stones()
                self.charge_stones_04_complete = True
                return
            if not self.all_elements_at_max_level():
                for element, _ in ELEMENTS:
                    self.elemental_cast_counts[element] = (SPELL_MAX_LEVEL - 1) * SPELL_CASTS_PER_LEVEL
                self.charge_stones_04_complete = False
                for npc in self.npc_mushrooms:
                    npc.growth_cycles = NPC_GROWTH_CYCLES_TO_DIVIDE
                return
            self.cheat_complete_regen()
    def cheat_place_primary_pebbles(self):
        for index, waypoint in enumerate(self.pebble_waypoints):
            waypoint.occupied_by = index
            waypoint.claimed_by = None
            waypoint.charge = max(waypoint.charge, 0.0)
        for index, pebble in enumerate(self.concentrate_pebbles[: len(self.pebble_waypoints)]):
            waypoint = self.pebble_waypoints[index]
            pebble.pos = waypoint.pos.copy()
            pebble.target_group = "primary"
            pebble.target_waypoint = index
            pebble.moving = False
            pebble.held = False
            pebble.placed = True
            pebble.claimed_by = None
    def cheat_place_companion_pebbles(self):
        for index, waypoint in enumerate(self.companion_waypoints):
            waypoint.occupied_by = 1000 + index
            waypoint.claimed_by = None
            waypoint.charge = max(waypoint.charge, 0.0)
    def cheat_place_ferns(self):
        for leaf_index, leaf in enumerate(self.leaf_decals):
            if not leaf.fern_slots:
                continue
            for slot_index in range(len(leaf.fern_slots)):
                fern_id = leaf_index * 10 + slot_index
                leaf.fern_slots[slot_index] = fern_id
        for fern in self.fern_fronds:
            fern.moving = False
            fern.held = False
            fern.placed = True
            fern.claimed_by = None
    def cheat_charge_all_occupied_stones(self):
        for _, _, waypoint in self.all_stone_waypoints():
            if waypoint.occupied_by is not None:
                waypoint.charge = 1.0
                waypoint.claimed_by = None
    def cheat_complete_regen(self):
        for _, _, waypoint in self.all_stone_waypoints():
            if waypoint.occupied_by is None or waypoint.regen_offsets:
                continue
            waypoint.regen_offsets = [
                pygame.Vector2(-42, -18),
                pygame.Vector2(38, -12),
                pygame.Vector2(0, 34),
            ]
            waypoint.claimed_by = None
    def player_charge_resistance_active(self):
        if self.concentrating:
            return True
        all_lumen_collected = self.lumen_count >= REQUIRED_LUMEN
        if self.phase == "explore" and all_lumen_collected and self.player.pos.distance_to(self.spawn) < MYCELIAL_ACTIVATION_RADIUS:
            return True
        if self.phase == "feed":
            return any(
                not leaf.connected
                and leaf.lumen_consumed
                and self.player.pos.distance_to(pygame.Vector2(leaf.x, leaf.z)) <= LEAF_ACTIVATION_RADIUS
                for leaf in self.leaf_decals
            )
        if self.phase == "transit" and self.collect_ferns_03_complete and not self.charge_stones_04_complete:
            return any(
                self.player.pos.distance_to(waypoint.pos) <= STONE_CHARGE_RADIUS
                for _, _, waypoint in self.chargeable_stone_waypoints()
            )
        return False
    @property
    def concentrate_unlocked(self):
        return self.phase in ("post_feed", "transit", "transit_select")
    @property
    def mushroom_body_scale(self):
        if not self.intro_complete:
            return self.intro_mushroom_body_scale
        if self.phase == "transit_pan":
            return 0.012
        return 1.0
    @property
    def player_transit_visibility(self):
        if self.phase == "transit_disappear":
            t = min(1.0, self.transit_time / TRANSIT_SHRINK_SECONDS)
            return max(0.0, 1.0 - smoothstep(t))
        if self.phase == "transit_pan":
            return 0.0
        if self.phase == "transit_appear":
            t = min(1.0, self.transit_time / TRANSIT_GROW_SECONDS)
            return smoothstep(t)
        return 1.0
    @property
    def transit_available(self):
        return self.phase in ("transit", "transit_select")
    @property
    def training_beat_active(self):
        return self.phase == "transit" and self.charge_stones_04_complete and self.any_charged_stones()
    @property
    def concentrate_rock_in_range(self):
        return (
            self.phase == "post_feed"
            and not self.concentrate_rock.lifted
            and self.concentrate_mode is None
            and self.channel_cover_leaves_ready
            and self.player.pos.distance_to(self.concentrate_rock.pos) <= CONCENTRATE_RANGE
        )
    @property
    def channel_cover_leaves_ready(self):
        return all(leaf.placed for leaf in self.channel_cover_leaves)
    @property
    def nearest_channel_cover_leaf(self):
        if self.phase != "post_feed" or self.concentrate_rock.lifted:
            return None
        if self.player.pos.distance_to(self.concentrate_rock.pos) > CONCENTRATE_RANGE:
            return None
        candidates = [(index, leaf) for index, leaf in enumerate(self.channel_cover_leaves) if not leaf.placed and not leaf.moving]
        if not candidates:
            return None
        return min(candidates, key=lambda item: (self.player.pos.distance_to(item[1].pos), item[0]))[1]
    @property
    def pebble_beat_active(self):
        return self.phase == "post_feed" and self.concentrate_rock.lifted
    @property
    def companion_pebble_beat_active(self):
        return self.phase == "transit" and self.npc_mushrooms and not self.collect_pebbles_02_complete
    @property
    def fern_beat_active(self):
        return self.phase == "transit" and self.collect_pebbles_02_complete and not self.collect_ferns_03_complete
    @property
    def nearest_targetable_pebble(self):
        if self.pebble_beat_active:
            group = "primary"
        elif self.companion_pebble_beat_active:
            group = "companion"
        else:
            return None
        candidates = [
            pebble
            for pebble in self.concentrate_pebbles
            if not pebble.placed and not pebble.moving and self.player.pos.distance_to(pebble.pos) <= CONCENTRATE_PEBBLE_RANGE
            and (pebble.claimed_by is None or pebble.claimed_by == -1)
        ] 
        if not candidates:
            return None
        return min(candidates, key=lambda pebble: (self.player.pos.distance_to(pebble.pos), pebble.id))
    @property
    def open_waypoint_indexes(self):
        return self.open_waypoint_indexes_for_group(self.selected_waypoint_group)
    def open_waypoint_indexes_for_group(self, group):
        waypoints = self.companion_waypoints if group == "companion" else self.pebble_waypoints
        return [
            index
            for index, waypoint in enumerate(waypoints)
            if waypoint.occupied_by is None and waypoint.claimed_by is None
        ]
    @property
    def nearest_targetable_fern(self):
        if not self.fern_beat_active:
            return None
        candidates = [
            fern
            for fern in self.fern_fronds
            if not fern.placed and not fern.moving and not fern.held
            and (fern.claimed_by is None or fern.claimed_by == -1)
            and self.player.pos.distance_to(fern.pos) <= CONCENTRATE_PEBBLE_RANGE
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda fern: (self.player.pos.distance_to(fern.pos), fern.id))
    def toggle_concentrate(self):
        if not self.concentrate_unlocked:
            return
        if self.concentrate_mode == "outlet_rock":
            self.release_concentrate_rock()
            return
        cover_leaf = self.nearest_channel_cover_leaf
        if cover_leaf:
            self.start_channel_cover_leaf_move(cover_leaf)
            return
        if self.concentrate_rock_in_range:
            self.start_outlet_rock_as_pebble()
            return
        pebble = self.nearest_targetable_pebble
        if pebble:
            group = "companion" if self.companion_pebble_beat_active else "primary"
            self.start_pebble_auto_move(pebble, group)
            return
        fern = self.nearest_targetable_fern
        if fern:
            self.start_player_fern_move(fern)
    def update_concentrate_action(self, dt):
        if self.concentrate_mode in ("outlet_rock", "pebble_select", "pebble_move", "fern_move"):
            self.player.clear_walk_target()
            self.player.request_channel()
            self.player.moving = False
    def start_outlet_rock_as_pebble(self):
        self.concentrate_rock.held = False
        self.concentrate_rock.lifted = True
        self.right_channel_active = True
        self.right_channel_reveal = 0.0
        image = self.concentrate_rock_image or self.prepare_pebble_image(
            self.pebble_sprites[-1],
            scale=0.78,
            angle=-14,
            tint=(0.58, 0.60, 0.57),
            alpha=255,
        )
        pebble_id = max((pebble.id for pebble in self.concentrate_pebbles), default=-1) + 1
        pebble = ConcentratePebble(pebble_id, self.concentrate_rock.pos.copy(), image)
        self.concentrate_pebbles.append(pebble)
        open_indexes = self.open_waypoint_indexes_for_group("primary")
        if open_indexes:
            closest = min(open_indexes, key=lambda index: pebble.pos.distance_to(self.pebble_waypoints[index].pos))
        else:
            closest = None
        self.start_pebble_auto_move(pebble, "primary", closest)
        return pebble
    def start_pebble_auto_move(self, pebble, group="primary", preferred_waypoint=None):
        self.selected_waypoint_group = group
        waypoints = self.companion_waypoints if group == "companion" else self.pebble_waypoints
        open_indexes = [
            index
            for index, waypoint in enumerate(waypoints)
            if waypoint.occupied_by is None
            and (
                waypoint.claimed_by is None
                or (waypoint.claimed_by == -1 and index == preferred_waypoint)
            )
        ]
        if not open_indexes:
            return False
        waypoint_index = preferred_waypoint if preferred_waypoint in open_indexes else min(
            open_indexes,
            key=lambda index: pebble.pos.distance_to(waypoints[index].pos),
        )
        self.selected_pebble = pebble
        self.selected_waypoint = waypoint_index
        pebble.held = True
        pebble.claimed_by = -1
        if self.confirm_pebble_waypoint():
            if self.auto_guide_pebble_id == pebble.id:
                self.clear_auto_guide_pebble_reservation()
            return True
        self.cancel_pebble_selection()
        return False
    def start_pebble_selection(self, pebble, group="primary", preferred_waypoint=None):
        self.selected_waypoint_group = group
        open_indexes = self.open_waypoint_indexes_for_group(group)
        if not open_indexes:
            return
        self.concentrating = True
        self.concentrate_mode = "pebble_select"
        self.selected_pebble = pebble
        self.selected_waypoint = preferred_waypoint if preferred_waypoint in open_indexes else open_indexes[0]
        pebble.held = True
        pebble.claimed_by = -1
    def cycle_selected_waypoint(self, direction):
        open_indexes = self.open_waypoint_indexes
        if not open_indexes or self.selected_waypoint is None:
            return
        current = open_indexes.index(self.selected_waypoint) if self.selected_waypoint in open_indexes else 0
        self.selected_waypoint = open_indexes[(current + direction) % len(open_indexes)]
    def confirm_pebble_waypoint(self):
        if not self.selected_pebble or self.selected_waypoint is None:
            self.cancel_pebble_selection()
            return False
        waypoints = self.companion_waypoints if self.selected_waypoint_group == "companion" else self.pebble_waypoints
        waypoint = waypoints[self.selected_waypoint]
        if waypoint.occupied_by is not None or (waypoint.claimed_by is not None and waypoint.claimed_by != -1):
            self.cycle_selected_waypoint(1)
            return False
        pebble = self.selected_pebble
        pebble.target_waypoint = self.selected_waypoint
        pebble.target_group = self.selected_waypoint_group
        pebble.move_start = pebble.pos.copy()
        pebble.move_progress = 0
        pebble.moving = True
        pebble.held = True
        waypoint.claimed_by = -1
        self.selected_pebble = None
        self.selected_waypoint = None
        self.selected_waypoint_group = "primary"
        self.concentrating = False
        self.concentrate_mode = None
        return True
    def cancel_pebble_selection(self):
        if self.selected_pebble:
            self.selected_pebble.held = False
            self.selected_pebble.claimed_by = None
        self.selected_pebble = None
        self.selected_waypoint = None
        self.selected_waypoint_group = "primary"
        self.concentrating = False
        self.concentrate_mode = None
    def start_channel_cover_leaf_move(self, leaf):
        leaf.moving = True
        leaf.move_start = leaf.pos.copy()
        leaf.move_progress = 0.0
        self.player.request_channel()
        self.player.moving = False
    def start_player_fern_move(self, fern, preferred_slot=None):
        slot = None
        if preferred_slot is not None:
            leaf_index, slot_index = preferred_slot
            if 0 <= leaf_index < len(self.leaf_decals):
                leaf = self.leaf_decals[leaf_index]
                claimed_by_same_fern = (
                    fern.target_leaf == leaf_index
                    and fern.target_slot == slot_index
                    and fern.claimed_by == -1
                )
                if (
                    leaf.fern_slots
                    and 0 <= slot_index < len(leaf.fern_slots)
                    and leaf.fern_slots[slot_index] is None
                    and claimed_by_same_fern
                ):
                    slot = (leaf_index, slot_index, pygame.Vector2(leaf.x, leaf.z))
        if slot is None:
            slot = self.find_open_fern_slot(fern.pos)
        if slot is None:
            return False
        leaf_index, slot_index, _ = slot
        fern.claimed_by = -1
        fern.target_leaf = leaf_index
        fern.target_slot = slot_index
        fern.move_start = fern.pos.copy()
        fern.move_progress = 0
        fern.moving = True
        fern.held = True
        self.concentrating = False
        self.concentrate_mode = None
        if self.auto_guide_fern_id == fern.id:
            self.clear_auto_guide_fern_reservation()
        return True
    def find_open_fern_slot(self, from_pos):
        open_slots = []
        for leaf_index, leaf in enumerate(self.leaf_decals):
            for slot_index, fern_id in enumerate(leaf.fern_slots or []):
                if fern_id is None:
                    claimed = any(
                        fern.target_leaf == leaf_index
                        and fern.target_slot == slot_index
                        and fern.claimed_by is not None
                        for fern in self.fern_fronds
                    )
                    if not claimed:
                        open_slots.append((leaf_index, slot_index, pygame.Vector2(leaf.x, leaf.z)))
        if not open_slots:
            return None
        return min(open_slots, key=lambda item: from_pos.distance_to(item[2]))
    def update_moving_pebbles(self, dt):
        for pebble in self.concentrate_pebbles:
            if not pebble.moving or pebble.target_waypoint is None or pebble.move_start is None:
                continue
            waypoint = self.resolve_pebble_target_waypoint(pebble)
            if waypoint is None:
                pebble.moving = False
                pebble.held = False
                continue
            pebble.move_progress = min(1.0, pebble.move_progress + dt / PEBBLE_GLIDE_SECONDS)
            t = pebble.move_progress
            ease = t * t * (3 - 2 * t)
            pebble.pos = pebble.move_start.lerp(waypoint.pos, ease)
            if pebble.move_progress >= 1.0:
                pebble.pos = waypoint.pos.copy()
                pebble.moving = False
                pebble.held = False
                pebble.placed = True
                waypoint.occupied_by = pebble.id
                waypoint.claimed_by = None
                pebble.claimed_by = None
                if self.selected_pebble == pebble:
                    self.selected_pebble = None
                    self.selected_waypoint = None
                    self.selected_waypoint_group = "primary"
                    self.concentrating = False
                    self.concentrate_mode = None
                if (
                    pebble.target_group == "primary"
                    and not self.transit_unlocked_announced
                    and self.pebble_waypoints
                    and all(waypoint.occupied_by is not None for waypoint in self.pebble_waypoints)
                ):
                    self.transit_unlocked_announced = True
                    self.phase = "transit_unlock_focus"
                    self.transit_time = 0
                if self.companion_waypoints and all(waypoint.occupied_by is not None for waypoint in self.companion_waypoints):
                    self.collect_pebbles_02_complete = True
    def terrain_lift_at(self, pos):
        lift = 0.0
        for pebble in self.concentrate_pebbles:
            if not pebble.placed or pebble.moving or pebble.held:
                continue
            distance = pos.distance_to(pebble.pos)
            if distance >= PEBBLE_TERRAIN_RADIUS:
                continue
            t = 1.0 - distance / PEBBLE_TERRAIN_RADIUS
            lift = max(lift, PEBBLE_TERRAIN_MAX_LIFT * smoothstep(t))
        return lift
    def update_mushroom_terrain_lifts(self, dt):
        follow = min(1.0, dt * PEBBLE_TERRAIN_FOLLOW_SPEED)
        target = self.terrain_lift_at(self.player.pos)
        self.player.terrain_lift += (target - self.player.terrain_lift) * follow
        if abs(self.player.terrain_lift - target) < 0.05:
            self.player.terrain_lift = target
        for npc in self.npc_mushrooms:
            target = self.terrain_lift_at(npc.pos)
            npc.terrain_lift += (target - npc.terrain_lift) * follow
            if abs(npc.terrain_lift - target) < 0.05:
                npc.terrain_lift = target
    def update_channel_cover_leaves(self, dt):
        for leaf in self.channel_cover_leaves:
            leaf.sway_phase += dt * 2.4
            if not leaf.moving or leaf.move_start is None:
                continue
            leaf.move_progress = min(1.0, leaf.move_progress + dt / CHANNEL_COVER_LEAF_GLIDE_SECONDS)
            ease = smoothstep(leaf.move_progress)
            leaf.pos = leaf.move_start.lerp(leaf.target, ease)
            if leaf.move_progress >= 1.0:
                leaf.pos = leaf.target.copy()
                leaf.moving = False
                leaf.placed = True
                leaf.move_start = None
                leaf.move_progress = 0.0
    def resolve_pebble_target_waypoint(self, pebble):
        if pebble.target_waypoint is None:
            return None
        waypoints = self.companion_waypoints if pebble.target_group == "companion" else self.pebble_waypoints
        if 0 <= pebble.target_waypoint < len(waypoints):
            return waypoints[pebble.target_waypoint]
        return None
    def pebble_element_color(self, pebble):
        waypoint = self.resolve_pebble_target_waypoint(pebble)
        return waypoint.color if waypoint else MYCELIUM_FAINT
    def pebble_charge(self, pebble):
        waypoint = self.resolve_pebble_target_waypoint(pebble)
        return waypoint.charge if waypoint else 0.0
    def selected_primary_waypoint_color(self):
        if self.selected_waypoint is None:
            return MYCELIUM_FAINT
        waypoints = self.companion_waypoints if self.selected_waypoint_group == "companion" else self.pebble_waypoints
        if 0 <= self.selected_waypoint < len(waypoints):
            return waypoints[self.selected_waypoint].color
        return MYCELIUM_FAINT
    def update_held_concentrate_rock(self, dt):
        self.player.trigger_pulse()
    def release_concentrate_rock(self):
        self.concentrating = False
        self.concentrate_mode = None
        self.concentrate_rock.held = False
    @property
    def controls_enabled(self):
        return (
            self.intro_complete
            and not self.options_open
            and not self.guidance_active()
            and self.phase not in ("feed_complete_focus", "feed_complete_return", "concentrate_unlock", *TRANSIT_UNLOCK_PHASES, "transit_select", "transit_disappear", "transit_pan", "transit_appear")
        )
    @property
    def cinematic_locked(self):
        return self.phase in ("feed_complete_focus", "concentrate_unlock", "feed_complete_return", *TRANSIT_UNLOCK_PHASES)
    @property
    def story_beat_locked(self):
        return self.phase in ("feed_complete_focus", "concentrate_unlock", "feed_complete_return", *TRANSIT_UNLOCK_PHASES)
    def skip_locked_cinematic(self):
        if self.cinematic_locked:
            if self.phase in TRANSIT_UNLOCK_PHASES:
                self.phase = "transit"
            else:
                self.phase = "post_feed"
            self.cinematic_time = 0
            self.transit_time = 0
            self.concentrating = False
            self.concentrate_mode = None
            self.concentrate_rock.held = False
    def camera_target(self):
        if self.phase in ("feed_complete_focus", "concentrate_unlock", "transit_unlock_focus", "transit_unlock"):
            return pygame.Vector2(0, 0), 0.52, 0.028
        if self.phase in ("feed_complete_return", "transit_unlock_return"):
            return self.player.pos, 1.0, 0.026
        if self.transit_targeting:
            return pygame.Vector2(0, 0), 0.52, 0.045
        if self.npc_mushrooms:
            return self.group_camera_target()
        if self.phase in ("transit_pan", "transit_appear") and self.transit_target is not None:
            return self.group_camera_target([self.transit_target])
        return self.player.pos, 1.0, 0.08
    def group_camera_target(self, extra_positions=None):
        positions = [self.player.pos] + [npc.pos for npc in self.npc_mushrooms]
        if self.transit_target is not None and self.phase in ("transit_disappear", "transit_pan", "transit_appear"):
            positions.append(self.transit_target)
        for npc in self.npc_mushrooms:
            if npc.transit_target is not None:
                positions.append(npc.transit_target)
        if extra_positions:
            positions.extend(extra_positions)
        min_x = min(pos.x for pos in positions)
        max_x = max(pos.x for pos in positions)
        min_z = min(pos.y for pos in positions)
        max_z = max(pos.y for pos in positions)
        center = pygame.Vector2((min_x + max_x) * 0.5, (min_z + max_z) * 0.5)
        width = max(1, max_x - min_x)
        height = max(1, (max_z - min_z) * DEPTH_SCALE)
        zoom_x = (SCREEN_WIDTH * 0.68) / (width + 360)
        zoom_y = (SCREEN_HEIGHT * 0.58) / (height + 260)
        zoom = max(0.42, min(1.0, min(zoom_x, zoom_y)))
        speed = 0.045 if zoom < 0.92 else 0.06
        return center, zoom, speed
    def update_leaf_feeding(self, dt):
        for leaf in self.leaf_decals:
            if leaf.connected:
                continue
            if not leaf.lumen_consumed:
                continue
            if self.player.pos.distance_to(pygame.Vector2(leaf.x, leaf.z)) <= LEAF_ACTIVATION_RADIUS:
                leaf.feed_progress = min(1.0, leaf.feed_progress + dt / LEAF_FEED_SECONDS)
                self.player.request_channel()
                self.player.moving = False
                if leaf.feed_progress >= 1:
                    leaf.connected = True
                    self.root_count += 1
                break
        if self.leaf_decals and all(leaf.connected for leaf in self.leaf_decals):
            self.phase = "feed_complete_focus"
            self.cinematic_time = 0
    def spawn_leaf_quest_lumens(self):
        if self.leaf_quest_lumens or not self.leaf_decals:
            return
        start = self.player.pos.copy()
        self.leaf_quest_lumens = []
        for index, leaf in enumerate(self.leaf_decals):
            lumen = LeafQuestLumen(
                leaf_index=index,
                start=start.copy(),
                target=pygame.Vector2(leaf.x, leaf.z),
                delay=index * LEAF_LUMEN_STAGGER_SECONDS,
                phase=index * 1.73,
            )
            self.leaf_quest_lumens.append(lumen)
    def update_leaf_quest_lumens(self, dt):
        if not self.leaf_quest_lumens:
            return
        for lumen in self.leaf_quest_lumens:
            if lumen.delay > 0:
                lumen.delay = max(0.0, lumen.delay - dt)
                continue
            if not lumen.arrived:
                lumen.progress = min(1.0, lumen.progress + dt / LEAF_LUMEN_TRAVEL_SECONDS)
            if lumen.consumed:
                lumen.consume_age += dt
                continue
            if not lumen.arrived:
                continue
            if 0 <= lumen.leaf_index < len(self.leaf_decals):
                leaf = self.leaf_decals[lumen.leaf_index]
                if not leaf.lumen_consumed and self.player.pos.distance_to(pygame.Vector2(leaf.x, leaf.z)) <= LEAF_ACTIVATION_RADIUS:
                    leaf.lumen_consumed = True
                    lumen.consumed = True
                    lumen.consume_age = 0
                    self.player.trigger_pulse()
        self.leaf_quest_lumens = [lumen for lumen in self.leaf_quest_lumens if lumen.visible]
    def update_feed_cinematic(self, dt):
        self.cinematic_time += dt
        if self.phase == "feed_complete_focus" and self.cinematic_time >= FEED_COMPLETE_FOCUS_SECONDS:
            self.phase = "concentrate_unlock"
            self.cinematic_time = 0
        elif self.phase == "concentrate_unlock" and self.cinematic_time >= CONCENTRATE_UNLOCK_SECONDS:
            self.phase = "feed_complete_return"
            self.cinematic_time = 0
        elif self.phase == "feed_complete_return" and self.cinematic_time >= FEED_COMPLETE_RETURN_SECONDS:
            self.phase = "post_feed"
            self.cinematic_time = 0
    def cycle_transit_destination(self, direction):
        if not self.transit_destinations:
            return
        self.selected_transit_destination = (self.selected_transit_destination + direction) % len(self.transit_destinations)
    def start_transit(self, target=None):
        if target is not None:
            self.transit_target = self.clamp_world_target(target)
            if not self.transit_used:
                self.spawn_npcs_after_transit = True
        elif not self.transit_destinations:
            return
        elif not self.transit_used:
            self.transit_target = self.spawn.copy()
            self.spawn_npcs_after_transit = True
        else:
            self.transit_target = self.transit_destinations[self.selected_transit_destination].copy()
        if target is None and self.transit_used and self.player.pos.distance_to(self.transit_target) < 8:
            self.cycle_transit_destination(1)
            self.transit_target = self.transit_destinations[self.selected_transit_destination].copy()
        self.transit_used = True
        self.transit_origin = self.player.pos.copy()
        self.transit_prompt_open = False
        self.transit_targeting = False
        self.phase = "transit_disappear"
        self.transit_time = 0
        self.player.moving = False
        self.player.clear_walk_target()
    def update_transit(self, dt):
        self.transit_time += dt
        self.player.moving = False
        self.player.height = 0
        self.player.vertical_velocity = 0
        self.player.grounded = True
        self.player.pulse_timer = 0.0
        if self.phase == "transit_unlock_focus" and self.transit_time >= TRANSIT_UNLOCK_FOCUS_SECONDS:
            self.phase = "transit_unlock"
            self.transit_time = 0
        elif self.phase == "transit_unlock" and self.transit_time >= TRANSIT_UNLOCK_SECONDS:
            self.phase = "transit_unlock_return"
            self.transit_time = 0
        elif self.phase == "transit_unlock_return" and self.transit_time >= TRANSIT_UNLOCK_RETURN_SECONDS:
            self.phase = "transit"
            self.transit_time = 0
        elif self.phase == "transit_disappear" and self.transit_time >= TRANSIT_SHRINK_SECONDS:
            self.phase = "transit_pan"
            self.transit_time = 0
            if self.transit_target is not None:
                self.player.pos = self.find_open_mushroom_position(self.transit_target)
        elif self.phase == "transit_pan" and self.transit_time >= TRANSIT_PAN_SECONDS:
            self.phase = "transit_appear"
            self.transit_time = 0
        elif self.phase == "transit_appear" and self.transit_time >= TRANSIT_GROW_SECONDS:
            self.phase = "transit"
            self.transit_time = 0
            self.transit_target = None
            if self.spawn_npcs_after_transit:
                self.spawn_npc_mushrooms()
                self.spawn_npcs_after_transit = False
    def update_moving_ferns(self, dt):
        for fern in self.fern_fronds:
            fern.sway_phase += dt * 2.2
            if not fern.moving or fern.move_start is None or fern.target_leaf is None or fern.target_slot is None:
                continue
            if fern.target_leaf >= len(self.leaf_decals):
                fern.moving = False
                fern.held = False
                continue
            leaf = self.leaf_decals[fern.target_leaf]
            slot_offset = pygame.Vector2(-34, -16) if fern.target_slot == 0 else pygame.Vector2(34, 18)
            target = pygame.Vector2(leaf.x, leaf.z) + slot_offset
            fern.move_progress = min(1.0, fern.move_progress + dt / FERN_GLIDE_SECONDS)
            t = fern.move_progress
            ease = t * t * (3 - 2 * t)
            fern.pos = fern.move_start.lerp(target, ease)
            if fern.move_progress >= 1.0:
                fern.pos = target
                fern.moving = False
                fern.held = False
                fern.placed = True
                player_claimed = fern.claimed_by == -1
                fern.claimed_by = None
                leaf.fern_slots[fern.target_slot] = fern.id
                if player_claimed and self.concentrate_mode == "fern_move":
                    self.concentrating = False
                    self.concentrate_mode = None
                if all(leaf.fern_slots and all(slot is not None for slot in leaf.fern_slots) for leaf in self.leaf_decals):
                    self.collect_ferns_03_complete = True
    def update_water_beat(self, dt):
        if self.drop_active:
            self.drop_progress += dt / 0.72
            if self.drop_progress >= 1:
                self.drop_active = False
                self.drop_progress = 0
                self.drop_timer = 2.2 + 1.3 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.0017))
                impact = self.puddle_pos + self.puddle_drop_offset
                self.ripples.append(Ripple(impact.x, impact.y, radius_scale=0.62))
        else:
            self.drop_timer -= dt
            if self.drop_timer <= 0:
                self.drop_active = True
                self.drop_progress = 0

        for ripple in self.ripples:
            ripple.age += dt
        self.ripples = [ripple for ripple in self.ripples if ripple.age < 1.6]
