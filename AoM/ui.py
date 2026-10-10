import pygame

from config import *
from entities import *
from game_backed import GameBackedManager
from game_platform import WEB_BUILD, browser_window, reload_with_framebuffer
from utils import *
from version_info import about_lines


class UIManager(GameBackedManager):
    @property
    def render_profile(self):
        return {
            "name": self.render_profile_name,
            "disable_darkness": not self.darkness_overlay_enabled,
            "fast_scale": not self.smooth_scaling_enabled,
            "cache_world_images": True,
            "quantize_world_images": True,
        }
    def cycle_render_profile(self, direction=1):
        current = self.visual_quality if self.visual_quality in PRESET_ORDER else "Mobile/Browser"
        index = (PRESET_ORDER.index(current) + direction) % len(PRESET_ORDER)
        self.apply_visual_quality(PRESET_ORDER[index])
    @property
    def render_profile_name(self):
        suffix = "fast" if not self.smooth_scaling_enabled else "smooth"
        darkness = "dark" if self.darkness_overlay_enabled else "bright"
        return f"{self.visual_quality.lower()} {darkness} {suffix}"
    def apply_visual_quality(self, quality):
        self.visual_quality = quality
        preset = PRESETS[quality]
        self.browser_fps_cap = effective_fps(preset["fps"])
        self.darkness_overlay_enabled = preset["darkness"]
        self.smooth_scaling_enabled = preset["smooth_scaling"]
        self.sprites.set_style(preset["sprite_style"])
        if WEB_BUILD:
            framebuffer_key = preset.get("framebuffer")
            if framebuffer_key != self.framebuffer_key:
                self.request_confirmation("framebuffer_reload", framebuffer_key)
            else:
                self.framebuffer_warning = ""
        self.world_image_cache.clear()
        self.sprite_shadow_cache.clear()
        self.background_cache.clear()
    def sync_visual_quality(self):
        for quality, preset in PRESETS.items():
            framebuffer_matches = True
            if WEB_BUILD:
                framebuffer_matches = self.framebuffer_key == preset["framebuffer"]
            if (
                self.browser_fps_cap == effective_fps(preset["fps"])
                and self.darkness_overlay_enabled == preset["darkness"]
                and self.smooth_scaling_enabled == preset["smooth_scaling"]
                and self.sprites.sprite_style == preset["sprite_style"]
                and framebuffer_matches
            ):
                self.visual_quality = quality
                return
        self.visual_quality = "Custom"
    def toggle_options(self):
        self.options_open = not self.options_open
        if self.options_open:
            self.options_selected = self.valid_option_index(self.options_selected)
    def options_rows(self):
        if self.title_screen:
            return TITLE_OPTIONS_ROWS
        return GAME_OPTIONS_ROWS
    def is_section_option(self, label):
        return label in OPTION_SECTION_ROWS
    def is_selectable_option(self, label):
        return not self.is_section_option(label)
    def selectable_option_indices(self):
        return [index for index, label in enumerate(self.options_rows()) if self.is_selectable_option(label)]
    def valid_option_index(self, preferred=0):
        indices = self.selectable_option_indices()
        if not indices:
            return 0
        if preferred in indices:
            return preferred
        return min(indices, key=lambda index: abs(index - preferred))
    def move_option_selection(self, direction):
        indices = self.selectable_option_indices()
        if not indices:
            self.options_selected = 0
            return
        if self.options_selected not in indices:
            self.options_selected = indices[0]
            return
        current = indices.index(self.options_selected)
        self.options_selected = indices[(current + direction) % len(indices)]
    def handle_options_key(self, key):
        rows = self.options_rows()
        self.options_selected = self.valid_option_index(self.options_selected)
        if key == pygame.K_ESCAPE:
            self.options_open = False
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.is_action_option(rows[self.options_selected]):
                self.change_option(self.options_selected, 0)
            else:
                self.options_open = False
        elif key in (pygame.K_w, pygame.K_UP):
            self.move_option_selection(-1)
        elif key in (pygame.K_s, pygame.K_DOWN):
            self.move_option_selection(1)
        elif key in (pygame.K_a, pygame.K_LEFT) and not self.is_action_option(rows[self.options_selected]):
            self.change_option(self.options_selected, -1)
        elif key in (pygame.K_d, pygame.K_RIGHT) and not self.is_action_option(rows[self.options_selected]):
            self.change_option(self.options_selected, 1)
    def is_action_option(self, label):
        return label in ("End Game", "Close", "About")
    def handle_title_key(self, key):
        if self.title_exiting:
            return True
        if key in (pygame.K_a, pygame.K_LEFT, pygame.K_w, pygame.K_UP):
            self.title_selected = (self.title_selected - 1) % 3
            return True
        if key in (pygame.K_d, pygame.K_RIGHT, pygame.K_s, pygame.K_DOWN):
            self.title_selected = (self.title_selected + 1) % 3
            return True
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            self.activate_title_selection()
            return True
        if key == pygame.K_ESCAPE:
            self.title_selected = 2
            self.request_confirmation("exit")
            return True
        if key == pygame.K_o:
            self.title_selected = 1
            self.toggle_options()
            return True
        return True
    def change_option(self, index, direction=1):
        rows = self.options_rows()
        if index < 0 or index >= len(rows):
            return
        label = rows[index]
        if label == "Framebuffer:":
            self.change_framebuffer_option(direction)
        elif label == "Auto Play":
            modes = AUTO_GUIDE_SPEED_OPTIONS
            current = self.auto_guide_speed_mode if self.auto_guide_speed_mode in modes else "Off"
            step = 1 if direction >= 0 else -1
            next_mode = modes[(modes.index(current) + step) % len(modes)]
            if next_mode == "Off":
                self.stop_auto_guide()
            else:
                self.start_auto_guide(next_mode)
        elif label == "Sprite Style":
            self.sprites.cycle_style(direction)
            self.sync_visual_quality()
        elif label == "Preset":
            self.cycle_render_profile(direction)
        elif label == "Darkness Overlay":
            self.darkness_overlay_enabled = not self.darkness_overlay_enabled
            self.sync_visual_quality()
        elif label == "Smooth Scaling":
            self.smooth_scaling_enabled = not self.smooth_scaling_enabled
            self.sync_visual_quality()
            self.world_image_cache.clear()
            self.background_cache.clear()
        elif label == "FPS Cap" and not WEB_BUILD:
            current = self.browser_fps_cap if self.browser_fps_cap in BROWSER_FPS_OPTIONS else BROWSER_FPS
            next_index = (BROWSER_FPS_OPTIONS.index(current) + direction) % len(BROWSER_FPS_OPTIONS)
            self.browser_fps_cap = BROWSER_FPS_OPTIONS[next_index]
            self.sync_visual_quality()
        elif label == "Debug Overlay":
            self.debug_overlay = not self.debug_overlay
        elif label == "About":
            self.open_about()
        elif label == "Auto Win":
            self.auto_win_enabled = not self.auto_win_enabled
            if self.auto_win_enabled:
                self.force_win_current_encounter()
        elif label == "Time Speed":
            self.cycle_time_scale(direction)
        elif label == "End Game":
            self.request_confirmation("end_game")
        elif label == "Close":
            self.options_open = False
    def change_framebuffer_option(self, direction=1):
        if not WEB_BUILD:
            return
        next_index = (FRAMEBUFFER_ORDER.index(self.framebuffer_key) + direction) % len(FRAMEBUFFER_ORDER)
        next_key = FRAMEBUFFER_ORDER[next_index]
        self.request_confirmation("framebuffer_reload", next_key)
    def apply_framebuffer_reload(self, key):
        if reload_with_framebuffer(key):
            return
        self.framebuffer_warning = "Framebuffer reload failed. Try refreshing with ?fb=" + key
    def option_value(self, label):
        if label == "Framebuffer:":
            return FRAMEBUFFER_OPTIONS[self.framebuffer_key][0]
        if label == "Auto Play":
            return self.auto_guide_speed_mode if self.auto_guide_enabled else "Off"
        if label == "Sprite Style":
            return self.sprites.sprite_style
        if label == "Preset":
            return self.visual_quality
        if label == "Darkness Overlay":
            return "On" if self.darkness_overlay_enabled else "Off"
        if label == "Smooth Scaling":
            return "On" if self.smooth_scaling_enabled else "Off"
        if label == "FPS Cap":
            return str(effective_fps(self.browser_fps_cap))
        if label == "Debug Overlay":
            return "On" if self.debug_overlay else "Off"
        if label == "Auto Win":
            return "On" if self.auto_win_enabled else "Off"
        if label == "Time Speed":
            return f"{self.time_scale}x"
        return ""
    def option_display_value(self, label):
        value = self.option_value(label)
        if not value:
            return ""
        return f"< {value} >"
    def option_tooltip(self, label):
        hints = {
            "Preset": "Apply a full performance and graphics configuration.",
            "Auto Play": "Choose automation speed for helpful player tasks.",
            "Debug Overlay": "Show frame timing and render diagnostics.",
            "Auto Win": "Force every encounter to resolve as a win (testing affordance).",
            "Time Speed": "Advance simulation time faster for testing (1x/2x/4x/8x; F9 cycles).",
            "Sprite Style": "Choose a mushroom species or visual style for sprites.",
            "Darkness Overlay": "Toggle the cave darkness lighting layer.",
            "Smooth Scaling": "Use smoother scaling for browser and framebuffer output.",
            "FPS Cap": "Set the frame-rate target.",
            "End Game": "Return to the title screen after confirmation.",
            "About": "Show build hash/time, Python, and package versions.",
            "Framebuffer:": "Choose browser resolution. Changes require reload.",
            "Close": "Close this menu.",
            "PRESET": "Preset options.",
            "GRAPHICS": "Graphics and performance options.",
            "GAME": "Gameplay automation options.",
            "TOOLS": "Diagnostics and developer tools.",
            "SYSTEM": "Session controls.",
            "": "",
        }
        return hints.get(label, "")
    def handle_options_click(self, pos, exact=False):
        positions = [(round(pos[0]), round(pos[1]))] if exact else self.mouse_position_candidates(pos)
        handled = any(self.handle_options_click_at(candidate) for candidate in positions)
        if not handled:
            self.last_mouse_debug = f"click {pos} -> {positions} btn {self.options_button_rect}"
            self.last_mouse_debug_time = 1.8
        return handled
    def handle_options_click_at(self, pos):
        if self.options_button_rect.inflate(4, 4).collidepoint(pos):
            self.note_manual_activity(stop_auto=False)
            self.toggle_options()
            return True
        if self.options_open:
            for index, rect in enumerate(self.options_row_rects):
                if rect.collidepoint(pos):
                    rows = self.options_rows()
                    if index >= len(rows) or not self.is_selectable_option(rows[index]):
                        return True
                    self.options_selected = index
                    self.change_option(index, 1)
                    return True
            self.options_open = False
            return True
        return False
    def open_about(self):
        self.about_lines = about_lines()
        self.about_open = True
        self.options_open = False
        self._publish_about_debug(True)
    def close_about(self):
        if not self.about_open:
            return False
        self.about_open = False
        self._publish_about_debug(False)
        return True
    def _publish_about_debug(self, opened):
        """Expose About state to the browser for the smoke test (web only)."""
        if not WEB_BUILD:
            return
        try:
            window = browser_window()
            if window is None:
                return
            window.__AOM_ABOUT_OPEN__ = bool(opened)
            build_hash = next(
                (value for label, value in self.about_lines if label == "Build"), ""
            )
            window.__AOM_BUILD_HASH__ = str(build_hash)
        except Exception:
            pass
    def handle_about_click(self, pos):
        if not self.about_open:
            return False
        self.close_about()
        return True
    def request_confirmation(self, action, payload=None):
        self.confirm_action = action
        self.confirm_display_action = action
        self.confirm_payload = payload
        self.confirm_selected = 1
    def cancel_confirmation(self):
        action = self.confirm_action
        self.confirm_action = None
        self.confirm_payload = None
        if action == "build":
            # Cancelling a build confirm abandons placement (no spend) and
            # returns the player to the sheet (Section 9.1.4).
            self.cancel_placement()
            self.open_build_menu()
    def confirm_current_action(self):
        action = self.confirm_action
        payload = self.confirm_payload
        self.confirm_action = None
        self.confirm_display_action = action
        self.confirm_payload = None
        if action == "end_game":
            self.start_end_game_transition()
        elif action == "exit":
            self.running = False
        elif action == "framebuffer_reload":
            self.apply_framebuffer_reload(payload or self.framebuffer_key)
        elif action == "build":
            payload = payload or {}
            building_id = payload.get("building_id")
            if building_id and not self.commit_build(building_id, payload.get("pos")):
                # Race / now-unaffordable: never silently spend or fail.
                self.open_build_menu()
    def start_end_game_transition(self):
        self.options_open = False
        self.end_game_fade_active = True
        self.end_game_fade_time = 0.0
    def finish_end_game_transition(self):
        self.reset()
        self.title_screen = True
        self.title_exiting = False
        self.title_transition_time = 0.0
        self.options_open = False
        self.end_game_fade_active = False
        self.end_game_fade_time = 0.0
    def handle_confirmation_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_n):
            self.cancel_confirmation()
            return True
        if key in (pygame.K_a, pygame.K_LEFT):
            self.confirm_selected = 0
            return True
        if key in (pygame.K_d, pygame.K_RIGHT):
            self.confirm_selected = 1
            return True
        if key == pygame.K_y:
            self.confirm_selected = 0
            self.confirm_current_action()
            return True
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.confirm_selected == 0:
                self.confirm_current_action()
            else:
                self.cancel_confirmation()
            return True
        return True
    def handle_confirmation_click(self, pos):
        if self.confirm_action is None:
            return False
        if self.confirm_yes_rect.collidepoint(pos):
            self.confirm_current_action()
            return True
        if self.confirm_no_rect.collidepoint(pos) or not self.confirm_rect.collidepoint(pos):
            self.cancel_confirmation()
            return True
        return True
    def start_game(self):
        self.title_exiting = True
        self.title_transition_time = min(self.title_transition_time, TITLE_OUT_TOTAL_FADE_SECONDS)
        self.options_open = False
        self.confirm_action = None
        self.confirm_payload = None
    def finish_start_game(self):
        self.title_screen = False
        self.title_exiting = False
        self.title_transition_time = TITLE_IN_TOTAL_FADE_SECONDS
        self.gameplay_fade = 0.0
        self.options_open = False
        self.confirm_action = None
        self.confirm_payload = None
    def activate_title_selection(self):
        if self.title_selected == 0:
            self.start_game()
        elif self.title_selected == 1:
            self.toggle_options()
        elif self.title_selected == 2:
            self.request_confirmation("exit")
    def handle_title_click(self, pos):
        if not self.title_screen or self.title_exiting:
            return False
        if self.title_start_rect.collidepoint(pos):
            self.title_selected = 0
            self.start_game()
            return True
        if self.title_options_rect.collidepoint(pos):
            self.title_selected = 1
            self.toggle_options()
            return True
        if self.title_exit_rect.collidepoint(pos):
            self.title_selected = 2
            self.request_confirmation("exit")
            return True
        return False
