import math
import random

import pygame

from config import *
from entities import *
from game_backed import GameBackedManager
from utils import *


class AutoGuide(GameBackedManager):
    def note_manual_activity(self, stop_auto=True):
        self.auto_guide_idle_time = 0.0
        if self.auto_guide_prompt_open():
            self.auto_guide_prompt_countdown_active = False
        else:
            self.auto_guide_prompt_time = 0.0
        if stop_auto and self.auto_guide_enabled:
            self.stop_auto_guide()
    def start_auto_guide(self, speed_mode="Slow"):
        self.release_auto_guide_reservations()
        self.auto_guide_enabled = True
        self.auto_guide_speed_mode = speed_mode if speed_mode in AUTO_GUIDE_SPEED_OPTIONS[1:] else "Slow"
        self.auto_guide_prompt_time = 0.0
        self.auto_guide_prompt_countdown_active = False
        self.auto_guide_prompt_shown = True
        self.auto_guide_idle_time = 0.0
        self.set_auto_guide_rest("start")
        self.auto_guide_last_target = None
        self.auto_guide_last_rest_kind = "move"
        self.auto_guide_follow_target = None
        self.auto_guide_follow_anchor = None
        self.auto_guide_follow_timer = 0.0
        self.auto_guide_follow_step = AUTO_GUIDE_FOLLOW_STEP_RANGE[0]
        self.reset_auto_guide_watchdog()
        self.transit_prompt_open = False
        self.transit_targeting = False
    def dismiss_auto_guide_prompt(self):
        self.auto_guide_prompt_time = 0.0
        self.auto_guide_prompt_countdown_active = False
        self.auto_guide_idle_time = 0.0
        self.auto_guide_prompt_shown = True
    def auto_guide_prompt_open(self):
        return self.auto_guide_prompt_time > 0 and not self.auto_guide_enabled
    def update_auto_guide_prompt_countdown(self, dt):
        if not self.auto_guide_prompt_countdown_active:
            return
        self.auto_guide_prompt_time = max(0.0, self.auto_guide_prompt_time - dt)
        if self.auto_guide_prompt_time <= 0 and not self.auto_guide_enabled:
            self.start_auto_guide()
    def stop_auto_guide(self):
        self.release_auto_guide_reservations()
        self.auto_guide_enabled = False
        self.auto_guide_speed_mode = "Off"
        self.auto_guide_prompt_time = 0.0
        self.auto_guide_prompt_countdown_active = False
        self.auto_guide_rest_timer = 0.0
        self.auto_guide_last_target = None
        self.auto_guide_follow_target = None
        self.auto_guide_follow_anchor = None
        self.auto_guide_follow_timer = 0.0
        self.auto_guide_follow_step = AUTO_GUIDE_FOLLOW_STEP_RANGE[0]
        self.reset_auto_guide_watchdog()
        self.player.clear_walk_target()
    def handle_auto_guide_prompt_key(self, key):
        if not self.auto_guide_prompt_open():
            return False
        self.auto_guide_prompt_countdown_active = False
        if key in (pygame.K_a, pygame.K_LEFT, pygame.K_w, pygame.K_UP):
            self.auto_guide_prompt_selected = 0
            return True
        if key in (pygame.K_d, pygame.K_RIGHT, pygame.K_s, pygame.K_DOWN):
            self.auto_guide_prompt_selected = 1
            return True
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.auto_guide_prompt_selected == 0:
                self.start_auto_guide()
            else:
                self.dismiss_auto_guide_prompt()
            return True
        if key == pygame.K_ESCAPE:
            self.dismiss_auto_guide_prompt()
            return True
        return True
    def handle_auto_guide_prompt_click(self, pos):
        if not self.auto_guide_prompt_open():
            return False
        if self.auto_guide_start_rect.collidepoint(pos):
            self.auto_guide_prompt_countdown_active = False
            self.auto_guide_prompt_selected = 0
            self.start_auto_guide()
            return True
        if self.auto_guide_dismiss_rect.collidepoint(pos) or self.auto_guide_prompt_rect.collidepoint(pos):
            self.auto_guide_prompt_countdown_active = False
            self.auto_guide_prompt_selected = 1
            self.dismiss_auto_guide_prompt()
            return True
        return False
    def reset_auto_guide_watchdog(self):
        target = self.auto_guide_watchdog_target()
        self.auto_guide_watch_target = target.copy() if target is not None else None
        self.auto_guide_watch_last_pos = self.player.pos.copy()
        self.auto_guide_watch_last_delta = None
        self.auto_guide_watch_last_distance = None
        self.auto_guide_watch_time = 0.0
        self.auto_guide_watch_flip_count = 0
    def auto_guide_watchdog_target(self):
        if self.auto_guide_follow_target is not None:
            target = self.auto_guide_follow_target
            if self.auto_guide_follow_anchor is not None:
                return pygame.Vector2(self.auto_guide_follow_anchor)
            if hasattr(target, "pos"):
                return pygame.Vector2(target.pos)
        return self.player.walk_target
    def recover_auto_guide_stuck_movement(self):
        self.player.moving = False
        self.player.clear_walk_target()
        self.release_auto_guide_reservations()
        self.auto_guide_follow_target = None
        self.auto_guide_follow_anchor = None
        self.auto_guide_follow_timer = 0.0
        self.auto_guide_last_target = None
        self.auto_guide_last_rest_kind = "move"
        self.auto_guide_rest_timer = AUTO_GUIDE_STUCK_RECOVERY_SECONDS
        self.reset_auto_guide_watchdog()
        self.last_mouse_debug = "Auto Play recovered from stuck movement"
        self.last_mouse_debug_time = 2.0
    def update_auto_guide_watchdog(self, dt):
        target = self.auto_guide_watchdog_target()
        if not self.auto_guide_enabled or target is None:
            self.reset_auto_guide_watchdog()
            return False

        target = pygame.Vector2(target)
        target_changed = (
            self.auto_guide_watch_target is None
            or self.auto_guide_watch_target.distance_to(target) > 2.0
        )
        if target_changed:
            self.auto_guide_watch_target = target.copy()
            self.auto_guide_watch_last_pos = self.player.pos.copy()
            self.auto_guide_watch_last_delta = None
            self.auto_guide_watch_last_distance = self.player.pos.distance_to(target)
            self.auto_guide_watch_time = 0.0
            self.auto_guide_watch_flip_count = 0
            return False

        current_distance = self.player.pos.distance_to(target)
        previous_distance = self.auto_guide_watch_last_distance
        delta = self.player.pos - self.auto_guide_watch_last_pos
        moved = delta.length()
        if moved > 0.8 and self.auto_guide_watch_last_delta is not None:
            last_delta = self.auto_guide_watch_last_delta
            if last_delta.length_squared() > 0.64 and delta.normalize().dot(last_delta.normalize()) < -0.45:
                self.auto_guide_watch_flip_count += 1
        if moved > 0.8:
            self.auto_guide_watch_last_delta = delta.copy()

        improved = previous_distance is None or current_distance < previous_distance - AUTO_GUIDE_STUCK_DISTANCE_EPSILON
        if improved:
            self.auto_guide_watch_time = 0.0
            self.auto_guide_watch_flip_count = 0
        else:
            self.auto_guide_watch_time += dt

        self.auto_guide_watch_last_pos = self.player.pos.copy()
        self.auto_guide_watch_last_distance = current_distance
        stuck_by_flipping = (
            self.auto_guide_watch_time >= AUTO_GUIDE_STUCK_WINDOW_SECONDS
            and self.auto_guide_watch_flip_count >= AUTO_GUIDE_STUCK_FLIP_COUNT
        )
        stuck_by_timeout = self.auto_guide_watch_time >= AUTO_GUIDE_STUCK_HARD_LIMIT_SECONDS
        if stuck_by_flipping or stuck_by_timeout:
            self.recover_auto_guide_stuck_movement()
            return True
        return False
    def set_auto_guide_rest(self, kind):
        if kind == "collect":
            self.auto_guide_rest_timer = random.uniform(0.05, 0.18) if random.random() < 0.3 else random.uniform(0.28, 0.72)
        elif kind == "approach":
            self.auto_guide_rest_timer = random.uniform(0.05, 0.24)
        elif kind == "charge":
            self.auto_guide_rest_timer = random.uniform(0.35, 0.95)
        elif kind == "cast":
            self.auto_guide_rest_timer = random.uniform(0.55, 1.15)
        elif kind == "concentrate":
            self.auto_guide_rest_timer = random.uniform(0.75, 1.65)
        elif kind == "transit":
            self.auto_guide_rest_timer = random.uniform(1.0, 2.15)
        elif kind == "start":
            self.auto_guide_rest_timer = random.uniform(0.25, 0.75)
        else:
            self.auto_guide_rest_timer = random.uniform(AUTO_GUIDE_REST_MIN_SECONDS, AUTO_GUIDE_REST_MAX_SECONDS)
    def auto_guide_standoff_target(self, object_pos, distance=AUTO_GUIDE_INTERACTION_STANDOFF):
        object_pos = pygame.Vector2(object_pos)
        direction = self.player.pos - object_pos
        if direction.length_squared() < 0.001:
            seed = object_pos.x * 0.031 + object_pos.y * 0.047 + self.lumen_count
            direction = pygame.Vector2(math.cos(seed), math.sin(seed))
        return self.clamp_world_target(object_pos + direction.normalize() * distance)
    def begin_auto_guide_follow(self, moving_object, anchor=None, seconds=None):
        if not self.auto_guide_enabled:
            return
        self.auto_guide_follow_target = moving_object
        self.auto_guide_follow_anchor = pygame.Vector2(anchor) if anchor is not None else None
        self.auto_guide_follow_timer = seconds if seconds is not None else random.uniform(*AUTO_GUIDE_FOLLOW_SECONDS_RANGE)
        self.auto_guide_follow_step = random.uniform(*AUTO_GUIDE_FOLLOW_STEP_RANGE)
    def clear_auto_guide_pebble_reservation(self):
        self.auto_guide_pebble_id = None
        self.auto_guide_pebble_waypoint_group = None
        self.auto_guide_pebble_waypoint_id = None
    def clear_auto_guide_fern_reservation(self):
        self.auto_guide_fern_id = None
        self.auto_guide_fern_leaf = None
        self.auto_guide_fern_slot = None
    def clear_auto_guide_stone_reservation(self):
        self.auto_guide_stone_group = None
        self.auto_guide_stone_id = None
        self.auto_guide_stone_kind = None
    def release_auto_guide_reservations(self):
        self.release_auto_guide_pebble_reservation()
        self.release_auto_guide_fern_reservation()
        self.release_auto_guide_stone_reservation()
    def release_auto_guide_pebble_reservation(self):
        pebble = self.get_pebble_by_id(self.auto_guide_pebble_id)
        waypoint = self.get_waypoint(self.auto_guide_pebble_waypoint_group, self.auto_guide_pebble_waypoint_id)
        if pebble is not None and pebble.claimed_by == -1 and not pebble.held and not pebble.moving and not pebble.placed:
            pebble.claimed_by = None
        if waypoint is not None and waypoint.claimed_by == -1 and waypoint.occupied_by is None:
            waypoint.claimed_by = None
        self.clear_auto_guide_pebble_reservation()
    def release_auto_guide_fern_reservation(self):
        fern = self.get_fern_by_id(self.auto_guide_fern_id)
        if fern is not None and fern.claimed_by == -1 and not fern.held and not fern.moving and not fern.placed:
            fern.claimed_by = None
            fern.target_leaf = None
            fern.target_slot = None
        self.clear_auto_guide_fern_reservation()
    def release_auto_guide_stone_reservation(self):
        waypoint = self.get_waypoint(self.auto_guide_stone_group, self.auto_guide_stone_id)
        if waypoint is not None and waypoint.claimed_by == -1:
            waypoint.claimed_by = None
        self.clear_auto_guide_stone_reservation()
    def try_claim_pebble(self, pebble, claimant):
        if pebble is None or pebble.placed or pebble.moving or pebble.held or pebble.claimed_by is not None:
            return False
        pebble.claimed_by = claimant
        return pebble.claimed_by == claimant
    def try_claim_waypoint(self, waypoint, claimant):
        if waypoint is None or waypoint.occupied_by is not None or waypoint.claimed_by is not None:
            return False
        waypoint.claimed_by = claimant
        return waypoint.claimed_by == claimant
    def try_claim_stone_waypoint(self, waypoint, claimant, kind):
        if waypoint is None or waypoint.occupied_by is None or waypoint.claimed_by is not None:
            return False
        if kind == "charge" and waypoint.charge >= 1.0:
            return False
        if kind == "cast" and waypoint.charge < 1.0:
            return False
        if kind == "regen" and waypoint.regen_offsets:
            return False
        waypoint.claimed_by = claimant
        return waypoint.claimed_by == claimant
    def fern_slot_claimed(self, leaf_index, slot_index):
        return any(
            fern.target_leaf == leaf_index
            and fern.target_slot == slot_index
            and fern.claimed_by is not None
            for fern in self.fern_fronds
        )
    def try_claim_fern_task(self, fern, leaf_index, slot_index, claimant):
        if fern is None or fern.placed or fern.moving or fern.held or fern.claimed_by is not None:
            return False
        if leaf_index is None or slot_index is None or leaf_index < 0 or leaf_index >= len(self.leaf_decals):
            return False
        leaf = self.leaf_decals[leaf_index]
        if not leaf.fern_slots or slot_index < 0 or slot_index >= len(leaf.fern_slots) or leaf.fern_slots[slot_index] is not None:
            return False
        if self.fern_slot_claimed(leaf_index, slot_index):
            return False
        fern.claimed_by = claimant
        fern.target_leaf = leaf_index
        fern.target_slot = slot_index
        if fern.claimed_by == claimant and fern.target_leaf == leaf_index and fern.target_slot == slot_index:
            return True
        if fern.claimed_by == claimant:
            fern.claimed_by = None
            fern.target_leaf = None
            fern.target_slot = None
        return False
    def auto_guide_reserved_pebble_task(self, group):
        if self.auto_guide_pebble_waypoint_group != group:
            self.release_auto_guide_pebble_reservation()
            return None, None
        pebble = self.get_pebble_by_id(self.auto_guide_pebble_id)
        waypoint = self.get_waypoint(group, self.auto_guide_pebble_waypoint_id)
        valid = (
            pebble is not None
            and waypoint is not None
            and not pebble.placed
            and not pebble.moving
            and not pebble.held
            and waypoint.occupied_by is None
            and pebble.claimed_by == -1
            and waypoint.claimed_by == -1
        )
        if not valid:
            self.release_auto_guide_pebble_reservation()
            return None, None
        return pebble, waypoint
    def reserve_auto_guide_pebble_task(self, group):
        pebble, waypoint = self.auto_guide_reserved_pebble_task(group)
        if pebble is not None and waypoint is not None:
            return pebble, waypoint
        waypoints = self.companion_waypoints if group == "companion" else self.pebble_waypoints
        open_waypoints = [
            (index, waypoint)
            for index, waypoint in enumerate(waypoints)
            if waypoint.occupied_by is None and waypoint.claimed_by is None
        ]
        open_pebbles = [
            pebble
            for pebble in self.concentrate_pebbles
            if not pebble.placed and not pebble.moving and not pebble.held and pebble.claimed_by is None
        ]
        if not open_waypoints or not open_pebbles:
            return None, None
        pebble = min(open_pebbles, key=lambda item: (self.player.pos.distance_to(item.pos), item.id))
        waypoint_index, waypoint = min(open_waypoints, key=lambda item: (pebble.pos.distance_to(item[1].pos), item[0]))
        if not self.try_claim_pebble(pebble, -1):
            return None, None
        if not self.try_claim_waypoint(waypoint, -1):
            pebble.claimed_by = None
            return None, None
        self.auto_guide_pebble_id = pebble.id
        self.auto_guide_pebble_waypoint_group = group
        self.auto_guide_pebble_waypoint_id = waypoint_index
        return pebble, waypoint
    def auto_guide_reserved_fern_task(self):
        fern = self.get_fern_by_id(self.auto_guide_fern_id)
        valid = (
            fern is not None
            and not fern.placed
            and not fern.moving
            and not fern.held
            and fern.claimed_by == -1
            and fern.target_leaf == self.auto_guide_fern_leaf
            and fern.target_slot == self.auto_guide_fern_slot
        )
        if not valid:
            self.release_auto_guide_fern_reservation()
            return None, None
        if self.auto_guide_fern_leaf is None or self.auto_guide_fern_slot is None:
            self.release_auto_guide_fern_reservation()
            return None, None
        if self.auto_guide_fern_leaf >= len(self.leaf_decals):
            self.release_auto_guide_fern_reservation()
            return None, None
        leaf = self.leaf_decals[self.auto_guide_fern_leaf]
        if not leaf.fern_slots or self.auto_guide_fern_slot >= len(leaf.fern_slots) or leaf.fern_slots[self.auto_guide_fern_slot] is not None:
            self.release_auto_guide_fern_reservation()
            return None, None
        return fern, (self.auto_guide_fern_leaf, self.auto_guide_fern_slot, pygame.Vector2(leaf.x, leaf.z))
    def reserve_auto_guide_fern_task(self):
        fern, slot = self.auto_guide_reserved_fern_task()
        if fern is not None and slot is not None:
            return fern, slot
        open_slots = []
        for leaf_index, leaf in enumerate(self.leaf_decals):
            for slot_index, fern_id in enumerate(leaf.fern_slots or []):
                if fern_id is not None:
                    continue
                claimed = any(
                    fern.target_leaf == leaf_index
                    and fern.target_slot == slot_index
                    and fern.claimed_by is not None
                    for fern in self.fern_fronds
                )
                if not claimed:
                    open_slots.append((leaf_index, slot_index, pygame.Vector2(leaf.x, leaf.z)))
        open_ferns = [
            fern
            for fern in self.fern_fronds
            if not fern.placed and not fern.moving and not fern.held and fern.claimed_by is None
        ]
        if not open_slots or not open_ferns:
            return None, None
        fern = min(open_ferns, key=lambda item: (self.player.pos.distance_to(item.pos), item.id))
        leaf_index, slot_index, slot_pos = min(open_slots, key=lambda item: (fern.pos.distance_to(item[2]), item[0], item[1]))
        if not self.try_claim_fern_task(fern, leaf_index, slot_index, -1):
            return None, None
        self.auto_guide_fern_id = fern.id
        self.auto_guide_fern_leaf = leaf_index
        self.auto_guide_fern_slot = slot_index
        return fern, (leaf_index, slot_index, slot_pos)
    def auto_guide_reserved_stone_task(self, kind):
        if self.auto_guide_stone_kind != kind:
            self.release_auto_guide_stone_reservation()
            return None, None, None
        waypoint = self.get_waypoint(self.auto_guide_stone_group, self.auto_guide_stone_id)
        valid = waypoint is not None and waypoint.occupied_by is not None and waypoint.claimed_by == -1
        if kind == "charge":
            valid = valid and waypoint.charge < 1.0
        elif kind == "cast":
            valid = valid and waypoint.charge >= 1.0
        else:
            valid = False
        if not valid:
            self.release_auto_guide_stone_reservation()
            return None, None, None
        return self.auto_guide_stone_group, self.auto_guide_stone_id, waypoint
    def reserve_auto_guide_stone_task(self, kind):
        group, index, waypoint = self.auto_guide_reserved_stone_task(kind)
        if waypoint is not None:
            return group, index, waypoint
        if kind == "charge":
            candidates = self.chargeable_stone_waypoints()
        elif kind == "cast":
            candidates = self.charged_stone_waypoints()
        else:
            return None, None, None
        open_stones = [
            (group, index, waypoint)
            for group, index, waypoint in candidates
            if waypoint.claimed_by is None
        ]
        if not open_stones:
            return None, None, None
        group, index, waypoint = min(open_stones, key=lambda item: (self.player.pos.distance_to(item[2].pos), 0 if item[0] == "primary" else 1, item[1]))
        if not self.try_claim_stone_waypoint(waypoint, -1, kind):
            return None, None, None
        self.auto_guide_stone_group = group
        self.auto_guide_stone_id = index
        self.auto_guide_stone_kind = kind
        return group, index, waypoint
    def update_auto_guide_follow(self, dt):
        if self.auto_guide_follow_timer <= 0 or self.auto_guide_follow_target is None:
            return False
        target = self.auto_guide_follow_target
        if not getattr(target, "moving", False):
            self.auto_guide_follow_target = None
            self.auto_guide_follow_anchor = None
            self.auto_guide_follow_timer = 0.0
            return False
        self.auto_guide_follow_timer = max(0.0, self.auto_guide_follow_timer - dt)
        if self.auto_guide_follow_timer <= 0:
            self.auto_guide_follow_target = None
            self.auto_guide_follow_anchor = None
            self.player.clear_walk_target()
            return False
        anchor = self.auto_guide_follow_anchor if self.auto_guide_follow_anchor is not None else getattr(target, "pos", self.player.pos)
        direction = anchor - self.player.pos
        if direction.length_squared() > 1:
            self.player.set_walk_target(self.clamp_world_target(self.player.pos + direction.normalize() * self.auto_guide_follow_step))
        self.player.request_channel()
        return True
    def update_auto_guide_prompt(self, dt):
        if self.auto_guide_enabled:
            return
        if self.auto_guide_prompt_time > 0:
            self.update_auto_guide_prompt_countdown(dt)
            return
        if self.auto_guide_prompt_shown or not self.intro_complete or not self.controls_enabled:
            return
        if self.player.moving or self.player.walk_target is not None:
            self.auto_guide_idle_time = 0.0
            return
        self.auto_guide_idle_time += dt
        if self.auto_guide_idle_time >= AUTO_GUIDE_IDLE_SECONDS:
            self.auto_guide_prompt_shown = True
            self.auto_guide_prompt_time = AUTO_GUIDE_PROMPT_SECONDS
            self.auto_guide_prompt_countdown_active = True
    def update_auto_guide(self, dt, keys):
        if self.options_open:
            self.update_auto_guide_prompt(dt)
            return
        if not self.auto_guide_enabled and self.movement_keys_pressed(keys):
            self.note_manual_activity(stop_auto=False)
            return
        self.update_auto_guide_prompt(dt)
        if not self.auto_guide_enabled:
            return
        if self.movement_keys_pressed(keys):
            self.note_manual_activity()
            return
        if not self.controls_enabled or self.options_open:
            return
        if self.update_auto_guide_follow(dt):
            self.update_auto_guide_watchdog(dt)
            return
        if self.update_auto_guide_watchdog(dt):
            return
        if self.player.walk_target is not None:
            return
        if self.auto_guide_last_target is not None and self.player.pos.distance_to(self.auto_guide_last_target) < 74:
            self.auto_guide_last_target = None
            self.set_auto_guide_rest(self.auto_guide_last_rest_kind)
            return
        if self.auto_guide_rest_timer > 0:
            self.auto_guide_rest_timer = max(0.0, self.auto_guide_rest_timer - dt)
            return
        if not self.auto_guide_choose_action():
            self.auto_guide_rest_timer = AUTO_GUIDE_NO_ACTION_RETRY_SECONDS
    def auto_guide_choose_action(self):
        if self.phase == "explore":
            if self.lumen_count < REQUIRED_LUMEN:
                lumens = [lumen for lumen in self.lumens if not lumen.collected]
                if lumens:
                    lumen = min(lumens, key=lambda item: item.distance_to(self.player.pos.x, self.player.pos.y))
                    return self.auto_guide_move_to(pygame.Vector2(lumen.x, lumen.z), "collect")
                return False
            if self.player.pos.distance_to(self.spawn) > MYCELIAL_ACTIVATION_RADIUS * 0.55:
                return self.auto_guide_move_to(self.spawn, "approach")
            return False

        if self.phase == "feed":
            leaves = [
                leaf
                for leaf in self.leaf_decals
                if leaf.feed_progress < 1.0
            ]
            if leaves:
                leaf = min(leaves, key=lambda item: self.player.pos.distance_to(pygame.Vector2(item.x, item.z)))
                return self.auto_guide_move_to(pygame.Vector2(leaf.x, leaf.z), "approach")
            return False

        if self.phase == "post_feed":
            if not self.channel_cover_leaves_ready:
                if self.nearest_channel_cover_leaf:
                    leaf = self.nearest_channel_cover_leaf
                    self.start_channel_cover_leaf_move(leaf)
                    self.begin_auto_guide_follow(leaf, leaf.target)
                    self.set_auto_guide_rest("concentrate")
                    return True
                else:
                    return self.auto_guide_move_to(self.auto_guide_standoff_target(self.concentrate_rock.pos), "approach")
            if not self.concentrate_rock.lifted:
                if self.concentrate_rock_in_range:
                    pebble = self.start_outlet_rock_as_pebble()
                    waypoint = self.resolve_pebble_target_waypoint(pebble) if pebble else None
                    if pebble:
                        self.begin_auto_guide_follow(pebble, waypoint.pos if waypoint else pebble.pos)
                    self.set_auto_guide_rest("concentrate")
                    return True
                else:
                    return self.auto_guide_move_to(self.auto_guide_standoff_target(self.concentrate_rock.pos), "approach")
            return self.auto_guide_concentrate_nearest_pebble("primary")

        if self.phase == "transit":
            if not self.npc_mushrooms and not self.transit_used:
                self.start_transit()
                self.set_auto_guide_rest("transit")
                return True
            if self.companion_pebble_beat_active:
                return self.auto_guide_concentrate_nearest_pebble("companion")
            if self.fern_beat_active:
                return self.auto_guide_concentrate_nearest_fern()
            if self.training_beat_active:
                group, index, waypoint = self.reserve_auto_guide_stone_task("cast")
                if waypoint is None:
                    return False
                if self.player.pos.distance_to(waypoint.pos) <= SPELL_CHARGE_RADIUS:
                    if not self.player_cast_training_spell((group, index)):
                        self.release_auto_guide_stone_reservation()
                        return False
                    self.set_auto_guide_rest("cast")
                    return True
                return self.auto_guide_move_to(self.auto_guide_standoff_target(waypoint.pos, 72), "cast")
            if self.collect_ferns_03_complete and not self.charge_stones_04_complete:
                _, _, waypoint = self.reserve_auto_guide_stone_task("charge")
                if waypoint is None:
                    return False
                return self.auto_guide_move_to(self.auto_guide_standoff_target(waypoint.pos, 72), "charge")
        return False
    def auto_guide_concentrate_nearest_pebble(self, group):
        pebble, waypoint = self.reserve_auto_guide_pebble_task(group)
        if pebble is None or waypoint is None:
            return False
        if self.player.pos.distance_to(pebble.pos) <= CONCENTRATE_PEBBLE_RANGE:
            if not self.start_pebble_auto_move(pebble, group, self.auto_guide_pebble_waypoint_id):
                self.release_auto_guide_pebble_reservation()
                return False
            self.begin_auto_guide_follow(pebble, waypoint.pos if waypoint else pebble.pos)
            self.set_auto_guide_rest("concentrate")
            return True
        return self.auto_guide_move_to(self.auto_guide_standoff_target(pebble.pos), "approach")
    def auto_guide_concentrate_nearest_fern(self):
        fern, slot = self.reserve_auto_guide_fern_task()
        if fern is None or slot is None:
            return False
        if self.player.pos.distance_to(fern.pos) <= CONCENTRATE_PEBBLE_RANGE:
            if not self.start_player_fern_move(fern, slot[:2]):
                self.release_auto_guide_fern_reservation()
                return False
            leaf_index, slot_index, slot_pos = slot
            slot_offset = pygame.Vector2(-34, -16) if slot_index == 0 else pygame.Vector2(34, 18)
            anchor = slot_pos + slot_offset
            self.begin_auto_guide_follow(fern, anchor if anchor is not None else fern.pos)
            self.set_auto_guide_rest("concentrate")
            return True
        return self.auto_guide_move_to(self.auto_guide_standoff_target(fern.pos), "approach")
    def auto_guide_move_to(self, target, rest_kind="move"):
        target = self.clamp_world_target(target)
        if self.transit_available and self.player.pos.distance_to(target) > NPC_TRANSIT_DISTANCE:
            self.start_transit(target)
            self.set_auto_guide_rest("transit")
            return True
        self.player.set_walk_target(target, eased=True)
        self.reset_auto_guide_watchdog()
        self.auto_guide_last_target = target.copy()
        self.auto_guide_last_rest_kind = rest_kind
        return True
    def auto_guide_debug_state(self):
        if not self.auto_guide_enabled:
            return "off"
        speed = self.auto_guide_speed_mode.lower()
        if self.auto_guide_stone_kind:
            return f"{speed} {self.auto_guide_stone_kind}:{self.auto_guide_stone_group}/{self.auto_guide_stone_id}"
        if self.auto_guide_pebble_id is not None:
            return f"{speed} pebble:{self.auto_guide_pebble_id}->{self.auto_guide_pebble_waypoint_group}/{self.auto_guide_pebble_waypoint_id}"
        if self.auto_guide_fern_id is not None:
            return f"{speed} fern:{self.auto_guide_fern_id}->{self.auto_guide_fern_leaf}/{self.auto_guide_fern_slot}"
        if self.auto_guide_follow_target is not None:
            return f"{speed} follow"
        if self.auto_guide_rest_timer > 0:
            return f"{speed} rest:{self.auto_guide_last_rest_kind} {self.auto_guide_rest_timer:.1f}s"
        if self.auto_guide_last_target is not None:
            return f"{speed} move:{self.auto_guide_last_rest_kind}"
        return f"{speed} idle"
