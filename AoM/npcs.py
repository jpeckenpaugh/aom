import math
import random

import pygame

from config import *
from entities import *
from game_backed import GameBackedManager
from utils import *


class NPCManager(GameBackedManager):
    def spawn_npc_mushrooms(self):
        if self.npc_mushrooms:
            return
        offsets = (pygame.Vector2(-64, 34), pygame.Vector2(64, 34))
        for index, offset in enumerate(offsets):
            pos = self.player.pos + offset
            npc = NpcMushroom(
                pos.copy(),
                pos.copy(),
                index * 1.7,
                pos.copy(),
                sprite_variant=self.choose_balanced_mushroom_variant(),
            )
            self.npc_mushrooms.append(self.apply_mushroom_profile(npc))
    def update_npc_mushrooms(self, dt):
        if not self.npc_mushrooms:
            return
        for npc in self.npc_mushrooms:
            npc.channel_requested = False
        for npc in self.npc_mushrooms:
            npc.spawn_age = min(NPC_GROW_SECONDS, npc.spawn_age + dt)
            self.update_npc_self_transit(npc, dt)
            self.update_npc_division(npc, dt)
        if any(npc.spawn_age < NPC_GROW_SECONDS for npc in self.npc_mushrooms):
            for npc in self.npc_mushrooms:
                npc.moving = False
            return
        if any(npc.transit_phase or npc.dividing for npc in self.npc_mushrooms):
            return
        if self.phase == "transit" and not self.collect_pebbles_02_complete:
            self.update_npc_collect_pebbles_02(dt)
            return
        if self.phase == "transit" and self.collect_pebbles_02_complete and not self.collect_ferns_03_complete:
            self.update_npc_collect_ferns_03(dt)
            return
        if self.phase == "transit" and self.collect_ferns_03_complete and not self.charge_stones_04_complete:
            self.update_npc_charge_stones_04(dt)
            return
        if self.regen_beat_active():
            self.update_npc_regen_06(dt)
            return
        if self.training_beat_active:
            self.update_npc_training_05(dt)
            return
        for npc in self.npc_mushrooms:
            npc.phase += dt
            if npc.pos.distance_to(npc.target) < 8 or int(npc.phase * 10) % 37 == 0:
                wander = pygame.Vector2(math.cos(npc.phase * 1.7), math.sin(npc.phase * 1.13)) * 54
                npc.target = npc.home + wander
            direction = npc.target - npc.pos
            npc.moving = direction.length_squared() > 16
            if npc.moving:
                step = min(direction.length(), 58 * dt)
                npc.pos += direction.normalize() * step
    def update_npc_collect_pebbles_02(self, dt):
        for npc_index, npc in enumerate(self.npc_mushrooms):
            npc.phase += dt
            if not self.npc_ready_for_task(npc, dt):
                continue
            if npc.task == "idle":
                self.assign_npc_collect_task(npc_index, npc)
            if npc.task == "seek_pebble":
                pebble = self.get_pebble_by_id(npc.pebble_id)
                waypoint = self.get_companion_waypoint(npc.waypoint_id)
                if (
                    pebble is None
                    or waypoint is None
                    or pebble.placed
                    or waypoint.occupied_by is not None
                    or pebble.claimed_by != npc_index
                    or waypoint.claimed_by != npc_index
                ):
                    self.clear_npc_task(npc)
                    continue
                npc.target = pebble.pos.copy()
                self.move_npc_toward(npc, npc.target, 72, dt)
                if npc.pos.distance_to(pebble.pos) <= CONCENTRATE_PEBBLE_RANGE * 0.65:
                    self.start_npc_pebble_move(npc, pebble, waypoint)
            elif npc.task == "guiding_pebble":
                pebble = self.get_pebble_by_id(npc.pebble_id)
                waypoint = self.get_companion_waypoint(npc.waypoint_id)
                if pebble is None or waypoint is None or waypoint.claimed_by != npc_index:
                    self.clear_npc_task(npc)
                    continue
                if pebble.placed:
                    npc.home = waypoint.pos.copy()
                    self.clear_npc_task(npc)
                    continue
                npc.target = pebble.pos.copy()
                self.move_npc_toward(npc, npc.target, 82, dt)
    def assign_npc_collect_task(self, npc_index, npc):
        open_waypoints = [
            (index, waypoint)
            for index, waypoint in enumerate(self.companion_waypoints)
            if waypoint.occupied_by is None and waypoint.claimed_by is None
        ]
        open_pebbles = [
            pebble
            for pebble in self.concentrate_pebbles
            if not pebble.placed and not pebble.moving and not pebble.held and pebble.claimed_by is None
        ]
        if not open_waypoints or not open_pebbles:
            npc.moving = False
            return
        pebble = min(open_pebbles, key=lambda item: (npc.pos.distance_to(item.pos), item.id))
        waypoint_index, waypoint = min(open_waypoints, key=lambda item: (pebble.pos.distance_to(item[1].pos), item[0]))
        if not self.try_claim_pebble(pebble, npc_index):
            npc.moving = False
            return
        if not self.try_claim_waypoint(waypoint, npc_index):
            pebble.claimed_by = None
            npc.moving = False
            return
        npc.pebble_id = pebble.id
        npc.waypoint_id = waypoint_index
        npc.task = "seek_pebble"
        npc.target = pebble.pos.copy()
    def start_npc_pebble_move(self, npc, pebble, waypoint):
        npc_index = self.npc_mushrooms.index(npc) if npc in self.npc_mushrooms else None
        if npc_index is None or pebble.claimed_by != npc_index or waypoint.claimed_by != npc_index:
            self.clear_npc_task(npc)
            return
        pebble.target_group = "companion"
        pebble.target_waypoint = npc.waypoint_id
        pebble.move_start = pebble.pos.copy()
        pebble.move_progress = 0
        pebble.moving = True
        pebble.held = True
        npc.task = "guiding_pebble"
    def clear_npc_task(self, npc):
        npc_index = self.npc_mushrooms.index(npc) if npc in self.npc_mushrooms else None
        pebble = self.get_pebble_by_id(npc.pebble_id)
        if (
            npc_index is not None
            and pebble is not None
            and pebble.claimed_by == npc_index
            and not pebble.held
            and not pebble.moving
            and not pebble.placed
        ):
            pebble.claimed_by = None
        fern = self.get_fern_by_id(npc.fern_id)
        if (
            npc_index is not None
            and fern is not None
            and fern.claimed_by == npc_index
            and not fern.held
            and not fern.moving
            and not fern.placed
        ):
            fern.claimed_by = None
            fern.target_leaf = None
            fern.target_slot = None
        waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
        if waypoint is not None and waypoint.claimed_by != -1 and (npc_index is None or waypoint.claimed_by == npc_index):
            waypoint.claimed_by = None
        npc.task = "idle"
        npc.pebble_id = None
        npc.waypoint_id = None
        npc.waypoint_group = "companion"
        npc.fern_id = None
        npc.leaf_id = None
        npc.fern_slot = None
        if npc.task != "cast_elemental_spell":
            npc.element_focus = None
        npc.cast_time = 0.0
        npc.regen_time = 0.0
        npc.moving = False
        npc.rest_timer = random.uniform(NPC_REST_MIN_SECONDS, NPC_REST_MAX_SECONDS)
    def npc_ready_for_task(self, npc, dt):
        if npc.task != "idle":
            return True
        if npc.rest_timer > 0:
            npc.rest_timer = max(0.0, npc.rest_timer - dt)
            npc.moving = False
            return False
        return True
    def move_npc_toward(self, npc, target, speed, dt):
        direction = target - npc.pos
        if direction.length() > NPC_TRANSIT_DISTANCE and npc.task not in ("guiding_pebble", "guiding_fern"):
            self.start_npc_self_transit(npc, target)
            npc.moving = False
            return
        npc.moving = direction.length_squared() > 16
        if npc.moving:
            step = min(direction.length(), speed * dt)
            npc.pos += direction.normalize() * step
    def request_npc_channel(self, npc):
        npc.channel_requested = True
    def update_npc_channel_states(self, dt):
        for npc in self.npc_mushrooms:
            self.update_npc_channel_state(npc, dt)
    def update_npc_channel_state(self, npc, dt):
        if npc.channel_requested:
            if npc.channel_phase is None:
                npc.channel_phase = "start"
                npc.channel_time = 0.0
            elif npc.channel_phase == "end":
                npc.channel_phase = "start"
                npc.channel_time = max(0.0, MUSHROOM_PULSE_EDGE_SECONDS - npc.channel_time)
            elif npc.channel_phase == "start":
                npc.channel_time += dt
                if npc.channel_time >= MUSHROOM_PULSE_EDGE_SECONDS:
                    npc.channel_phase = "loop"
                    npc.channel_time = 0.0
            elif npc.channel_phase == "loop":
                npc.channel_time += dt
        elif npc.channel_phase in ("start", "loop"):
            npc.channel_phase = "end"
            npc.channel_time = 0.0
        elif npc.channel_phase == "end":
            npc.channel_time += dt
            if npc.channel_time >= MUSHROOM_PULSE_EDGE_SECONDS:
                npc.channel_phase = None
                npc.channel_time = 0.0
        npc.channeling = npc.channel_phase is not None
    def start_npc_self_transit(self, npc, target):
        if npc.transit_phase:
            return
        npc.transit_target = pygame.Vector2(target)
        npc.transit_time = 0
        npc.transit_phase = "shrink"
        npc.moving = False
    def update_npc_self_transit(self, npc, dt):
        if not npc.transit_phase:
            npc.body_scale = self.npc_growth_scale(npc)
            return
        npc.transit_time += dt
        npc.moving = False
        if npc.transit_phase == "shrink":
            t = min(1.0, npc.transit_time / NPC_TRANSIT_SHRINK_SECONDS)
            npc.body_scale = self.npc_growth_scale(npc)
            if t >= 1.0:
                if npc.dividing:
                    npc.transit_phase = None
                    npc.transit_time = 0
                    npc.body_scale = 0.012
                    return
                if npc.transit_target is not None:
                    npc.pos = self.find_open_mushroom_position(npc.transit_target, exclude=npc)
                npc.transit_phase = "grow"
                npc.transit_time = 0
        elif npc.transit_phase == "grow":
            t = min(1.0, npc.transit_time / NPC_TRANSIT_GROW_SECONDS)
            npc.body_scale = self.npc_growth_scale(npc)
            if t >= 1.0:
                npc.body_scale = self.npc_growth_scale(npc)
                npc.transit_phase = None
                npc.transit_target = None
                npc.transit_time = 0
    def npc_growth_scale(self, npc):
        if len(self.npc_mushrooms) >= MAX_NPC_MUSHROOMS:
            return 1.34
        return 1.0 + min(NPC_GROWTH_CYCLES_TO_DIVIDE, npc.growth_cycles) * 0.034
    def add_npc_growth_cycle(self, npc, amount=1):
        npc.growth_cycles += amount
        if npc.growth_cycles >= NPC_GROWTH_CYCLES_TO_DIVIDE and len(self.npc_mushrooms) < MAX_NPC_MUSHROOMS:
            npc.pending_division = True
            self.start_npc_division(npc)
    def start_npc_division(self, npc):
        if npc.dividing or npc.transit_phase:
            return
        npc.dividing = True
        npc.divide_time = 0
        npc.divide_origin = npc.pos.copy()
        npc.transit_target = None
        npc.transit_phase = "shrink"
        npc.moving = False
    def update_npc_division(self, npc, dt):
        if not npc.dividing:
            return
        if npc.transit_phase:
            return
        npc.divide_time += dt
        if npc.divide_time >= 0.18:
            self.complete_npc_division(npc)
    def complete_npc_division(self, npc):
        origin = (npc.divide_origin or npc.pos).copy()
        npc.dividing = False
        npc.pending_division = False
        npc.divide_time = 0
        npc.divide_origin = None
        split_offsets = (pygame.Vector2(-54, -24), pygame.Vector2(54, 30))
        first_pos = self.find_open_mushroom_position(origin + split_offsets[0], exclude=npc)
        npc.pos = first_pos.copy()
        npc.home = first_pos.copy()
        npc.target = first_pos.copy()
        npc.growth_cycles = 0
        npc.spawn_age = NPC_GROW_SECONDS
        npc.body_scale = self.npc_growth_scale(npc)
        npc.transit_phase = "grow"
        npc.transit_time = 0
        npc.transit_target = None
        npc.sprite_variant = self.choose_balanced_mushroom_variant()
        self.apply_mushroom_profile(npc)
        if len(self.npc_mushrooms) >= MAX_NPC_MUSHROOMS:
            return
        child_pos = self.find_open_mushroom_position(origin + split_offsets[1])
        child = NpcMushroom(
            child_pos.copy(),
            child_pos.copy(),
            npc.phase + 2.1,
            child_pos.copy(),
            sprite_variant=self.choose_balanced_mushroom_variant(),
        )
        child.spawn_age = NPC_GROW_SECONDS
        child.body_scale = self.npc_growth_scale(child)
        child.transit_phase = "grow"
        child.transit_time = 0
        self.npc_mushrooms.append(self.apply_mushroom_profile(child))
    def find_open_mushroom_position(self, desired, exclude=None):
        desired = pygame.Vector2(desired)
        occupied = [self.player.pos]
        occupied.extend(npc.pos for npc in self.npc_mushrooms if npc is not exclude)
        candidates = [desired]
        for radius in (34, 58, 82, 112):
            for step in range(10):
                angle = step * math.tau / 10 + radius * 0.017
                candidates.append(desired + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius)
        max_radius = CAVE_RADIUS - PLAYER_MARGIN
        for candidate in candidates:
            if candidate.length() > max_radius:
                candidate = candidate.normalize() * max_radius
            if all(candidate.distance_to(pos) >= 42 for pos in occupied):
                return candidate
        return desired
    def get_pebble_by_id(self, pebble_id):
        if pebble_id is None:
            return None
        for pebble in self.concentrate_pebbles:
            if pebble.id == pebble_id:
                return pebble
        return None
    def get_companion_waypoint(self, waypoint_id):
        if waypoint_id is None or waypoint_id < 0 or waypoint_id >= len(self.companion_waypoints):
            return None
        return self.companion_waypoints[waypoint_id]
    def update_npc_collect_ferns_03(self, dt):
        for npc_index, npc in enumerate(self.npc_mushrooms):
            npc.phase += dt
            if npc.task not in ("idle", "seek_fern", "guiding_fern"):
                self.clear_npc_task(npc)
            if not self.npc_ready_for_task(npc, dt):
                continue
            if npc.task == "idle":
                self.assign_npc_fern_task(npc_index, npc)
            if npc.task == "seek_fern":
                fern = self.get_fern_by_id(npc.fern_id)
                if (
                    fern is None
                    or fern.placed
                    or fern.claimed_by != npc_index
                    or fern.target_leaf != npc.leaf_id
                    or fern.target_slot != npc.fern_slot
                ):
                    self.clear_npc_task(npc)
                    continue
                npc.target = fern.pos.copy()
                self.move_npc_toward(npc, npc.target, 72, dt)
                if npc.pos.distance_to(fern.pos) <= CONCENTRATE_PEBBLE_RANGE * 0.65:
                    self.start_npc_fern_move(npc, fern)
            elif npc.task == "guiding_fern":
                fern = self.get_fern_by_id(npc.fern_id)
                if fern is None or fern.claimed_by != npc_index:
                    self.clear_npc_task(npc)
                    continue
                if fern.placed:
                    if fern.target_leaf is not None:
                        leaf = self.leaf_decals[fern.target_leaf]
                        npc.home = pygame.Vector2(leaf.x, leaf.z)
                    self.clear_npc_task(npc)
                    continue
                npc.target = fern.pos.copy()
                self.move_npc_toward(npc, npc.target, 82, dt)
    def assign_npc_fern_task(self, npc_index, npc):
        open_slots = []
        for leaf_index, leaf in enumerate(self.leaf_decals):
            for slot_index, fern_id in enumerate(leaf.fern_slots or []):
                if fern_id is None:
                    if not self.fern_slot_claimed(leaf_index, slot_index):
                        open_slots.append((leaf_index, slot_index, pygame.Vector2(leaf.x, leaf.z)))
        open_ferns = [fern for fern in self.fern_fronds if not fern.placed and not fern.moving and not fern.held and fern.claimed_by is None]
        if not open_slots or not open_ferns:
            npc.moving = False
            return
        fern = min(open_ferns, key=lambda item: (npc.pos.distance_to(item.pos), item.id))
        leaf_index, slot_index, slot_pos = min(open_slots, key=lambda item: (fern.pos.distance_to(item[2]), item[0], item[1]))
        if not self.try_claim_fern_task(fern, leaf_index, slot_index, npc_index):
            npc.moving = False
            return
        npc.fern_id = fern.id
        npc.leaf_id = leaf_index
        npc.fern_slot = slot_index
        npc.task = "seek_fern"
        npc.target = fern.pos.copy()
    def start_npc_fern_move(self, npc, fern):
        npc_index = self.npc_mushrooms.index(npc) if npc in self.npc_mushrooms else None
        if (
            npc_index is None
            or fern.claimed_by != npc_index
            or fern.target_leaf != npc.leaf_id
            or fern.target_slot != npc.fern_slot
        ):
            self.clear_npc_task(npc)
            return
        fern.move_start = fern.pos.copy()
        fern.move_progress = 0
        fern.moving = True
        fern.held = True
        npc.task = "guiding_fern"
    def all_stone_waypoints(self):
        return [("primary", index, waypoint) for index, waypoint in enumerate(self.pebble_waypoints)] + [
            ("companion", index, waypoint) for index, waypoint in enumerate(self.companion_waypoints)
        ]
    def update_waypoint_visual_charges(self, dt):
        follow = min(1.0, dt * 4.4)
        for _, _, waypoint in self.all_stone_waypoints():
            target = max(0.0, min(1.0, waypoint.charge))
            waypoint.visible_charge += (target - waypoint.visible_charge) * follow
            if abs(waypoint.visible_charge - target) < 0.002:
                waypoint.visible_charge = target
    def chargeable_stone_waypoints(self):
        return [
            (group, index, waypoint)
            for group, index, waypoint in self.all_stone_waypoints()
            if waypoint.occupied_by is not None and waypoint.charge < 1.0
        ]
    def update_player_stone_charging(self, dt):
        candidates = [
            (group, index, waypoint)
            for group, index, waypoint in self.chargeable_stone_waypoints()
            if self.player.pos.distance_to(waypoint.pos) <= STONE_CHARGE_RADIUS
            and (waypoint.claimed_by is None or waypoint.claimed_by == -1)
        ]
        if self.auto_guide_enabled and self.auto_guide_stone_kind == "charge":
            candidates = [
                item
                for item in candidates
                if item[0] == self.auto_guide_stone_group and item[1] == self.auto_guide_stone_id
            ]
        if not candidates:
            return
        group, index, waypoint = min(candidates, key=lambda item: (self.player.pos.distance_to(item[2].pos), 0 if item[0] == "primary" else 1, item[1]))
        waypoint.charge = min(1.0, waypoint.charge + STONE_CHARGE_RATE * dt)
        self.player.request_channel()
        self.player.moving = False
        if waypoint.charge >= 1.0 and waypoint.claimed_by == -1:
            waypoint.claimed_by = None
            if self.auto_guide_stone_kind == "charge" and self.auto_guide_stone_group == group and self.auto_guide_stone_id == index:
                self.clear_auto_guide_stone_reservation()
        self.finish_stone_charge_if_complete()
    def update_npc_charge_stones_04(self, dt):
        for npc_index, npc in enumerate(self.npc_mushrooms):
            npc.phase += dt
            if npc.task not in ("idle", "seek_charge_stone", "charge_stone"):
                self.clear_npc_task(npc)
            if not self.npc_ready_for_task(npc, dt):
                continue
            if npc.task == "idle":
                self.assign_npc_charge_task(npc_index, npc)
            if npc.task == "seek_charge_stone":
                waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
                if waypoint is None or waypoint.occupied_by is None or waypoint.charge >= 1.0 or waypoint.claimed_by != npc_index:
                    self.clear_npc_task(npc)
                    continue
                npc.target = waypoint.pos.copy()
                self.move_npc_toward(npc, npc.target, 66, dt)
                if npc.pos.distance_to(waypoint.pos) <= STONE_CHARGE_RADIUS * 0.55:
                    npc.task = "charge_stone"
                    npc.moving = False
            elif npc.task == "charge_stone":
                waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
                if waypoint is None or waypoint.occupied_by is None or waypoint.claimed_by != npc_index:
                    self.clear_npc_task(npc)
                    continue
                npc.target = waypoint.pos.copy()
                if npc.pos.distance_to(waypoint.pos) > STONE_CHARGE_RADIUS * 0.75:
                    npc.task = "seek_charge_stone"
                    continue
                npc.moving = False
                self.request_npc_channel(npc)
                waypoint.charge = min(1.0, waypoint.charge + STONE_CHARGE_RATE * dt)
                if waypoint.charge >= 1.0:
                    self.add_npc_growth_cycle(npc)
                    npc.home = waypoint.pos.copy()
                    waypoint.claimed_by = None
                    self.clear_npc_task(npc)
                self.finish_stone_charge_if_complete()
    def assign_npc_charge_task(self, npc_index, npc):
        open_stones = [
            (group, index, waypoint)
            for group, index, waypoint in self.chargeable_stone_waypoints()
            if waypoint.claimed_by is None
        ]
        if not open_stones:
            npc.moving = False
            return
        group, index, waypoint = min(open_stones, key=lambda item: (npc.pos.distance_to(item[2].pos), 0 if item[0] == "primary" else 1, item[1]))
        if not self.try_claim_stone_waypoint(waypoint, npc_index, "charge"):
            npc.moving = False
            return
        npc.waypoint_group = group
        npc.waypoint_id = index
        npc.task = "seek_charge_stone"
        npc.target = waypoint.pos.copy()
    def get_waypoint(self, group, waypoint_id):
        waypoints = self.companion_waypoints if group == "companion" else self.pebble_waypoints
        if waypoint_id is None or waypoint_id < 0 or waypoint_id >= len(waypoints):
            return None
        return waypoints[waypoint_id]
    def finish_stone_charge_if_complete(self):
        occupied = [waypoint for _, _, waypoint in self.all_stone_waypoints() if waypoint.occupied_by is not None]
        if len(occupied) >= 15 and all(waypoint.charge >= 1.0 for waypoint in occupied):
            self.charge_stones_04_complete = True
    def charged_stone_waypoints(self):
        return [
            (group, index, waypoint)
            for group, index, waypoint in self.all_stone_waypoints()
            if waypoint.occupied_by is not None and waypoint.charge >= 1.0
        ]
    def any_charged_stones(self):
        return any(waypoint.charge >= 1.0 for _, _, waypoint in self.all_stone_waypoints() if waypoint.occupied_by is not None)
    def player_cast_training_spell(self, preferred_stone=None):
        if not self.training_beat_active:
            return False
        candidates = [
            (group, index, waypoint)
            for group, index, waypoint in self.charged_stone_waypoints()
            if self.player.pos.distance_to(waypoint.pos) <= SPELL_CHARGE_RADIUS
            and (waypoint.claimed_by is None or waypoint.claimed_by == -1)
        ]
        if preferred_stone is not None:
            candidates = [
                item
                for item in candidates
                if item[0] == preferred_stone[0] and item[1] == preferred_stone[1]
            ]
        if not candidates:
            return False
        group, index, waypoint = min(candidates, key=lambda item: (self.player.pos.distance_to(item[2].pos), 0 if item[0] == "primary" else 1, item[1]))
        direction = self.player.facing.copy()
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        self.cast_elemental_spell(self.player.pos, direction, waypoint)
        if self.auto_guide_stone_kind == "cast" and self.auto_guide_stone_group == group and self.auto_guide_stone_id == index:
            self.clear_auto_guide_stone_reservation()
        self.player.trigger_pulse()
        return True
    def update_npc_training_05(self, dt):
        for npc_index, npc in enumerate(self.npc_mushrooms):
            npc.phase += dt
            if npc.task not in ("idle", "seek_training_stone", "cast_elemental_spell"):
                self.clear_npc_task(npc)
            if not self.any_charged_stones():
                self.charge_stones_04_complete = False
                self.clear_npc_task(npc)
                continue
            if not self.npc_ready_for_task(npc, dt):
                continue
            if npc.task == "idle":
                self.assign_npc_training_task(npc_index, npc)
            if npc.task == "seek_training_stone":
                waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
                if waypoint is None or waypoint.occupied_by is None or waypoint.charge < 1.0 or waypoint.claimed_by != npc_index:
                    self.finish_npc_training_task(npc)
                    continue
                npc.target = waypoint.pos.copy()
                self.move_npc_toward(npc, npc.target, 76, dt)
                if npc.pos.distance_to(waypoint.pos) <= SPELL_CHARGE_RADIUS * 0.58:
                    npc.task = "cast_elemental_spell"
                    npc.cast_time = -random.uniform(0.0, 0.85)
                    npc.moving = False
            elif npc.task == "cast_elemental_spell":
                waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
                if waypoint is None or waypoint.charge < 1.0 or waypoint.claimed_by != npc_index:
                    self.finish_npc_training_task(npc)
                    continue
                npc.cast_time += dt
                npc.moving = False
                self.request_npc_channel(npc)
                if npc.cast_time < SPELL_ABSORB_SECONDS:
                    continue
                direction = waypoint.pos.copy()
                if direction.length_squared() == 0:
                    direction = pygame.Vector2(math.cos(npc.phase), math.sin(npc.phase))
                self.cast_elemental_spell(npc.pos, direction, waypoint, npc)
                npc.home = waypoint.pos.copy()
                same_element_remaining = any(
                    stone.element == waypoint.element and stone.charge >= 1.0
                    for _, _, stone in self.charged_stone_waypoints()
                )
                npc.element_focus = waypoint.element if same_element_remaining else None
                self.finish_npc_training_task(npc)
        if not self.any_charged_stones():
            self.charge_stones_04_complete = False
    def regen_beat_active(self):
        return (
            self.phase == "transit"
            and len(self.npc_mushrooms) >= MAX_NPC_MUSHROOMS
            and self.all_elements_at_max_level()
            and any(npc.growth_cycles >= NPC_GROWTH_CYCLES_TO_DIVIDE for npc in self.npc_mushrooms)
            and bool(self.available_regen_waypoints())
        )
    def all_elements_at_max_level(self):
        return all(self.elemental_spell_level(element) >= SPELL_MAX_LEVEL for element, _ in ELEMENTS)
    def regen_counts_by_element(self):
        counts = {element: 0 for element, _ in ELEMENTS}
        for _, _, waypoint in self.all_stone_waypoints():
            if waypoint.regen_offsets:
                counts[waypoint.element] = counts.get(waypoint.element, 0) + 1
        return counts
    def available_regen_waypoints(self):
        return [
            (group, index, waypoint)
            for group, index, waypoint in self.all_stone_waypoints()
            if waypoint.occupied_by is not None and not waypoint.regen_offsets and waypoint.claimed_by is None
        ]
    def update_npc_regen_06(self, dt):
        for npc_index, npc in list(enumerate(self.npc_mushrooms)):
            npc.phase += dt
            if npc.task not in ("idle", "seek_regen_stone", "regen_shrink"):
                self.clear_npc_task(npc)
            if npc.task == "idle":
                if npc.growth_cycles < NPC_GROWTH_CYCLES_TO_DIVIDE:
                    continue
                self.assign_npc_regen_task(npc_index, npc)
            if npc.task == "seek_regen_stone":
                waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
                if waypoint is None or waypoint.occupied_by is None or waypoint.regen_offsets or waypoint.claimed_by != npc_index:
                    self.clear_npc_task(npc)
                    continue
                npc.target = waypoint.pos.copy()
                self.move_npc_toward(npc, npc.target, 78, dt)
                if npc.pos.distance_to(waypoint.pos) <= STONE_CHARGE_RADIUS * 0.55:
                    npc.task = "regen_shrink"
                    npc.regen_time = 0.0
                    npc.moving = False
            elif npc.task == "regen_shrink":
                waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
                if waypoint is None or waypoint.claimed_by != npc_index:
                    self.clear_npc_task(npc)
                    continue
                npc.regen_time += dt
                t = min(1.0, npc.regen_time / REGEN_SHRINK_SECONDS)
                npc.body_scale = self.npc_growth_scale(npc) * max(0.012, 1 - (t * t * (3 - 2 * t)))
                npc.moving = False
                if t >= 1.0:
                    self.complete_npc_regen(npc, waypoint)
                    return
    def assign_npc_regen_task(self, npc_index, npc):
        candidates = self.available_regen_waypoints()
        if not candidates:
            return
        counts = self.regen_counts_by_element()
        group, index, waypoint = min(candidates, key=lambda item: (counts.get(item[2].element, 0), npc.pos.distance_to(item[2].pos), 0 if item[0] == "primary" else 1, item[1]))
        if not self.try_claim_stone_waypoint(waypoint, npc_index, "regen"):
            npc.moving = False
            return
        npc.waypoint_group = group
        npc.waypoint_id = index
        npc.task = "seek_regen_stone"
        npc.target = waypoint.pos.copy()
    def complete_npc_regen(self, npc, waypoint):
        rng = random.Random(round(waypoint.pos.x * 13 + waypoint.pos.y * 17) + len(waypoint.regen_offsets) * 97)
        count = REGEN_MINI_MUSHROOM_COUNT
        waypoint.regen_offsets = []
        for index in range(count):
            angle = index * math.tau / count + rng.uniform(-0.22, 0.22)
            radius = rng.uniform(48, 96)
            waypoint.regen_offsets.append(pygame.Vector2(math.cos(angle) * radius, math.sin(angle) * radius))
        waypoint.claimed_by = None
        if npc in self.npc_mushrooms:
            self.npc_mushrooms.remove(npc)
        for candidate in self.npc_mushrooms:
            if len(self.npc_mushrooms) < MAX_NPC_MUSHROOMS and candidate.growth_cycles >= NPC_GROWTH_CYCLES_TO_DIVIDE:
                self.start_npc_division(candidate)
                break
    def assign_npc_training_task(self, npc_index, npc):
        charged = [
            (group, index, waypoint)
            for group, index, waypoint in self.charged_stone_waypoints()
            if waypoint.claimed_by is None
        ]
        if npc.element_focus:
            focused = [item for item in charged if item[2].element == npc.element_focus]
            if focused:
                charged = focused
        if not charged:
            npc.moving = False
            return
        group, index, waypoint = min(charged, key=lambda item: (npc.pos.distance_to(item[2].pos), 0 if item[0] == "primary" else 1, item[1]))
        if not self.try_claim_stone_waypoint(waypoint, npc_index, "cast"):
            npc.moving = False
            return
        npc.waypoint_group = group
        npc.waypoint_id = index
        npc.element_focus = waypoint.element
        npc.task = "seek_training_stone"
        npc.target = waypoint.pos.copy()
    def finish_npc_training_task(self, npc):
        waypoint = self.get_waypoint(npc.waypoint_group, npc.waypoint_id)
        if waypoint is not None and waypoint.claimed_by != -1:
            waypoint.claimed_by = None
        npc.task = "idle"
        npc.waypoint_id = None
        npc.waypoint_group = "companion"
        npc.cast_time = 0.0
        npc.moving = False
        npc.rest_timer = random.uniform(NPC_REST_MIN_SECONDS, NPC_REST_MAX_SECONDS)
    def cast_elemental_spell(self, origin, direction, waypoint, caster_npc=None):
        if waypoint.charge < 1.0:
            return
        direction = pygame.Vector2(direction)
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        direction = direction.normalize()
        waypoint.charge = max(0.0, waypoint.charge - 1.0)
        waypoint.claimed_by = None
        level = self.elemental_spell_level(waypoint.element)
        self.elemental_cast_counts[waypoint.element] = self.elemental_cast_counts.get(waypoint.element, 0) + 1
        self.spawn_elemental_spell_orbs(pygame.Vector2(origin), direction, waypoint.color, waypoint.element, level)
        if caster_npc is not None:
            self.add_npc_growth_cycle(caster_npc)
        if not self.any_charged_stones():
            self.charge_stones_04_complete = False
    def elemental_spell_level(self, element):
        return min(SPELL_MAX_LEVEL, 1 + self.elemental_cast_counts.get(element, 0) // SPELL_CASTS_PER_LEVEL)
    def spawn_elemental_spell_orbs(self, origin, direction, color, element, level):
        if level >= 5:
            self.elemental_spells.append(ElementalSpell(origin, direction, color, element, level=level, size_scale=3.0, burst_on_expire=True))
            return
        orb_count = min(3, level)
        size_scale = 2.0 if level >= 4 else 1.0
        spreads = {1: (0,), 2: (-12, 12), 3: (-18, 0, 18)}[orb_count]
        for index, degrees in enumerate(spreads):
            orb_direction = direction.rotate(degrees)
            self.elemental_spells.append(
                ElementalSpell(origin.copy(), orb_direction, color, element, level=level, size_scale=size_scale, delay=index * 0.09)
            )
    def update_elemental_spells(self, dt):
        expired_bursts = []
        for spell in self.elemental_spells:
            if spell.delay > 0:
                spell.delay = max(0.0, spell.delay - dt)
                continue
            spell.age += dt
            spell.pos += spell.direction * SPELL_SPEED * dt
            if spell.age >= SPELL_LIFETIME and spell.burst_on_expire:
                expired_bursts.append(spell)
        self.elemental_spells = [spell for spell in self.elemental_spells if spell.age < SPELL_LIFETIME or spell.delay > 0]
        for spell in expired_bursts:
            for degrees in (-24, 0, 24):
                self.elemental_spells.append(
                    ElementalSpell(
                        spell.pos.copy(),
                        spell.direction.rotate(degrees),
                        spell.color,
                        spell.element,
                        level=spell.level,
                        size_scale=1.2,
                    )
                )
    def update_regen_mushrooms(self, dt):
        for _, _, waypoint in self.all_stone_waypoints():
            if waypoint.regen_offsets and waypoint.occupied_by is not None and waypoint.charge < 1.0:
                waypoint.charge = min(1.0, waypoint.charge + STONE_CHARGE_RATE * dt)
    def get_fern_by_id(self, fern_id):
        if fern_id is None:
            return None
        for fern in self.fern_fronds:
            if fern.id == fern_id:
                return fern
        return None
