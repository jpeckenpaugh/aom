import pygame

from config import *
from entities import *
from game_backed import GameBackedManager
from game_platform import browser_inner_size, browser_pointer_clicks
from utils import *


class InputHandler(GameBackedManager):
    def mouse_position_candidates(self, event_pos):
        candidates = []
        for pos in (event_pos, pygame.mouse.get_pos()):
            if pos is None:
                continue
            point = (round(pos[0]), round(pos[1]))
            if point not in candidates:
                candidates.append(point)
            for window_width, window_height in self.pointer_window_sizes():
                scaled = (
                    round(pos[0] * SCREEN_WIDTH / window_width),
                    round(pos[1] * SCREEN_HEIGHT / window_height),
                )
                if scaled not in candidates:
                    candidates.append(scaled)
        return candidates
    def pointer_window_sizes(self):
        sizes = []
        try:
            sizes.append(pygame.display.get_window_size())
        except (AttributeError, pygame.error):
            pass
        browser_size = browser_inner_size()
        if browser_size is not None:
            sizes.append(browser_size)
        unique = []
        for width, height in sizes:
            if width > 0 and height > 0 and (width != SCREEN_WIDTH or height != SCREEN_HEIGHT) and (width, height) not in unique:
                unique.append((width, height))
        return unique
    def browser_click_value(self, click, key, default=0):
        try:
            return getattr(click, key)
        except (AttributeError, TypeError):
            try:
                return click[key]
            except (KeyError, TypeError):
                return default
    def drain_browser_pointer_clicks(self, process=True):
        if not WEB_BUILD:
            return False
        clicks = browser_pointer_clicks()
        if clicks is None:
            return False

        handled = False
        while True:
            try:
                if int(getattr(clicks, "length", 0)) <= 0:
                    break
                click = clicks.shift()
            except (AttributeError, TypeError, ValueError):
                break
            if not process:
                continue
            pos = (
                int(self.browser_click_value(click, "x")),
                int(self.browser_click_value(click, "y")),
            )
            if self.handle_about_click(pos):
                handled = True
            elif self.handle_confirmation_click(pos):
                handled = True
            elif self.handle_item_drawer_click(pos):
                handled = True
            elif self.handle_options_click(pos, exact=True):
                handled = True
            elif self.handle_title_click(pos):
                handled = True
            elif self.handle_auto_guide_prompt_click(pos):
                handled = True
            elif self.cinematic_locked:
                self.note_manual_activity(stop_auto=False)
                self.skip_locked_cinematic()
                handled = True
            else:
                self.note_manual_activity()
                handled = self.handle_game_click(pos) or handled
        return handled
    def handle_game_click(self, pos):
        if self.options_open:
            return False
        if self.item_drawer_visible:
            return self.handle_item_drawer_click(pos)
        if self._handle_pagination_click(pos):
            return True
        screen_pos = pygame.Vector2(pos)
        world_pos = self.camera.unproject(screen_pos.x, screen_pos.y)
        if self.transit_targeting:
            if self.controls_enabled:
                self.transit_targeting = False
                self.transit_prompt_open = False
                self.player.clear_walk_target()
                self.start_transit(self.clamp_world_target(world_pos))
                return True
            return False
        if self.transit_prompt_open:
            if self.transit_button_rect.collidepoint(pos):
                self.transit_targeting = True
                self.transit_prompt_open = False
                self.player.clear_walk_target()
                return True
            self.transit_prompt_open = False
        if self.clicked_player(screen_pos):
            self.transit_prompt_open = True
            self.player.clear_walk_target()
            return True
        if self.handle_click_action(screen_pos):
            return True
        if self.handle_click_transit(world_pos):
            return True
        if self.controls_enabled:
            self.player.set_walk_target(self.clamp_world_target(world_pos))
            return True
        return False
    def clamp_world_target(self, world_pos):
        target = pygame.Vector2(world_pos)
        max_radius = CAVE_RADIUS - PLAYER_MARGIN
        if target.length() > max_radius:
            target.scale_to_length(max_radius)
        return target
    def clicked_world_target(self, screen_pos, world_pos, hit_radius=CLICK_ACTION_SCREEN_RADIUS):
        screen = self.camera.project(world_pos.x, world_pos.y)
        return screen.distance_to(screen_pos) <= hit_radius
    def clicked_player(self, screen_pos):
        if not self.transit_available or not self.controls_enabled:
            return False
        player_screen = self.camera.project(self.player.pos.x, self.player.pos.y, self.player.height + 36)
        hit_radius = max(38, round(58 * self.camera.zoom))
        return player_screen.distance_to(screen_pos) <= hit_radius
    def handle_click_action(self, screen_pos):
        if not self.concentrate_unlocked or self.concentrate_mode is not None:
            return False
        if self.nearest_channel_cover_leaf:
            candidates = [
                leaf
                for leaf in self.channel_cover_leaves
                if not leaf.placed
                and not leaf.moving
                and self.player.pos.distance_to(self.concentrate_rock.pos) <= CONCENTRATE_RANGE
                and self.clicked_world_target(screen_pos, leaf.pos)
            ]
            if candidates:
                leaf = min(candidates, key=lambda item: self.camera.project(item.pos.x, item.pos.y).distance_to(screen_pos))
                self.player.clear_walk_target()
                self.start_channel_cover_leaf_move(leaf)
                return True
        if self.concentrate_rock_in_range and self.clicked_world_target(screen_pos, self.concentrate_rock.pos):
            self.player.clear_walk_target()
            self.start_outlet_rock_as_pebble()
            return True
        pebble = self.clicked_targetable_pebble(screen_pos)
        if pebble:
            group = "companion" if self.companion_pebble_beat_active else "primary"
            self.player.clear_walk_target()
            self.start_pebble_auto_move(pebble, group)
            return True
        fern = self.clicked_targetable_fern(screen_pos)
        if fern:
            self.player.clear_walk_target()
            self.start_player_fern_move(fern)
            return True
        return False
    def clicked_targetable_pebble(self, screen_pos):
        if not (self.pebble_beat_active or self.companion_pebble_beat_active):
            return None
        candidates = [
            pebble
            for pebble in self.concentrate_pebbles
            if not pebble.placed
            and not pebble.moving
            and (pebble.claimed_by is None or pebble.claimed_by == -1)
            and self.player.pos.distance_to(pebble.pos) <= CONCENTRATE_PEBBLE_RANGE
            and self.clicked_world_target(screen_pos, pebble.pos)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: (self.camera.project(item.pos.x, item.pos.y).distance_to(screen_pos), item.id))
    def clicked_targetable_fern(self, screen_pos):
        if not self.fern_beat_active:
            return None
        candidates = [
            fern
            for fern in self.fern_fronds
            if not fern.placed
            and not fern.moving
            and not fern.held
            and (fern.claimed_by is None or fern.claimed_by == -1)
            and self.player.pos.distance_to(fern.pos) <= CONCENTRATE_PEBBLE_RANGE
            and self.clicked_world_target(screen_pos, fern.pos)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: (self.camera.project(item.pos.x, item.pos.y).distance_to(screen_pos), item.id))
    def handle_click_transit(self, world_pos):
        if not self.transit_available:
            return False
        if self.player.pos.distance_to(world_pos) < CLICK_TRANSIT_DISTANCE:
            return False
        self.player.clear_walk_target()
        self.start_transit(self.clamp_world_target(world_pos))
        return True
    def movement_keys_pressed(self, keys):
        return (
            keys[pygame.K_a]
            or keys[pygame.K_LEFT]
            or keys[pygame.K_d]
            or keys[pygame.K_RIGHT]
            or keys[pygame.K_w]
            or keys[pygame.K_UP]
            or keys[pygame.K_s]
            or keys[pygame.K_DOWN]
        )
    def handle_events(self):
        saw_mouse_event = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.about_open:
                    self.note_manual_activity(stop_auto=False)
                    self.close_about()
                elif self.confirm_action is not None:
                    self.handle_confirmation_key(event.key)
                elif self.item_drawer_visible and event.key == pygame.K_ESCAPE:
                    self.note_manual_activity(stop_auto=False)
                    self.close_item_drawer()
                elif self.options_open:
                    self.handle_options_key(event.key)
                elif self.handle_auto_guide_prompt_key(event.key):
                    pass
                elif self.title_screen:
                    self.handle_title_key(event.key)
                elif event.key == pygame.K_RETURN:
                    self.note_manual_activity(stop_auto=False)
                    self.toggle_options()
                elif event.key == pygame.K_ESCAPE:
                    self.note_manual_activity(stop_auto=False)
                    self.toggle_options()
                elif event.key == pygame.K_r:
                    self.note_manual_activity()
                    self.reset()
                elif event.key == pygame.K_F3:
                    self.note_manual_activity(stop_auto=False)
                    self.debug_overlay = not self.debug_overlay
                elif event.key == pygame.K_F4:
                    self.note_manual_activity(stop_auto=False)
                    self.cycle_render_profile()
                elif event.key == pygame.K_F10:
                    self.note_manual_activity(stop_auto=False)
                    self.force_win_current_encounter()
                elif event.key == pygame.K_F9:
                    self.note_manual_activity(stop_auto=False)
                    self.cycle_time_scale()
                elif event.key == pygame.K_c:
                    self.note_manual_activity()
                    self.cheat_advance_phase()
                elif event.key == pygame.K_SPACE and self.cinematic_locked:
                    self.note_manual_activity(stop_auto=False)
                    self.skip_locked_cinematic()
                elif event.key == pygame.K_t and self.phase == "transit_select":
                    self.note_manual_activity()
                    self.phase = "transit"
                elif event.key == pygame.K_t and self.phase == "transit":
                    self.note_manual_activity()
                    self.phase = "transit_select"
                elif self.phase == "transit_select" and event.key in (pygame.K_a, pygame.K_LEFT, pygame.K_w, pygame.K_UP):
                    self.note_manual_activity()
                    self.cycle_transit_destination(-1)
                elif self.phase == "transit_select" and event.key in (pygame.K_d, pygame.K_RIGHT, pygame.K_s, pygame.K_DOWN):
                    self.note_manual_activity()
                    self.cycle_transit_destination(1)
                elif self.concentrate_mode == "pebble_select" and event.key in (pygame.K_a, pygame.K_LEFT, pygame.K_w, pygame.K_UP):
                    self.note_manual_activity()
                    self.cycle_selected_waypoint(-1)
                elif self.concentrate_mode == "pebble_select" and event.key in (pygame.K_d, pygame.K_RIGHT, pygame.K_s, pygame.K_DOWN):
                    self.note_manual_activity()
                    self.cycle_selected_waypoint(1)
                elif event.key == pygame.K_SPACE and self.phase == "transit_select":
                    self.note_manual_activity()
                    self.start_transit()
                elif event.key == pygame.K_SPACE and self.training_beat_active:
                    self.note_manual_activity()
                    self.player_cast_training_spell()
                elif event.key == pygame.K_SPACE and self.controls_enabled:
                    self.note_manual_activity()
                    self.toggle_concentrate()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                saw_mouse_event = True
                if WEB_BUILD:
                    continue
                if self.handle_about_click(event.pos):
                    continue
                if self.handle_confirmation_click(event.pos):
                    continue
                if self.handle_item_drawer_click(event.pos):
                    continue
                if self.handle_options_click(event.pos):
                    continue
                if self.handle_title_click(event.pos):
                    continue
                if self.handle_auto_guide_prompt_click(event.pos):
                    continue
                self.note_manual_activity()
                if self.cinematic_locked:
                    self.skip_locked_cinematic()
                else:
                    self.handle_game_click(event.pos)
        self.drain_browser_pointer_clicks(process=WEB_BUILD or not saw_mouse_event)
    def _handle_pagination_click(self, pos):
        if self.inventory_page_anim_t > 0:
            return False
        for i, rect in enumerate(self.inventory_pagination_rects):
            if rect.collidepoint(pos) and i != self.inventory_page:
                self.inventory_page_target = i
                self.inventory_page_anim_t = 0.001
                return True
        return False
    def handle_item_drawer_click(self, pos):
        if self._handle_pagination_click(pos):
            return True
        if self.item_drawer_visible and self.item_drawer_close_rect.collidepoint(pos):
            self.close_item_drawer()
            return True
        if self.options_open or self.title_screen:
            return False
        for item_key, rect in self.resource_icon_rects.items():
            if rect.collidepoint(pos):
                self.open_item_drawer(item_key)
                return True
        if self.item_drawer_visible:
            return True
        return False
