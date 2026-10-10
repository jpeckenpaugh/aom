import math

import pygame

from config import *
from entities import *
from game_backed import GameBackedManager
from utils import *


def lumen_rotated_surface(src, time, phase_offset=0):
    base = (360 * math.sin(time * 0.12 + phase_offset) + 240 * math.sin(time * 0.07 + phase_offset * 1.7) + 160 * math.sin(time * 0.19 + phase_offset * 0.3))
    drift = 280 * math.sin(time * 0.17 + 0.5 + phase_offset)
    lope = 200 * math.sin(time * 0.43 + 2.1 + phase_offset * 0.7)
    shiver = 80 * math.sin(time * 1.7 + 0.8 + phase_offset * 1.3)
    angle = base + drift + lope + shiver

    rotated = pygame.transform.rotate(src, angle)
    w, h = src.get_size()
    bbox = int(math.ceil(math.hypot(w, h)))
    if rotated.get_size() != (bbox, bbox):
        canvas = pygame.Surface((bbox, bbox), pygame.SRCALPHA)
        canvas.blit(rotated, rotated.get_rect(center=(bbox // 2, bbox // 2)))
        return canvas
    return rotated


def lumen_swing_rotated(frames, time, phase_offset=0):
    if not frames:
        return None
    idx = lumen_timeline_sprite(time, phase_offset, len(frames))
    return lumen_rotated_surface(frames[idx], time, phase_offset)


class Renderer(GameBackedManager):
    def draw(self):
        time = self.ui_time if self.title_screen else self.world_time
        if self.title_screen:
            self.draw_title_screen(time)
            self.draw_options_ui()
            self.draw_confirmation_ui()
            self.draw_about_ui()
            pygame.display.flip()
            return

        self.screen.fill(BG)
        self.draw_cave_floor()

        story_beat = self.story_beat_locked
        drawables = []
        drawables.append((self.spawn.y, lambda: self.draw_mycelial_spawn(time)))
        if not story_beat:
            for lumen in self.lumens:
                if lumen.visible and self.world_visible(pygame.Vector2(lumen.x, lumen.z), 60):
                    lumen_sprites = self.lumen_spin_frames or self.lumen_front_frame
                    drawables.append((lumen.z, lambda lumen=lumen: lumen.draw(self.screen, self.camera, time, self.growth_state, self.visual_depth_scale(pygame.Vector2(lumen.x, lumen.z)), sprites=lumen_sprites)))
            for lumen in self.leaf_quest_lumens:
                if lumen.visible and lumen.delay <= 0 and self.world_visible(lumen.pos, 72):
                    drawables.append((lumen.pos.y, lambda lumen=lumen: self.draw_leaf_quest_lumen(lumen, time)))
            for npc in self.npc_mushrooms:
                if self.world_visible(npc.pos, 90):
                    drawables.append((npc.pos.y, lambda npc=npc: self.draw_npc_mushroom(npc, time)))
        drawables.append((self.player.pos.y, lambda: self.draw_player(time)))
        if not story_beat:
            for spell in self.elemental_spells:
                if self.world_visible(spell.pos, 90):
                    drawables.append((spell.pos.y, lambda spell=spell: self.draw_elemental_spell(spell, time)))

        self.debug_draw_count = len(drawables)
        for _, draw in sorted(drawables, key=lambda item: item[0]):
            draw()
        if not story_beat:
            self.draw_water_drop()

        if self.phase == "concentrate_unlock":
            self.draw_story_word("concentrate", time)
        if self.phase == "transit_unlock":
            self.draw_story_word("transit", time, TRANSIT_UNLOCK_SECONDS)

        self.draw_darkness_overlay(time)
        self.draw_transit_markers(time)
        self.draw_transit_click_ui()
        self.draw_top_stone_bar()
        self.draw_top_hud_dock()
        self.draw_item_drawer()
        self.draw_bottom_hud_dock()
        self.draw_guidance_word_overlay(time)
        self.draw_auto_guide_ui()
        self.draw_debug_overlay()
        self.draw_options_ui()
        self.draw_confirmation_ui()
        self.draw_about_ui()
        self.draw_gameplay_fade()
        self.draw_end_game_fade()
        pygame.display.flip()
    def draw_title_screen(self, time):
        background_alpha, title_alpha, menu_alpha = self.title_stage_alphas()
        previous_screen = self.screen
        self.screen.fill(BG)

        background_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.screen = background_layer
        self.draw_title_background(time)
        self.screen = previous_screen
        background_layer.set_alpha(round(255 * background_alpha))
        self.screen.blit(background_layer, (0, 0))

        title_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.screen = title_layer
        self.draw_title_logo(time)
        self.screen = previous_screen
        title_layer.set_alpha(round(255 * title_alpha))
        self.screen.blit(title_layer, (0, 0))

        menu_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.screen = menu_layer
        menu_y = round(SCREEN_HEIGHT * 0.85)
        gap = round(18 * (SCREEN_WIDTH / BASE_SCREEN_WIDTH))
        button_width = round(178 * (SCREEN_WIDTH / BASE_SCREEN_WIDTH))
        total_width = button_width * 3 + gap * 2
        start_x = (SCREEN_WIDTH - total_width) // 2
        self.title_start_rect = self.draw_title_button("Start", start_x, menu_y, button_width, primary=True, selected=self.title_selected == 0)
        self.title_options_rect = self.draw_title_button("Options", start_x + button_width + gap, menu_y, button_width, selected=self.title_selected == 1)
        self.title_exit_rect = self.draw_title_button("Exit", start_x + (button_width + gap) * 2, menu_y, button_width, selected=self.title_selected == 2)
        self.screen = previous_screen
        menu_layer.set_alpha(round(255 * menu_alpha))
        self.screen.blit(menu_layer, (0, 0))
    def title_stage_alphas(self):
        if self.title_exiting:
            t = max(0.0, min(TITLE_OUT_TOTAL_FADE_SECONDS, self.title_transition_time))
            bg_seconds = TITLE_OUT_BACKGROUND_FADE_SECONDS
            text_seconds = TITLE_OUT_TEXT_FADE_SECONDS
            menu_seconds = TITLE_OUT_MENU_FADE_SECONDS
        else:
            t = max(0.0, min(TITLE_IN_TOTAL_FADE_SECONDS, self.title_transition_time))
            bg_seconds = TITLE_IN_BACKGROUND_FADE_SECONDS
            text_seconds = TITLE_IN_TEXT_FADE_SECONDS
            menu_seconds = TITLE_IN_MENU_FADE_SECONDS
        background = smoothstep(min(1.0, t / bg_seconds))
        text_start = bg_seconds
        title_text = smoothstep(max(0.0, min(1.0, (t - text_start) / text_seconds)))
        menu_start = bg_seconds + text_seconds
        menu = smoothstep(max(0.0, min(1.0, (t - menu_start) / menu_seconds)))
        return background, title_text, menu
    def draw_title_logo(self, time):
        scale = SCREEN_HEIGHT / BASE_SCREEN_HEIGHT
        center_x = SCREEN_WIDTH // 2
        top_y = round(SCREEN_HEIGHT * 0.055)
        age_font = self.assets.get_font(max(64, round(128 * scale)), bold=True)
        of_font = self.assets.get_font(max(24, round(48 * scale)), italic=True)
        myth_font = self.assets.get_font(max(64, round(128 * scale)), bold=True)
        myth_big_font = self.assets.get_font(max(82, round(164 * scale)), bold=True)
        edition_font = self.assets.get_font(max(18, round(36 * scale)), bold=True)

        gold = (218, 194, 137)
        gold_hi = (250, 232, 174)
        deep_shadow = (3, 5, 7)

        age = self.assets.render_textured_title_text(age_font, "AGE", (round(18 * scale), 0))
        if age is None:
            age = age_font.render("AGE", True, gold_hi)
        age_edge = age_font.render("AGE", True, gold_hi)
        age_shadow = age_font.render("AGE", True, deep_shadow)
        age_rect = age.get_rect(center=(center_x, top_y + round(62 * scale)))
        self.screen.blit(age_shadow, age_rect.move(round(4 * scale), round(5 * scale)))
        for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.screen.blit(age_edge, age_rect.move(offset[0], offset[1]))
        self.screen.blit(age, age_rect)
        self.draw_title_stone_line(center_x, age_rect.bottom - round(8 * scale), age_rect.width - round(8 * scale), scale)

        of_text = self.assets.render_textured_title_text(of_font, "of", (round(190 * scale), round(18 * scale)))
        if of_text is None:
            of_text = of_font.render("of", True, gold)
        of_edge = of_font.render("of", True, gold)
        of_shadow = of_font.render("of", True, deep_shadow)
        of_rect = of_text.get_rect(center=(center_x, age_rect.bottom + round(32 * scale)))
        self.screen.blit(of_shadow, of_rect.move(round(2 * scale), round(3 * scale)))
        for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.screen.blit(of_edge, of_rect.move(offset[0], offset[1]))
        self.screen.blit(of_text, of_rect)

        word = "MYCOLOGY"
        pieces = []
        total_width = 0
        texture_offset = 0
        for index, char in enumerate(word):
            oversized = index in (0, len(word) - 1)
            font = myth_big_font if oversized else myth_font
            image = self.assets.render_textured_title_text(font, char, (texture_offset, round(42 * scale)))
            if image is None:
                image = font.render(char, True, gold_hi if oversized else gold)
            edge = font.render(char, True, gold_hi if oversized else gold)
            shadow = font.render(char, True, deep_shadow)
            pieces.append((image, edge, shadow, oversized))
            total_width += image.get_width() + round(1 * scale)
            texture_offset += image.get_width() + round(1 * scale)
        x = center_x - total_width // 2
        myth_center_y = of_rect.bottom + round(82 * scale)
        for image, edge, shadow, oversized in pieces:
            rect = image.get_rect()
            rect.midleft = (x, myth_center_y)
            self.screen.blit(shadow, rect.move(round(4 * scale), round(5 * scale)))
            for offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self.screen.blit(edge, rect.move(offset[0], offset[1]))
            self.screen.blit(image, rect)
            x += image.get_width() + round(1 * scale)

        bar_y = myth_center_y + round(max(piece[0].get_height() for piece in pieces) * 0.5) + round(18 * scale)
        self.draw_title_stone_line(center_x, bar_y, round(total_width * 0.94), scale)

        tagline = "BIOLUMINESCENT EDITION"
        pulse = 0.5 + 0.5 * math.sin(time * 2.8)
        color_lift = round(42 * pulse)
        tagline_color = (
            min(255, LUMEN_CORE[0] + color_lift),
            min(255, LUMEN_CORE[1] + color_lift),
            min(255, LUMEN_CORE[2] + color_lift),
        )
        tagline_image = edition_font.render(tagline, True, tagline_color)
        tagline_rect = tagline_image.get_rect(center=(center_x, bar_y + round(48 * scale)))
        wide_glow = make_radial_glow(round((560 + pulse * 120) * scale), MYCELIUM, round(42 + pulse * 48), 2.7)
        tight_glow = make_radial_glow(round((320 + pulse * 60) * scale), LUMEN_CORE, round(38 + pulse * 42), 1.9)
        self.screen.blit(wide_glow, wide_glow.get_rect(center=tagline_rect.center))
        self.screen.blit(tight_glow, tight_glow.get_rect(center=tagline_rect.center))
        for offset in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, 0), (1, 0), (0, -1), (0, 1)):
            aura = edition_font.render(tagline, True, MYCELIUM)
            aura.set_alpha(round(66 + pulse * 78))
            self.screen.blit(aura, tagline_rect.move(offset[0], offset[1]))
        self.screen.blit(tagline_image, tagline_rect)
    def draw_title_stone_line(self, center_x, y, width, scale):
        top_height = max(3, round(6 * scale))
        shadow_height = max(2, round(4 * scale))
        bar = self.assets.make_stone_bar(max(1, int(width)), top_height, shadow_height)
        if bar is None:
            pygame.draw.line(
                self.screen,
                (92, 70, 38),
                (center_x - width // 2, y),
                (center_x + width // 2, y),
                max(1, round(2 * scale)),
            )
            return
        self.screen.blit(bar, bar.get_rect(midtop=(center_x, y)))
    def draw_title_background(self, time):
        old_camera = (self.camera.x, self.camera.z, self.camera.zoom)
        self.camera.x = self.spawn.x
        self.camera.z = self.spawn.y
        self.camera.zoom = 1.0
        self.draw_static_cave_base()
        center = self.camera.project(self.spawn.x, self.spawn.y)
        pulse = 0.5 + 0.5 * math.sin(time * 2.1)
        glow = make_radial_glow(520 + round(pulse * 54), MYCELIUM_FAINT, 28 + round(pulse * 10), 2.4)
        self.screen.blit(glow, glow.get_rect(center=(round(center.x), round(center.y))))
        if self.mycelial_overlay:
            overlay = self.mycelial_overlay.copy()
            overlay.set_alpha(138)
            self.blit_world_image(overlay, self.spawn, cache=False)
        for index, lumen in enumerate(self.lumens):
            bob = math.sin(time * 1.8 + index) * 8
            screen = self.camera.project(lumen.x, lumen.z, 36 + bob)
            scale = self.visual_depth_scale(pygame.Vector2(lumen.x, lumen.z))
            frames = self.lumen_spin_frames or self.lumen_front_frame
            if frames:
                pulse = 0.5 + 0.5 * math.sin(time * 4.0 + lumen.phase)
                glow = make_radial_glow(round(84 * scale), LUMEN, round((22 + pulse * 8) * scale), 1.95)
                haze = make_radial_glow(round(40 * scale), LUMEN_CORE, round((34 + pulse * 14) * scale), 1.40)
                self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
                self.screen.blit(haze, haze.get_rect(center=(round(screen.x), round(screen.y))))
                rendered = lumen_swing_rotated(frames, time, lumen.phase)
                target = max(1, round(16 * scale))
                art = pygame.transform.scale(rendered, (target, target))
                self.screen.blit(art, art.get_rect(center=(round(screen.x), round(screen.y))))
            else:
                pulse = 0.5 + 0.5 * math.sin(time * 4.0 + lumen.phase)
                wisp_glow = make_radial_glow(round((92 + pulse * 18) * scale), LUMEN, round((14 + pulse * 6) * scale), 1.95)
                haze = make_radial_glow(round((36 + pulse * 8) * scale), LUMEN_CORE, round((30 + pulse * 8) * scale), 1.45)
                self.screen.blit(wisp_glow, wisp_glow.get_rect(center=(round(screen.x), round(screen.y))))
                self.screen.blit(haze, haze.get_rect(center=(round(screen.x), round(screen.y))))
                pygame.draw.circle(self.screen, (*LUMEN_CORE, round(54 * scale)), (round(screen.x), round(screen.y)), max(1, round(3 * scale)))
        self.camera.x, self.camera.z, self.camera.zoom = old_camera
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 74))
        self.screen.blit(shade, (0, 0))
    def draw_end_game_fade(self):
        if not self.end_game_fade_active:
            return
        t = smoothstep(min(1.0, self.end_game_fade_time / END_GAME_FADE_SECONDS))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, round(255 * t)))
        self.screen.blit(overlay, (0, 0))
    def draw_gameplay_fade(self):
        if self.gameplay_fade >= 1.0:
            return
        t = smoothstep(max(0.0, min(1.0, self.gameplay_fade)))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, round(255 * (1.0 - t))))
        self.screen.blit(overlay, (0, 0))
    def draw_title_button(self, label, x, y, width=244, primary=False, selected=False):
        height = 40
        rect = pygame.Rect(x, y, width, height)
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        if selected:
            panel.fill((13, 42, 52, 232))
        else:
            panel.fill((20, 30, 32, 222) if primary else (10, 16, 17, 210))
        border_rect = panel.get_rect()
        self.draw_textured_rect_border(panel, border_rect, self.ui_wood_texture, 4)
        highlight = MYCELIUM if selected or primary else MYCELIUM_FAINT
        pygame.draw.rect(panel, (*highlight, 72 if selected or primary else 38), border_rect.inflate(-8, -8), 1)
        if selected:
            pygame.draw.rect(panel, (*MYCELIUM, 58), panel.get_rect().inflate(-6, -6), 1)
        image = self.small_font.render(label, True, TEXT if selected or primary else QUEST)
        panel.blit(image, image.get_rect(center=panel.get_rect().center))
        self.screen.blit(panel, rect)
        return rect
    def draw_branded_menu_title(self, surface, word, center_x, center_y):
        scale = SCREEN_HEIGHT / BASE_SCREEN_HEIGHT
        font = self.assets.get_font(max(22, round(32 * scale)), bold=True)
        big_font = self.assets.get_font(max(26, round(39 * scale)), bold=True)
        gold = (218, 194, 137)
        gold_hi = (250, 232, 174)
        deep_shadow = (3, 5, 7)
        pieces = []
        total_width = 0
        for index, char in enumerate(word):
            oversized = index in (0, len(word) - 1)
            char_font = big_font if oversized else font
            image = char_font.render(char, True, gold_hi if oversized else gold)
            shadow = char_font.render(char, True, deep_shadow)
            pieces.append((image, shadow))
            total_width += image.get_width() + 1
        x = center_x - total_width // 2
        for image, shadow in pieces:
            rect = image.get_rect()
            rect.midleft = (x, center_y)
            surface.blit(shadow, rect.move(2, 3))
            surface.blit(image, rect)
            x += image.get_width() + 1
    def draw_confirmation_ui(self):
        fade = max(0.0, min(1.0, self.confirm_fade))
        if self.confirm_action is None and fade <= 0:
            self.confirm_rect = pygame.Rect(0, 0, 0, 0)
            self.confirm_yes_rect = pygame.Rect(0, 0, 0, 0)
            self.confirm_no_rect = pygame.Rect(0, 0, 0, 0)
            return
        fade = fade * fade * (3 - 2 * fade)
        action = self.confirm_action or self.confirm_display_action

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, round(128 * fade)))
        self.screen.blit(overlay, (0, 0))

        width = min(560, SCREEN_WIDTH - 56)
        height = 210
        rect = pygame.Rect((SCREEN_WIDTH - width) // 2, (SCREEN_HEIGHT - height) // 2, width, height)
        self.confirm_rect = rect
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((6, 10, 12, 246))
        pygame.draw.rect(panel, (92, 70, 38), panel.get_rect(), 1)
        pygame.draw.rect(panel, (*MYCELIUM, 80), panel.get_rect().inflate(-6, -6), 1)

        if action == "end_game":
            title = "END GAME"
            body = "Return to the title screen. Current progress will be lost."
            confirm = "End"
        elif action == "framebuffer_reload":
            key = self.confirm_payload or self.framebuffer_key
            label = FRAMEBUFFER_OPTIONS.get(key, FRAMEBUFFER_OPTIONS[self.framebuffer_key])[0]
            title = "RESTART REQUIRED"
            body = f"Changing framebuffer to {label} requires a restart. Current progress will be lost."
            confirm = "Continue"
        else:
            title = "EXIT GAME"
            body = "Return to the desktop/browser shell."
            confirm = "Exit"

        self.draw_branded_menu_title(panel, title, width // 2, 36)
        pygame.draw.line(panel, (92, 70, 38), (28, 64), (width - 28, 64), 1)
        y = 84
        for line in self.wrap_text(body, self.small_font, width - 56):
            body_image = self.small_font.render(line, True, (218, 194, 137))
            panel.blit(body_image, body_image.get_rect(centerx=width // 2, y=y))
            y += body_image.get_height() + 4

        button_width = 132
        button_height = 38
        gap = 18
        buttons_width = button_width * 2 + gap
        yes_rect = pygame.Rect((width - buttons_width) // 2, height - 60, button_width, button_height)
        no_rect = pygame.Rect(yes_rect.right + gap, height - 60, button_width, button_height)
        for index, (button_rect, label) in enumerate(((yes_rect, confirm), (no_rect, "Cancel"))):
            selected = self.confirm_selected == index
            fill = (9, 44, 58, 238) if selected else (10, 16, 17, 224)
            border = MYCELIUM if selected else MYCELIUM_FAINT
            pygame.draw.rect(panel, fill, button_rect)
            pygame.draw.rect(panel, border, button_rect, 2 if selected else 1)
            if selected:
                pygame.draw.rect(panel, (*MYCELIUM, 48), button_rect.inflate(-6, -6), 1)
            text = self.small_font.render(label, True, TEXT if selected else (218, 194, 137))
            panel.blit(text, text.get_rect(center=button_rect.center))

        panel.set_alpha(round(255 * fade))
        self.screen.blit(panel, rect)
        self.confirm_yes_rect = yes_rect.move(rect.topleft)
        self.confirm_no_rect = no_rect.move(rect.topleft)
    def draw_about_ui(self):
        fade = max(0.0, min(1.0, self.about_fade))
        if not self.about_open and fade <= 0:
            self.about_rect = pygame.Rect(0, 0, 0, 0)
            return
        fade = fade * fade * (3 - 2 * fade)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, round(140 * fade)))
        self.screen.blit(overlay, (0, 0))

        rows = self.about_lines or [("Build", "unknown"), ("Python", "-")]
        width = min(620, SCREEN_WIDTH - 56)
        line_height = self.small_font.get_height() + 8
        header_height = 74
        footer_height = 46
        height = min(
            SCREEN_HEIGHT - 48,
            header_height + line_height * len(rows) + footer_height,
        )
        rect = pygame.Rect(
            (SCREEN_WIDTH - width) // 2, (SCREEN_HEIGHT - height) // 2, width, height
        )
        self.about_rect = rect

        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((6, 10, 12, 246))
        pygame.draw.rect(panel, (92, 70, 38), panel.get_rect(), 1)
        pygame.draw.rect(panel, (*MYCELIUM, 80), panel.get_rect().inflate(-6, -6), 1)

        self.draw_branded_menu_title(panel, "ABOUT", width // 2, 34)
        pygame.draw.line(panel, (92, 70, 38), (28, 60), (width - 28, 60), 1)

        label_x = 36
        value_right = width - 36
        value_space = value_right - label_x - 150
        y = 76
        for label, value in rows:
            label_image = self.small_font.render(str(label), True, (218, 194, 137))
            panel.blit(label_image, (label_x, y))
            value_text = str(value)
            value_image = self.small_font.render(value_text, True, TEXT)
            while value_image.get_width() > value_space and len(value_text) > 6:
                value_text = value_text[:-2]
                value_image = self.small_font.render(value_text + "...", True, TEXT)
            panel.blit(value_image, (value_right - value_image.get_width(), y))
            y += line_height

        hint_image = self.small_font.render(
            "Press any key or click to close", True, MYCELIUM
        )
        panel.blit(hint_image, hint_image.get_rect(centerx=width // 2, bottom=height - 14))

        panel.set_alpha(round(255 * fade))
        self.screen.blit(panel, rect)
    def wrap_text(self, text, font, max_width):
        lines = []
        current = ""
        for word in text.split():
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
    def draw_story_word(self, word, time, duration=CONCENTRATE_UNLOCK_SECONDS):
        clock = self.transit_time if word == "transit" else self.cinematic_time
        t = min(1.0, clock / max(0.001, duration))
        fade = math.sin(t * math.pi)
        pulse = 0.5 + 0.5 * math.sin(time * 4.0)
        origin = self.camera.project(self.spawn.x, self.spawn.y, 80)
        image = self.font.render(word, True, MYCELIUM_FAINT)
        image.set_alpha(round((118 + pulse * 34) * fade))
        rect = image.get_rect(center=(round(origin.x), round(origin.y - 56 * self.camera.zoom)))
        self.screen.blit(image, rect)
    def guidance_word_fade(self):
        if self.guidance_word is None:
            return 0.0
        if self.guidance_time < GUIDANCE_FADE_IN_SECONDS:
            return smoothstep(self.guidance_time / GUIDANCE_FADE_IN_SECONDS)
        hold_end = GUIDANCE_FADE_IN_SECONDS + GUIDANCE_HOLD_SECONDS
        if self.guidance_time < hold_end:
            return 1.0
        fade_out_t = (self.guidance_time - hold_end) / GUIDANCE_FADE_OUT_SECONDS
        return 1.0 - smoothstep(min(1.0, fade_out_t))
    def draw_guidance_word_overlay(self, time):
        if self.guidance_word is None:
            return
        fade = self.guidance_word_fade()
        if fade <= 0:
            return
        word = self.guidance_word
        font = self.title_small_font
        if font.size(word)[0] > SCREEN_WIDTH - 80:
            font = self.font
        pulse = 0.5 + 0.5 * math.sin(time * 3.2)
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        glow_size = min(SCREEN_WIDTH - 48, 420)
        glow = make_radial_glow(glow_size, MYCELIUM, round((34 + pulse * 10) * fade), 2.45)
        self.screen.blit(glow, glow.get_rect(center=center))

        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 8, 9, round(34 * fade)))
        self.screen.blit(veil, (0, 0))

        shadow = font.render(word, True, (0, 0, 0))
        text = font.render(word, True, LUMEN_CORE)
        aura = font.render(word, True, MYCELIUM_FAINT)
        shadow.set_alpha(round(176 * fade))
        text.set_alpha(round((210 + pulse * 36) * fade))
        aura.set_alpha(round(82 * fade))
        self.screen.blit(aura, aura.get_rect(center=(center[0], center[1] - 1)))
        self.screen.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 3)))
        self.screen.blit(text, text.get_rect(center=center))
    def draw_transit_markers(self, time):
        if self.phase != "transit_select":
            return
        for index, pos in enumerate(self.transit_destinations):
            screen = self.camera.project(pos.x, pos.y)
            selected = index == self.selected_transit_destination
            pulse = 0.5 + 0.5 * math.sin(time * 4.0 + index * 0.8)
            alpha = round((20 + pulse * 8) if not selected else (42 + pulse * 24))
            width = round((120 if not selected else 172) * self.camera.zoom)
            height = round(width * DEPTH_SCALE)
            ring = make_elliptical_ring(width, height, max(4, round(12 * self.camera.zoom)), MYCELIUM_FAINT, alpha)
            self.screen.blit(ring, ring.get_rect(center=(round(screen.x), round(screen.y))))
            if selected:
                glow = make_radial_glow(round(240 * self.camera.zoom), MYCELIUM_FAINT, 24 + round(pulse * 10), 2.8)
                self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
    def draw_transit_click_ui(self):
        if self.transit_prompt_open and self.transit_available and self.controls_enabled:
            text = self.small_font.render("Transit", True, TEXT)
            width = max(94, text.get_width() + 30)
            height = 34
            player_screen = self.camera.project(self.player.pos.x, self.player.pos.y, self.player.height + 82)
            x = round(player_screen.x - width * 0.5)
            y = round(player_screen.y - height * 0.5)
            x = max(12, min(SCREEN_WIDTH - width - 12, x))
            y = max(12, min(SCREEN_HEIGHT - height - 12, y))
            self.transit_button_rect = pygame.Rect(x, y, width, height)
            button = pygame.Surface((width, height), pygame.SRCALPHA)
            button.fill((12, 17, 18, 210))
            pygame.draw.rect(button, MYCELIUM_FAINT, button.get_rect(), 1)
            button.blit(text, text.get_rect(center=button.get_rect().center))
            self.screen.blit(button, self.transit_button_rect)
        elif self.transit_targeting:
            self.transit_button_rect = pygame.Rect(0, 0, 0, 0)
            text = self.small_font.render("Click a destination", True, TEXT)
            width = text.get_width() + 28
            height = 34
            rect = pygame.Rect((SCREEN_WIDTH - width) // 2, 18, width, height)
            panel = pygame.Surface((width, height), pygame.SRCALPHA)
            panel.fill((12, 17, 18, 190))
            pygame.draw.rect(panel, MYCELIUM_FAINT, panel.get_rect(), 1)
            panel.blit(text, text.get_rect(center=panel.get_rect().center))
            self.screen.blit(panel, rect)
        else:
            self.transit_button_rect = pygame.Rect(0, 0, 0, 0)
    def draw_top_stone_bar(self):
        if self.top_stone_bar is not None:
            self.screen.blit(self.top_stone_bar, (0, 0))
    def draw_location_plaque(self):
        self.draw_stone_dock(
            pygame.Rect((SCREEN_WIDTH - 240) // 2, 0, 240, 36),
            sections=1,
            border=5,
            divider_width=0,
            label="Speleos Prime",
            darken=132,
        )
    def draw_top_hud_dock(self):
        self.draw_location_plaque()
    def draw_bottom_hud_dock(self):
        width = min(750, SCREEN_WIDTH)
        dock_height = 100
        rect = pygame.Rect((SCREEN_WIDTH - width) // 2, SCREEN_HEIGHT - dock_height, width, dock_height)
        panel, section_rects = self.build_stone_dock(
            rect,
            sections=3,
            section_widths=(INVENTORY_SECTION_WIDTH, 200, 200),
            border=7,
            divider_width=6,
        )
        if panel is None:
            return
        if section_rects:
            self.resource_icon_rects = {}
            self.inventory_pagination_rects = []
            section = section_rects[0]
            grid_rect = pygame.Rect(section.left + INVENTORY_PAGINATION_WIDTH, section.top, INVENTORY_PAGE_GRID_WIDTH, section.height)
            self.draw_inventory_pagination(panel, section, rect.topleft)
            self.draw_lumen_resource_counter(panel, grid_rect, rect.topleft)
        if len(section_rects) > 1:
            self.draw_guidance_command(panel, section_rects[1])
        self.screen.blit(panel, rect)
    def draw_stone_dock(self, rect, sections=1, border=7, divider_width=6, label=None, darken=82, section_widths=None):
        panel, _ = self.build_stone_dock(rect, sections, border, divider_width, label, darken, section_widths)
        if panel is not None:
            self.screen.blit(panel, pygame.Rect(rect))
    def build_stone_dock(self, rect, sections=1, border=7, divider_width=6, label=None, darken=82, section_widths=None):
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return None, []
        width, height = rect.size
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel_rect = panel.get_rect()
        section_rects = []

        panel.fill((20, 20, 18, 232))
        if self.ui_stone_texture is not None:
            self.blit_tiled_texture(panel, self.ui_stone_texture, panel_rect, offset=rect.topleft)
            veil = pygame.Surface((width, height), pygame.SRCALPHA)
            veil.fill((16, 18, 18, darken))
            panel.blit(veil, (0, 0))

        self.draw_stone_dock_strip(panel, pygame.Rect(0, 0, width, border), (142, 138, 124), "horizontal")
        self.draw_stone_dock_strip(panel, pygame.Rect(0, height - border, width, border), (78, 78, 72), "horizontal")
        self.draw_stone_dock_strip(panel, pygame.Rect(0, 0, border, height), (112, 112, 102), "vertical")
        self.draw_stone_dock_strip(panel, pygame.Rect(width - border, 0, border, height), (62, 64, 60), "vertical")

        if section_widths:
            edges = [0]
            for section_width in section_widths:
                edges.append(edges[-1] + section_width)
            edges[-1] = width
        else:
            edges = [round(width * index / sections) for index in range(sections + 1)] if sections > 0 else [0, width]

        if len(edges) > 2 and divider_width > 0:
            for divider in edges[1:-1]:
                divider_rect = pygame.Rect(divider - divider_width // 2, border + 1, divider_width, height - border * 2 - 2)
                self.draw_stone_dock_strip(panel, divider_rect, (106, 104, 96), "vertical")
        for left, right in zip(edges, edges[1:]):
            section_rects.append(pygame.Rect(left + border, border, max(0, right - left - border * 2), max(0, height - border * 2)))

        pygame.draw.rect(panel, (206, 198, 166, 68), panel_rect.inflate(-12, -12), 1)
        pygame.draw.rect(panel, (8, 9, 9, 190), panel_rect, 1)
        if label:
            label_image = self.small_font.render(label, True, (246, 248, 246))
            shadow_image = self.small_font.render(label, True, (0, 0, 0))
            center = panel_rect.center
            panel.blit(shadow_image, shadow_image.get_rect(center=(center[0] + 1, center[1] + 1)))
            panel.blit(label_image, label_image.get_rect(center=center))
        return panel, section_rects
    def draw_inventory_pagination(self, panel, section, screen_offset):
        strip = pygame.Rect(section.left, section.top, INVENTORY_PAGINATION_WIDTH, section.height)
        box_height = strip.height // INVENTORY_PAGE_COUNT
        inner_margin = 2
        for i in range(INVENTORY_PAGE_COUNT):
            box = pygame.Rect(strip.left + inner_margin, strip.top + i * box_height + inner_margin, strip.width - inner_margin * 2, box_height - inner_margin * 2)
            if i == self.inventory_page:
                color = (80, 80, 80, 255)
                border_color = (140, 140, 140, 255)
            else:
                color = (216, 216, 216, 255)
                border_color = (200, 200, 200, 255)
            pygame.draw.rect(panel, color, box, border_radius=2)
            pygame.draw.rect(panel, border_color, box, 1, border_radius=2)
            hit_rect = box.move(screen_offset[0] - section.left + strip.left, screen_offset[1])
            self.inventory_pagination_rects.append(hit_rect)
    def _inventory_page_items(self, page):
        if page == 0:
            return [
                ("lumen", self.lumen_icon, self.lumen_count, "lumen"),
                ("shell", self.shell_icon, self.shell_count, "shell"),
                ("acorn", self.acorn_icon, self.acorn_count, "acorn"),
                ("root", self.root_icon, self.root_count, "root"),
                ("crystal", self.crystal_icon, self.crystal_count, "crystal"),
                ("amber", self.amber_icon, self.amber_count, "amber"),
            ]
        start = page * 10
        return [
            (f"page{page}_{i}", None, start + i + 1, None)
            for i in range(6)
        ]
    def _draw_inventory_grid(self, panel, rect, items, screen_offset, y_offset=0):
        rect = pygame.Rect(rect)
        column_width = rect.width / 3
        column_centers = [round(rect.left + column_width * (index + 0.5) - 30) for index in range(3)]
        top_y = rect.top + y_offset
        row1_y = top_y + round(rect.height * 0.24)
        row2_y = top_y + round(rect.height * 0.78)
        for i, (key, icon, count, fallback) in enumerate(items):
            col = i % 3
            row = i // 3
            cy = row1_y if row == 0 else row2_y
            center = (column_centers[col], cy)
            if icon is not None:
                self.record_resource_hit_rect(key, center, (46, 46), screen_offset)
                img = icon.copy()
                img.set_alpha(236)
                panel.blit(img, img.get_rect(center=center))
            elif fallback is not None:
                self.record_resource_hit_rect(key, center, (46, 46), screen_offset)
                self.draw_icon_resource(panel, None, count, center, rect.right - 4, fallback=fallback)
            else:
                placeholder = pygame.Rect(0, 0, 36, 36)
                placeholder.center = center
                pygame.draw.rect(panel, (60, 64, 60, 200), placeholder, border_radius=4)
                pygame.draw.rect(panel, (120, 124, 120, 160), placeholder, 1, border_radius=4)
                count_text = self.font.render(str(count), True, (200, 200, 200, 236))
                panel.blit(count_text, count_text.get_rect(center=center))
            if icon is not None:
                col_right = rect.left + column_width * (col + 1) - 4
                self.draw_resource_count(panel, count, (center[0] + 28, cy), col_right)
    def draw_lumen_resource_counter(self, panel, rect, screen_offset=(0, 0)):
        if self.inventory_page_anim_t > 0:
            out_items = self._inventory_page_items(self.inventory_page)
            in_items = self._inventory_page_items(self.inventory_page_target)
            p = self.inventory_page_anim_t
            h = rect.height
            if self.inventory_page_target > self.inventory_page:
                out_off = -round(p * h)
                in_off = round((1.0 - p) * h)
            else:
                out_off = round(p * h)
                in_off = -round((1.0 - p) * h)
            self._draw_inventory_grid(panel, rect, out_items, screen_offset, out_off)
            self._draw_inventory_grid(panel, rect, in_items, screen_offset, in_off)
        else:
            items = self._inventory_page_items(self.inventory_page)
            self._draw_inventory_grid(panel, rect, items, screen_offset, 0)
    def draw_icon_resource(self, panel, icon, count, center, max_right, alpha=232, fallback=None):
        if icon is not None:
            image = icon.copy()
            image.set_alpha(alpha)
            panel.blit(image, image.get_rect(center=center))
        elif fallback == "shell":
            pygame.draw.circle(panel, (222, 236, 246, 214), center, 14, 3)
            pygame.draw.arc(panel, (246, 248, 246, 226), pygame.Rect(center[0] - 10, center[1] - 10, 20, 20), 0.5, 5.2, 3)
        elif fallback == "root":
            pygame.draw.line(panel, (194, 198, 190), (center[0], center[1] - 14), (center[0], center[1] + 12), 4)
            pygame.draw.line(panel, (194, 198, 190), (center[0], center[1] + 4), (center[0] - 14, center[1] + 14), 3)
            pygame.draw.line(panel, (194, 198, 190), (center[0], center[1] + 4), (center[0] + 14, center[1] + 14), 3)
        elif fallback in ("crystal", "amber"):
            color = (238, 190, 72, 226) if fallback == "amber" else (222, 236, 246, 214)
            points = [
                (center[0], center[1] - 18),
                (center[0] + 12, center[1] - 4),
                (center[0] + 7, center[1] + 16),
                (center[0] - 9, center[1] + 16),
                (center[0] - 13, center[1] - 4),
            ]
            pygame.draw.polygon(panel, color, points)
            pygame.draw.polygon(panel, (246, 248, 246, 226), points, 2)
        elif fallback == "acorn":
            pygame.draw.circle(panel, (170, 92, 34, 226), (center[0], center[1] + 4), 13)
            pygame.draw.ellipse(panel, (106, 76, 52, 226), pygame.Rect(center[0] - 14, center[1] - 14, 28, 16))
        self.draw_resource_count(panel, count, (center[0] + 28, center[1]), max_right)
    def record_resource_hit_rect(self, item_key, center, size, screen_offset):
        rect = pygame.Rect(0, 0, size[0], size[1])
        rect.center = (round(center[0] + screen_offset[0]), round(center[1] + screen_offset[1]))
        self.resource_icon_rects[item_key] = rect
    def item_detail_data(self, item_key):
        details = {
            "lumen": {
                "name": "Lumen",
                "count": self.lumen_count,
                "description": "A living mote of pale fungal energy. Lumens are gathered by seeking through the cave, then rooted into the mycelial network to wake deeper growth.",
                "icon": self.lumen_icon,
                "frames": self.lumen_spin_frames,
                "swing": True,
            },
            "shell": {
                "name": "Glass Shell",
                "count": self.shell_count,
                "description": "A spiral shell with glassy facets, useful for focusing echoes and preserving delicate cave resonance.",
                "icon": self.shell_icon,
                "frames": self.shell_spin_frames,
            },
            "acorn": {
                "name": "Acorn",
                "count": self.acorn_count,
                "description": "A compact seed of stored forest memory. Acorns carry patient energy for future growth.",
                "icon": self.acorn_icon,
                "frames": self.acorn_spin_frames,
            },
            "root": {
                "name": "Root",
                "count": self.root_count,
                "description": "A measure of established mycelial reach. Roots mark where the network has taken hold beneath the stone.",
                "icon": self.root_icon,
                "frames": self.root_spin_frames,
            },
            "crystal": {
                "name": "Crystal",
                "count": self.crystal_count,
                "description": "A clear quartz shard that catches and bends cave light into precise channels.",
                "icon": self.crystal_icon,
                "frames": self.crystal_spin_frames,
                "lumen_spin": True,
            },
            "amber": {
                "name": "Amber Shard",
                "count": self.amber_count,
                "description": "A warm shard of hardened sap, holding old sunlight in a mineral-like glow.",
                "icon": self.amber_icon,
                "frames": self.amber_spin_frames,
            },
        }
        return details.get(item_key, details["lumen"])
    def draw_item_drawer(self):
        if not self.item_drawer_visible or self.selected_item is None:
            self.item_drawer_close_rect = pygame.Rect(0, 0, 0, 0)
            return
        progress = smoothstep(self.item_drawer_t)
        dock_height = 100
        drawer_height = min(ITEM_DRAWER_HEIGHT, SCREEN_HEIGHT - 132)
        width = min(720, SCREEN_WIDTH)
        x = (SCREEN_WIDTH - width) // 2
        full_y = SCREEN_HEIGHT - dock_height - drawer_height
        y = round(SCREEN_HEIGHT - dock_height - drawer_height * progress)
        rect = pygame.Rect(x, y, width, drawer_height)

        panel, _ = self.build_stone_dock(rect, sections=1, border=7, divider_width=0, darken=112)
        if panel is None:
            return
        inner = panel.get_rect().inflate(-34, -28)

        close_size = 32
        close_rect = pygame.Rect(panel.get_width() - close_size - 16, 14, close_size, close_size)
        self.item_drawer_close_rect = close_rect.move(rect.topleft)
        pygame.draw.rect(panel, (10, 12, 12, 218), close_rect)
        pygame.draw.rect(panel, (216, 210, 184, 132), close_rect, 1)
        x_font = self.small_font
        x_text = x_font.render("X", True, (246, 248, 246))
        panel.blit(x_text, x_text.get_rect(center=close_rect.center))

        data = self.item_detail_data(self.selected_item)
        art_rect = pygame.Rect(inner.left + 8, inner.top + 18, 260, 260)
        text_rect = pygame.Rect(art_rect.right + 30, inner.top + 28, inner.right - art_rect.right - 44, inner.height - 42)
        self.draw_item_detail_art(panel, data, art_rect)
        self.draw_item_detail_text(panel, data, text_rect)

        if y < SCREEN_HEIGHT - dock_height:
            self.screen.blit(panel, rect)
        if progress <= 0:
            self.item_drawer_close_rect = pygame.Rect(0, 0, 0, 0)
    def draw_item_detail_art(self, panel, data, rect):
        if rect.width <= 0 or rect.height <= 0:
            return
        art_panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        art_panel.fill((4, 8, 9, 42))
        pygame.draw.rect(art_panel, (216, 210, 184, 48), art_panel.get_rect(), 1)

        image = None
        frames = data.get("frames") or []
        bob = 0
        glow_rect = None
        if frames:
            if data.get("swing"):
                t = self.ui_time
                rendered = lumen_swing_rotated(frames, t)
                glow_rect = rect
                bob = math.sin(t * 2.5) * 4
                image = rendered
            elif len(frames) == 1:
                t = self.ui_time
                rendered = lumen_rotated_surface(frames[0], t)
                glow_rect = rect
                bob = math.sin(t * 2.5) * 4
                image = rendered
            elif data.get("lumen_spin"):
                t = self.ui_time
                raw = (360 * math.sin(t * 0.12) + 240 * math.sin(t * 0.07) + 160 * math.sin(t * 0.19) + 280 * math.sin(t * 0.17 + 0.5) + 200 * math.sin(t * 0.43 + 2.1) + 80 * math.sin(t * 1.7 + 0.8))
                n = len(frames)
                frame_index = min(int(abs(raw) % 90 / 90 * n), n - 1)
                image = frames[frame_index]
            else:
                fps = data.get("spin_fps", ITEM_SPIN_FPS)
                frame_index = int(self.ui_time * fps) % len(frames)
                image = frames[frame_index]
        elif data.get("icon") is not None:
            image = data["icon"]
        if image is not None:
            max_size = min(rect.width - 28, rect.height - 28)
            scale = min(max_size / image.get_width(), max_size / image.get_height())
            size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
            scaler = pygame.transform.scale if WEB_BUILD else pygame.transform.smoothscale
            art = scaler(image, size)
            center = art_panel.get_rect().center
            art_panel.blit(art, art.get_rect(center=(center[0], center[1] + round(bob))))
        if glow_rect is not None:
            glow = make_radial_glow(400, (240, 242, 245), 200, 1.95)
            panel.blit(glow, glow.get_rect(center=glow_rect.center))
        panel.blit(art_panel, rect)
    def draw_item_detail_text(self, panel, data, rect):
        if rect.width <= 0 or rect.height <= 0:
            return
        name = data["name"]
        count = data["count"]
        title = self.title_small_font.render(name, True, (246, 248, 246))
        title_shadow = self.title_small_font.render(name, True, (0, 0, 0))
        panel.blit(title_shadow, title_shadow.get_rect(topleft=(rect.left + 2, rect.top + 2)))
        panel.blit(title, title.get_rect(topleft=rect.topleft))

        count_text = self.font.render(f"Count: {count}", True, MYCELIUM_FAINT)
        panel.blit(count_text, count_text.get_rect(topleft=(rect.left, rect.top + 48)))

        lines = self.wrap_text(data["description"], self.small_font, rect.width)
        y = rect.top + 88
        for line in lines[:8]:
            text = self.small_font.render(line, True, TEXT)
            panel.blit(text, (rect.left, y))
            y += 24
    def draw_resource_count(self, panel, count, midleft, max_right=None):
        value = str(count)
        font = self.font
        if max_right is not None and midleft[0] + font.size(value)[0] > max_right:
            font = self.small_font
        count_text = font.render(value, True, (246, 248, 246))
        shadow_text = font.render(value, True, (0, 0, 0))
        panel.blit(shadow_text, shadow_text.get_rect(midleft=(midleft[0] + 1, midleft[1] + 1)))
        panel.blit(count_text, count_text.get_rect(midleft=midleft))
    def active_guidance_command(self):
        if self.phase in ("feed_complete_focus", "concentrate_unlock", "feed_complete_return", "post_feed"):
            return "Concentrate"
        if self.phase in (*TRANSIT_UNLOCK_PHASES, "transit", "transit_select", "transit_disappear", "transit_pan", "transit_appear"):
            return "Transit"
        return ""
    def draw_guidance_command(self, panel, rect):
        rect = pygame.Rect(rect)
        command = self.active_guidance_command()
        if not command or rect.width <= 0 or rect.height <= 0:
            return
        label = self.small_font.render("COMMAND", True, (168, 178, 172))
        command_font = self.font if self.font.size(command)[0] <= rect.width - 28 else self.small_font
        command_text = command_font.render(command, True, (246, 248, 246))
        shadow_text = command_font.render(command, True, (0, 0, 0))
        center_x = rect.centerx
        label_y = rect.top + 10
        command_y = rect.centery + 10
        panel.blit(label, label.get_rect(center=(center_x, label_y)))
        panel.blit(shadow_text, shadow_text.get_rect(center=(center_x + 1, command_y + 1)))
        panel.blit(command_text, command_text.get_rect(center=(center_x, command_y)))
    def draw_stone_dock_strip(self, surface, rect, tint, orientation="horizontal"):
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return
        if self.ui_stone_texture is None:
            pygame.draw.rect(surface, tint, rect)
            return
        strip = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        self.blit_tiled_texture(strip, self.ui_stone_texture, strip.get_rect())
        strip.fill((*tint, 255), special_flags=pygame.BLEND_RGB_MULT)
        if orientation == "vertical":
            half = max(1, rect.width // 2)
            pygame.draw.rect(strip, (76, 76, 70, 74), pygame.Rect(half, 0, rect.width - half, rect.height))
            pygame.draw.line(strip, (210, 204, 176, 54), (0, 0), (0, rect.height), 1)
            pygame.draw.line(strip, (26, 28, 26, 92), (rect.width - 1, 0), (rect.width - 1, rect.height), 1)
        else:
            half = max(1, rect.height // 2)
            pygame.draw.rect(strip, (76, 76, 70, 74), pygame.Rect(0, half, rect.width, rect.height - half))
            pygame.draw.line(strip, (210, 204, 176, 54), (0, 0), (rect.width, 0), 1)
            pygame.draw.line(strip, (26, 28, 26, 92), (0, rect.height - 1), (rect.width, rect.height - 1), 1)
        surface.blit(strip, rect)
    def draw_panel_corner_ornaments(self, panel):
        if not self.hud_corner_ornaments:
            return
        width, height = panel.get_size()
        top_right = self.hud_corner_ornaments["top_right"]
        bottom_left = self.hud_corner_ornaments["bottom_left"]
        bottom_right = self.hud_corner_ornaments["bottom_right"]
        placements = {
            "top_left": (0, 0),
            "top_right": (width - top_right.get_width(), 0),
            "bottom_left": (0, height - bottom_left.get_height()),
            "bottom_right": (width - bottom_right.get_width(), height - bottom_right.get_height()),
        }
        for key, pos in placements.items():
            panel.blit(self.hud_corner_ornaments[key], pos)
    def draw_wood_grain_panel_border(self, panel, thickness=8):
        self.draw_textured_rect_border(panel, panel.get_rect(), self.ui_wood_texture, thickness)
    def draw_textured_rect_border(self, surface, rect, texture, thickness):
        rect = pygame.Rect(rect)
        thickness = max(1, int(thickness))
        if texture is None:
            pygame.draw.rect(surface, WOOD_GRAIN, rect, thickness)
            return
        strips = [
            pygame.Rect(rect.left, rect.top, rect.width, thickness),
            pygame.Rect(rect.left, rect.bottom - thickness, rect.width, thickness),
            pygame.Rect(rect.left, rect.top, thickness, rect.height),
            pygame.Rect(rect.right - thickness, rect.top, thickness, rect.height),
        ]
        for strip in strips:
            self.blit_tiled_texture(surface, texture, strip)
        pygame.draw.rect(surface, WOOD_GRAIN_DARK, rect, 1)
        inner = rect.inflate(-thickness * 2, -thickness * 2)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.rect(surface, WOOD_GRAIN_LIGHT, inner, 1)
    def blit_tiled_texture(self, surface, texture, target_rect, offset=(0, 0)):
        target_rect = pygame.Rect(target_rect)
        if target_rect.width <= 0 or target_rect.height <= 0:
            return
        texture_width, texture_height = texture.get_size()
        if texture_width <= 0 or texture_height <= 0:
            return
        original_clip = surface.get_clip()
        surface.set_clip(target_rect)
        start_x = target_rect.left - ((target_rect.left + offset[0]) % texture_width)
        start_y = target_rect.top - ((target_rect.top + offset[1]) % texture_height)
        for y in range(start_y, target_rect.bottom, texture_height):
            for x in range(start_x, target_rect.right, texture_width):
                surface.blit(texture, (x, y))
        surface.set_clip(original_clip)
    def draw_player(self, time):
        ground = self.camera.project(self.player.pos.x, self.player.pos.y)
        luminosity = self.intro_mushroom_luminosity if not self.intro_complete else self.player_transit_visibility
        visual_height = self.player.height + self.player.terrain_lift
        body_scale = self.mushroom_body_scale
        animation_override = None
        animation_progress = None
        if self.phase == "transit_disappear":
            animation_override = "burrow"
            animation_progress = min(1.0, self.transit_time / TRANSIT_SHRINK_SECONDS)
        elif self.phase == "transit_appear":
            animation_override = "emerge"
            animation_progress = min(1.0, self.transit_time / TRANSIT_GROW_SECONDS)
        depth_scale = self.visual_depth_scale(self.player.pos, PLAYER_DEPTH_VISUAL_FAR_SCALE, PLAYER_DEPTH_VISUAL_NEAR_SCALE)
        if self.player.sprites.available:
            self.player.draw_sprite(
                self.screen,
                ground,
                time,
                self.growth_state,
                luminosity,
                body_scale,
                self.player.sprite_variant,
                animation_override=animation_override,
                animation_progress=animation_progress,
                depth_scale=depth_scale,
                camera_scale=self.camera.zoom,
                width_scale=self.player.width_scale,
                height_scale=self.player.height_scale,
                draw_height=visual_height,
            )
        else:
            self.player.draw_geometry(self.screen, ground, self.growth_state, body_scale, visual_height=visual_height)
    def draw_npc_mushroom(self, npc, time):
        ground = self.camera.project(npc.pos.x, npc.pos.y)
        t = max(0, min(1, npc.spawn_age / NPC_GROW_SECONDS))
        body_scale = 0.82 * smoothstep(t) * npc.body_scale
        animation_override = None
        animation_progress = None
        if npc.transit_phase == "shrink":
            animation_override = "burrow"
            animation_progress = min(1.0, npc.transit_time / NPC_TRANSIT_SHRINK_SECONDS)
        elif npc.transit_phase == "grow":
            animation_override = "emerge"
            animation_progress = min(1.0, npc.transit_time / NPC_TRANSIT_GROW_SECONDS)
        elif npc.channel_phase == "start":
            animation_override = "pulse_start"
            animation_progress = npc.channel_time / MUSHROOM_PULSE_EDGE_SECONDS
        elif npc.channel_phase == "loop":
            animation_override = "pulse_loop"
        elif npc.channel_phase == "end":
            animation_override = "pulse_end"
            animation_progress = npc.channel_time / MUSHROOM_PULSE_EDGE_SECONDS
        depth_scale = self.visual_depth_scale(npc.pos)
        if self.player.sprites.available:
            animation_time = math.floor((time + npc.phase) * NPC_ANIMATION_FPS) / NPC_ANIMATION_FPS
            original_moving = self.player.moving
            original_pulse = self.player.pulse_timer
            original_grounded = self.player.grounded
            original_channeling = self.player.channeling
            original_channel_requested = self.player.channel_requested
            original_channel_phase = self.player.channel_phase
            original_channel_time = self.player.channel_time
            self.player.moving = npc.moving
            self.player.pulse_timer = 0
            self.player.grounded = True
            self.player.channeling = False
            self.player.channel_requested = False
            self.player.channel_phase = None
            self.player.channel_time = 0.0
            self.player.draw_sprite(
                self.screen,
                ground,
                animation_time,
                self.growth_state,
                npc.luminosity,
                body_scale,
                npc.sprite_variant,
                animation_override=animation_override,
                animation_progress=animation_progress,
                depth_scale=depth_scale,
                camera_scale=self.camera.zoom,
                width_scale=npc.width_scale,
                height_scale=npc.height_scale,
                draw_glow=bool(npc.channeling or npc.channel_phase or animation_override),
                draw_height=npc.terrain_lift,
            )
            self.player.moving = original_moving
            self.player.pulse_timer = original_pulse
            self.player.grounded = original_grounded
            self.player.channeling = original_channeling
            self.player.channel_requested = original_channel_requested
            self.player.channel_phase = original_channel_phase
            self.player.channel_time = original_channel_time
        else:
            self.player.draw_geometry(self.screen, ground, self.growth_state, body_scale, visual_height=npc.terrain_lift)
    def draw_elemental_spell(self, spell, time):
        if spell.delay > 0:
            return
        t = spell.age / SPELL_LIFETIME
        fade = max(0.0, 1.0 - t)
        pulse = 0.5 + 0.5 * math.sin(time * 14.0 + spell.age * 9.0)
        depth_scale = self.visual_depth_scale(spell.pos)
        center = self.camera.project(spell.pos.x, spell.pos.y, 62)
        glow_size = round((110 + pulse * 34) * spell.size_scale * self.camera.zoom * depth_scale)
        glow = make_radial_glow(glow_size, spell.color, round((108 + pulse * 46) * fade), 1.12)
        self.screen.blit(glow, glow.get_rect(center=(round(center.x), round(center.y))))
        core_radius = max(2, round((8 + pulse * 4) * spell.size_scale * self.camera.zoom * depth_scale))
        self.draw_energy_orb(center, core_radius, spell.color, fade, time + spell.age * 0.7)
    def draw_energy_orb(self, center, radius, color, fade, phase):
        radius = max(3, radius)
        layer_size = max(16, round(radius * 4.2))
        layer = pygame.Surface((layer_size, layer_size), pygame.SRCALPHA)
        local_center = pygame.Vector2(layer_size / 2, layer_size / 2)
        core_glow = make_radial_glow(radius * 2.25, LUMEN_CORE, round(142 * fade), 1.5)
        layer.blit(core_glow, core_glow.get_rect(center=(round(local_center.x), round(local_center.y))))
        arc_rect = pygame.Rect(0, 0, round(radius * 2.7), round(radius * 2.7))
        arc_rect.center = (round(local_center.x), round(local_center.y))
        for index in range(4):
            start = phase * (1.5 + index * 0.18) + index * math.tau * 0.23
            span = 0.82 + 0.24 * math.sin(phase * 1.9 + index)
            alpha = round((168 - index * 14) * fade)
            width = max(2, round(radius * (0.2 if index < 2 else 0.15)))
            pygame.draw.arc(layer, (*color, alpha), arc_rect.inflate(index * 2, index * 2), start, start + span, width)

        inner_rect = pygame.Rect(0, 0, round(radius * 1.45), round(radius * 1.45))
        inner_rect.center = (round(local_center.x), round(local_center.y))
        pygame.draw.arc(layer, (*LUMEN_CORE, round(148 * fade)), inner_rect, -phase * 1.7, -phase * 1.7 + 1.05, max(2, round(radius * 0.14)))

        tangent = pygame.Vector2(math.cos(phase), math.sin(phase))
        normal = pygame.Vector2(-tangent.y, tangent.x)
        for index in range(3):
            offset = normal * ((index - 1) * radius * 0.34) + tangent * math.sin(phase * 2.1 + index) * radius * 0.22
            start = local_center + offset - tangent * radius * 0.6
            end = local_center + offset + tangent * radius * 0.65
            pygame.draw.line(layer, (*color, round((96 + index * 10) * fade)), start, end, max(1, round(radius * 0.1)))

        for index in range(5):
            angle = phase * (1.2 + index * 0.07) + index * math.tau / 5
            distance = radius * (0.25 + 0.68 * ((index * 37) % 5) / 5)
            point = pygame.Vector2(local_center.x + math.cos(angle) * distance, local_center.y + math.sin(angle) * distance * 0.72)
            pygame.draw.circle(layer, (*LUMEN_CORE, round(138 * fade)), point, max(1, round(radius * 0.12)))

        self.screen.blit(layer, layer.get_rect(center=(round(center.x), round(center.y))))
    def draw_leaf_quest_lumen(self, lumen, time):
        pos = lumen.pos
        scale = lumen.visual_scale * self.visual_depth_scale(pos)
        bob = math.sin(time * 2.5 + lumen.phase) * 7 * scale
        screen = self.camera.project(pos.x, pos.y, 48 + bob)
        frames = self.lumen_spin_frames or self.lumen_front_frame
        if frames:
            pulse = 0.5 + 0.5 * math.sin(time * 4.0 + lumen.phase)
            glow = make_radial_glow(round(84 * scale), LUMEN, round((22 + pulse * 8) * scale), 1.95)
            self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
            haze = make_radial_glow(round(40 * scale), LUMEN_CORE, round((34 + pulse * 14) * scale), 1.40)
            self.screen.blit(haze, haze.get_rect(center=(round(screen.x), round(screen.y))))
            rendered = lumen_swing_rotated(frames, time, lumen.phase)
            target = max(1, round(16 * scale))
            art = pygame.transform.scale(rendered, (target, target))
            self.screen.blit(art, art.get_rect(center=(round(screen.x), round(screen.y))))
        else:
            pulse = 0.5 + 0.5 * math.sin(time * 5.2 + lumen.phase)
            glow = make_radial_glow((128 + round(pulse * 28)) * scale, LUMEN, round((18 + pulse * 10) * scale), 1.95)
            self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
            haze = make_radial_glow((48 + round(pulse * 12)) * scale, LUMEN_CORE, round((34 + pulse * 14) * scale), 1.45)
            self.screen.blit(haze, haze.get_rect(center=(round(screen.x), round(screen.y))))
            pygame.draw.circle(self.screen, (*LUMEN_CORE, round(62 * scale)), screen, max(1, round(4 * scale)))
    def screen_point_visible(self, point, margin=WORLD_CULL_MARGIN):
        return (
            -margin <= point.x <= SCREEN_WIDTH + margin
            and -margin <= point.y <= SCREEN_HEIGHT + margin
        )
    def world_visible(self, world_pos, height=0, margin=WORLD_CULL_MARGIN):
        return self.screen_point_visible(self.camera.project(world_pos.x, world_pos.y, height), margin)
    def draw_channel_cover_leaves(self):
        for leaf in sorted(self.channel_cover_leaves, key=lambda item: item.pos.y):
            height = 0
            angle = 0
            if leaf.moving:
                height = math.sin(leaf.move_progress * math.pi) * 46
                angle = math.sin(leaf.move_progress * math.pi) * 28
            self.draw_world_sprite_shadow(leaf.image, leaf.pos, 44, angle=angle, squash=0.3, stretch=1.12, screen_offset=(0, 5))
            self.blit_world_image(leaf.image, leaf.pos, height=height, scale=1.0, angle=angle)
    def blit_world_image(self, image, world_pos, height=0, scale=1.0, screen_offset=(0, 0), special_flags=0, angle=0.0, target=None, cull=True, cache=True, quantize=True):
        if image is None:
            return None
        target = target or self.screen
        screen = self.camera.project(world_pos.x, world_pos.y, height)
        draw_scale = max(0.01, self.camera.zoom * scale * self.visual_depth_scale(world_pos))
        width, height = (
            max(1, round(image.get_width() * draw_scale)),
            max(1, round(image.get_height() * draw_scale)),
        )
        center = (round(screen.x + screen_offset[0] * self.camera.zoom), round(screen.y + screen_offset[1] * self.camera.zoom))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center
        if cull and not rect.colliderect(pygame.Rect(-WORLD_CULL_MARGIN, -WORLD_CULL_MARGIN, SCREEN_WIDTH + WORLD_CULL_MARGIN * 2, SCREEN_HEIGHT + WORLD_CULL_MARGIN * 2)):
            return None
        scaled = self.transform_world_image(image, width, height, angle, cache=cache, quantize=quantize)
        rect = scaled.get_rect(center=center)
        target.blit(scaled, rect, special_flags=special_flags)
        return rect
    def transform_world_image(self, image, width, height, angle=0.0, cache=True, quantize=True):
        profile = self.render_profile
        if quantize and profile["quantize_world_images"]:
            width = browser_bucket(width, bucket=8, maximum=900)
            height = browser_bucket(height, bucket=8, maximum=900)
            angle = 0 if abs(angle) <= 0.01 else round(angle / 5) * 5

        max_pixels = BROWSER_WORLD_CACHE_MAX_PIXELS if WEB_BUILD else NATIVE_WORLD_CACHE_MAX_PIXELS
        cache_limit = BROWSER_WORLD_CACHE_LIMIT if WEB_BUILD else NATIVE_WORLD_CACHE_LIMIT
        use_cache = cache and profile["cache_world_images"] and width * height <= max_pixels
        cache_key = None
        if use_cache:
            cache_key = (id(image), width, height, angle, profile["fast_scale"])
            cached = self.world_image_cache.get(cache_key)
            if cached is not None:
                return cached

        scaler = pygame.transform.scale if WEB_BUILD and profile["fast_scale"] else pygame.transform.smoothscale
        scaled = scaler(image, (width, height))
        if abs(angle) > 0.01:
            scaled = pygame.transform.rotate(scaled, angle)

        if use_cache:
            self.world_image_cache[cache_key] = scaled
            if len(self.world_image_cache) > cache_limit:
                self.world_image_cache.pop(next(iter(self.world_image_cache)))
        return scaled
    def draw_world_sprite_shadow(self, image, world_pos, alpha, scale=1.0, angle=0.0, squash=0.34, stretch=1.08, screen_offset=(0, 0)):
        if image is None:
            return
        floor = self.camera.project(world_pos.x, world_pos.y)
        draw_scale = max(0.01, self.camera.zoom * scale * self.visual_depth_scale(world_pos))
        width = max(1, round(image.get_width() * draw_scale * stretch))
        height = max(1, round(image.get_height() * draw_scale))
        shadow = self.transform_sprite_shadow(image, width, height, angle, alpha, squash)
        center = (
            round(floor.x + screen_offset[0] * self.camera.zoom),
            round(floor.y + screen_offset[1] * self.camera.zoom),
        )
        rect = shadow.get_rect(center=center)
        if not rect.colliderect(pygame.Rect(-WORLD_CULL_MARGIN, -WORLD_CULL_MARGIN, SCREEN_WIDTH + WORLD_CULL_MARGIN * 2, SCREEN_HEIGHT + WORLD_CULL_MARGIN * 2)):
            return
        self.screen.blit(shadow, rect)
    def transform_sprite_shadow(self, image, width, height, angle, alpha, squash):
        profile = self.render_profile
        width = browser_bucket(width, bucket=8, maximum=900)
        height = browser_bucket(height, bucket=8, maximum=900)
        angle = 0 if abs(angle) <= 0.01 else round(angle / 5) * 5
        alpha = max(0, min(255, round(alpha)))
        squash_key = round(squash * 100)
        cache_key = (id(image), width, height, angle, alpha, squash_key, profile["fast_scale"])
        cached = self.sprite_shadow_cache.get(cache_key)
        if cached is not None:
            return cached

        scaler = pygame.transform.scale if WEB_BUILD and profile["fast_scale"] else pygame.transform.smoothscale
        shadow = scaler(image, (width, height))
        if abs(angle) > 0.01:
            shadow = pygame.transform.rotate(shadow, angle)
        shadow = shadow.copy()
        shadow.fill((0, 0, 0, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        squashed_height = max(1, round(shadow.get_height() * squash))
        shadow = scaler(shadow, (shadow.get_width(), squashed_height))

        self.sprite_shadow_cache[cache_key] = shadow
        if len(self.sprite_shadow_cache) > SPRITE_SHADOW_CACHE_LIMIT:
            self.sprite_shadow_cache.pop(next(iter(self.sprite_shadow_cache)))
        return shadow
    def draw_cave_floor(self):
        self.draw_static_cave_base()

        self.draw_leaf_connections()
        time = self.world_time
        art_pulse = 0.0 if self.story_beat_locked else self.mycelial_art_pulse_strength(time)

        for decal in self.leaf_decals:
            decal_pos = pygame.Vector2(decal.x, decal.z)
            if not self.world_visible(decal_pos, margin=360):
                continue
            screen = self.camera.project(decal.x, decal.z)
            progress = 1.0 if self.phase in ("feed_complete_focus", "concentrate_unlock", "feed_complete_return", *TRANSIT_UNLOCK_PHASES, "post_feed", "transit", "transit_select", "transit_disappear", "transit_pan", "transit_appear") else decal.feed_progress
            if progress > 0 and decal.mycelial_image:
                image = decal.mycelial_image.copy()
                image.set_alpha(round(min(1.0, progress) * 184))
                self.blit_world_image(image, decal_pos, screen_offset=(0, 4), cache=False)
                pulse_alpha = round(min(1.0, progress) * art_pulse * 34)
                if pulse_alpha > 0:
                    pulse_image = decal.mycelial_image.copy()
                    pulse_image.set_alpha(pulse_alpha)
                    pulse_image.fill((*MYCELIUM_FAINT, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    self.blit_world_image(pulse_image, decal_pos, screen_offset=(0, 4), cache=False)
            if progress > 0 or decal.connected:
                glow_size = round((440 + progress * 560) * self.camera.zoom)
                glow_alpha = round(20 + progress * 84)
                glow = make_radial_glow(glow_size, MYCELIUM_FAINT, glow_alpha, 2.05)
                self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
            self.blit_world_image(decal.image, decal_pos)

        if self.mycelial_overlay:
            overlay = None
            overlay_alpha = round(255 * self.mycelial_art_visibility)
            if overlay_alpha > 0:
                overlay = self.mycelial_overlay.copy()
                overlay.set_alpha(overlay_alpha)
            self.blit_world_image(overlay, self.spawn, cache=False)
            pulse_alpha = round(art_pulse * 38 * self.mycelial_art_visibility)
            if pulse_alpha > 0:
                pulse_overlay = self.mycelial_overlay.copy()
                pulse_overlay.set_alpha(pulse_alpha)
                pulse_overlay.fill((*MYCELIUM_FAINT, 255), special_flags=pygame.BLEND_RGBA_MULT)
                self.blit_world_image(pulse_overlay, self.spawn, cache=False)

        if self.puddle_image:
            self.blit_world_image(self.puddle_image, self.puddle_pos)
            self.draw_puddle_ripples()
        self.draw_stone_charge_glows()
        self.draw_pebble_waypoints()
        self.draw_concentrate_pebbles()
        self.draw_regen_colonies()
        self.draw_fern_fronds()
        self.draw_concentrate_rock()
        self.draw_channel_cover_leaves()
    def static_background_key(self):
        return (
            round(self.camera.x / BACKGROUND_CAMERA_BUCKET),
            round(self.camera.z / BACKGROUND_CAMERA_BUCKET),
            round(self.camera.zoom / BACKGROUND_ZOOM_BUCKET),
            bool(self.right_channel_active),
            round(self.right_channel_reveal / 0.08) if self.right_channel_active else 0,
        )
    def draw_static_cave_base(self):
        key = self.static_background_key()
        cached = self.background_cache.get(key)
        if cached is not None:
            self.screen.blit(cached, (0, 0))
            return

        layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.draw_static_cave_base_to(layer)
        self.background_cache[key] = layer
        if len(self.background_cache) > BACKGROUND_CACHE_LIMIT:
            self.background_cache.pop(next(iter(self.background_cache)))
        self.screen.blit(layer, (0, 0))
    def draw_static_cave_base_to(self, target):
        center = self.camera.project(0, 0)
        floor_rect = pygame.Rect(0, 0, CAVE_RADIUS * 2, round(CAVE_RADIUS * 2 * DEPTH_SCALE))
        floor_rect.center = (round(center.x), round(center.y))
        pygame.draw.ellipse(target, CAVE_FLOOR, floor_rect)

        self.draw_right_channel_bed(target)
        if self.right_channel_active:
            self.draw_right_water_channel(target)

        for pebble in self.edge_pebbles:
            self.blit_world_image(pebble.image, pygame.Vector2(pebble.x, pebble.z), target=target)

        for leaf in self.edge_leaves:
            self.blit_world_image(leaf.image, pygame.Vector2(leaf.x, leaf.z), target=target)
    def draw_mycelial_spawn(self, time):
        origin = self.camera.project(self.spawn.x, self.spawn.y)
        pulse = 0.5 + 0.5 * math.sin(time * 3.2)
        intro_pulse = self.intro_mycelial_pulse
        intro_peak = math.sin(intro_pulse * math.pi) if intro_pulse is not None else 0
        intro_visibility = self.intro_mycelial_visibility
        glow = make_radial_glow(
            420 + round(pulse * 50) + round(intro_peak * 80),
            MYCELIUM_FAINT,
            round((4 + round(pulse) + round(intro_peak * 9)) * intro_visibility),
            2.15,
        )
        self.screen.blit(glow, glow.get_rect(center=(round(origin.x), round(origin.y))))
    def draw_water_channel(self):
        start = pygame.Vector2(self.puddle_pos.x - 120, self.puddle_pos.y - 8)
        end = pygame.Vector2(-CAVE_RADIUS + 55, self.puddle_pos.y - 70)
        control = pygame.Vector2((self.puddle_pos.x - CAVE_RADIUS) * 0.5, self.puddle_pos.y - 44)
        points = self.make_bezier_world_points(start, control, end, 26)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.draw_organic_water_path(overlay, points, 34, time_offset=0.0, flow_speed=0.17, opacity=0.42)
        self.screen.blit(overlay, (0, 0))
    def right_channel_paths(self):
        start = pygame.Vector2(self.puddle_pos.x + 130, self.puddle_pos.y + 2)
        junction = pygame.Vector2(0, 0)
        branch_half_angle = math.radians(60)
        branch_direction = pygame.Vector2(math.cos(branch_half_angle), math.sin(branch_half_angle))
        branch_reach = CAVE_RADIUS * 0.88
        upper_end = pygame.Vector2(branch_direction.x, -branch_direction.y) * branch_reach
        lower_end = branch_direction * branch_reach
        upper_anchors = (
            junction,
            pygame.Vector2(145, -260),
            pygame.Vector2(310, -545),
            pygame.Vector2(upper_end.x - 78, upper_end.y + 74),
            upper_end,
        )
        lower_anchors = (
            junction,
            pygame.Vector2(162, 248),
            pygame.Vector2(330, 555),
            pygame.Vector2(lower_end.x - 92, lower_end.y - 68),
            lower_end,
        )
        return (
            junction,
            self.make_bezier_world_points(start, pygame.Vector2(-360, -24), junction, 34, wobble_strength=8.0),
            self.make_smooth_world_path(upper_anchors, 64),
            self.make_smooth_world_path(lower_anchors, 64),
        )
    def draw_right_channel_bed(self, target=None):
        target = target or self.screen
        junction, main, upper, lower = self.right_channel_paths()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.draw_dry_channel_path(overlay, main, 48, opacity=1.0, cap_end=False)
        self.draw_dry_channel_path(overlay, upper, 36, opacity=0.88, cap_start=False)
        self.draw_dry_channel_path(overlay, lower, 37, opacity=0.9, cap_start=False)
        self.draw_channel_junction_blend(overlay, junction, wet=False, strength=1.0)
        target.blit(overlay, (0, 0))
    def draw_right_water_channel(self, target=None):
        target = target or self.screen
        junction, main, upper, lower = self.right_channel_paths()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        reveal = smoothstep(self.right_channel_reveal)
        main_reveal = min(1.0, reveal / 0.56)
        branch_reveal = max(0.0, (reveal - 0.48) / 0.52)
        self.draw_organic_water_path(overlay, main, 34, time_offset=0.23, flow_speed=0.2, opacity=0.86, reveal=main_reveal, cap_end=False)
        self.draw_organic_water_path(overlay, upper, 24, time_offset=0.51, flow_speed=0.24, opacity=0.76, reveal=branch_reveal, cap_start=False)
        self.draw_organic_water_path(overlay, lower, 25, time_offset=0.71, flow_speed=0.22, opacity=0.78, reveal=branch_reveal, cap_start=False)

        junction_screen = self.camera.project(junction.x, junction.y)
        split_alpha = round(14 * max(0.0, min(1.0, (reveal - 0.42) / 0.28)))
        if split_alpha > 0:
            self.draw_channel_junction_blend(overlay, junction, wet=True, strength=max(0.0, min(1.0, (reveal - 0.38) / 0.32)))
            split_glow = make_radial_glow(round(190 * self.camera.zoom), WATER_CORE, split_alpha, 3.2)
            overlay.blit(split_glow, split_glow.get_rect(center=(round(junction_screen.x), round(junction_screen.y))))
        target.blit(overlay, (0, 0))
    def make_bezier_points(self, start, control, end, count):
        return [self.camera.project(world.x, world.y) for world in self.make_bezier_world_points(start, control, end, count)]
    def make_bezier_world_points(self, start, control, end, count, wobble_strength=8.0):
        points = []
        for i in range(count):
            t = i / max(1, count - 1)
            a = (1 - t) * (1 - t)
            b = 2 * (1 - t) * t
            c = t * t
            world = start * a + control * b + end * c
            broad_wobble = math.sin(t * math.tau * 1.4 + start.x * 0.013 + end.y * 0.009)
            fine_wobble = math.sin(t * math.tau * 3.1 + control.x * 0.011 - end.x * 0.004) * 0.38
            wobble = (broad_wobble + fine_wobble) * wobble_strength * math.sin(t * math.pi)
            tangent = (end - start)
            normal = pygame.Vector2(-tangent.y, tangent.x)
            if normal.length_squared() > 0:
                world += normal.normalize() * wobble
            points.append(world)
        return points
    def make_smooth_world_path(self, anchors, count):
        points = []
        if len(anchors) < 2:
            return [point.copy() for point in anchors]
        segment_count = len(anchors) - 1
        for i in range(count):
            travel = i / max(1, count - 1) * segment_count
            segment = min(segment_count - 1, int(travel))
            t = travel - segment
            p0 = anchors[max(0, segment - 1)]
            p1 = anchors[segment]
            p2 = anchors[segment + 1]
            p3 = anchors[min(len(anchors) - 1, segment + 2)]
            t2 = t * t
            t3 = t2 * t
            point = (p1 * 2 + (p2 - p0) * t + (p0 * 2 - p1 * 5 + p2 * 4 - p3) * t2 + (-p0 + p1 * 3 - p2 * 3 + p3) * t3) * 0.5
            points.append(point)
        return points
    def draw_organic_water_path(self, surface, world_points, width, time_offset=0.0, flow_speed=0.2, opacity=1.0, reveal=1.0, cap_start=True, cap_end=True):
        if len(world_points) < 2:
            return
        world_points = self.partial_world_polyline(world_points, reveal)
        if len(world_points) < 2:
            return
        points = [self.camera.project(point.x, point.y) for point in world_points]
        time = self.world_time
        zoom = self.camera.zoom

        self.draw_water_polyline(surface, points, width + 22, (18, 55, 62), 42, opacity, irregular=True, cap_start=cap_start, cap_end=cap_end)
        self.draw_water_polyline(surface, points, width + 12, (42, 116, 130), 54, opacity, irregular=True, cap_start=cap_start, cap_end=cap_end)
        self.draw_water_banks(surface, points, width, opacity)
        self.draw_water_polyline(surface, points, width + 3, (96, 190, 205), 72, opacity, irregular=True, cap_start=cap_start, cap_end=cap_end)
        self.draw_water_polyline(surface, points, width - 8, WATER, 58, opacity, irregular=True, cap_start=cap_start, cap_end=cap_end)
        self.draw_water_polyline(surface, points, max(3, width * 0.18), WATER_CORE, 38, opacity, shimmer=True, broken=True, cap_start=cap_start, cap_end=cap_end)

        for bead in range(9):
            t = (time * flow_speed + time_offset + bead / 7) % 1.0
            pos = self.point_on_world_polyline(world_points, t)
            ahead = self.point_on_world_polyline(world_points, min(1.0, t + 0.024))
            screen = self.camera.project(pos.x, pos.y)
            forward = self.camera.project(ahead.x, ahead.y) - screen
            if forward.length_squared() == 0:
                continue
            forward = forward.normalize()
            length = (12 + bead % 4 * 6) * zoom
            start = screen - forward * length * 0.35
            end = screen + forward * length * 0.65
            fade = math.sin(t * math.pi)
            pygame.draw.line(surface, (*WATER_CORE, round(44 * fade * opacity)), start, end, max(1, round(1.45 * zoom)))
    def draw_dry_channel_path(self, surface, world_points, width, opacity=1.0, cap_start=True, cap_end=True):
        if len(world_points) < 2:
            return
        points = [self.camera.project(point.x, point.y) for point in world_points]
        self.draw_water_polyline(surface, points, width + 14, (2, 4, 5), 26, opacity, irregular=True, cap_start=cap_start, cap_end=cap_end)
        self.draw_water_polyline(surface, points, width + 6, (13, 25, 27), 34, opacity, irregular=True, cap_start=cap_start, cap_end=cap_end)
        self.draw_water_polyline(surface, points, width - 4, (28, 47, 49), 24, opacity, irregular=True, cap_start=cap_start, cap_end=cap_end)
        self.draw_dry_channel_edges(surface, points, width, opacity)
    def draw_dry_channel_edges(self, surface, points, width, opacity):
        zoom = self.camera.zoom
        edge_offset = (width * 0.52 + 4) * zoom
        line_width = max(1, round(1.6 * zoom))
        for index, (p0, p1) in enumerate(zip(points, points[1:])):
            direction = p1 - p0
            if direction.length_squared() == 0:
                continue
            normal = pygame.Vector2(-direction.y, direction.x).normalize()
            alpha = round((24 + math.sin(index * 1.2) * 5) * opacity)
            for side in (-1, 1):
                pygame.draw.line(surface, (*CRACK, alpha), p0 + normal * edge_offset * side, p1 + normal * edge_offset * side, line_width)
    def draw_water_polyline(self, surface, points, width, color, alpha, opacity=1.0, shimmer=False, irregular=False, broken=False, cap_start=True, cap_end=True):
        time = self.world_time
        for index, (p0, p1) in enumerate(zip(points, points[1:])):
            wave = math.sin(index * 1.37 + time * 1.3) * (10 if shimmer else 5)
            if broken and math.sin(index * 1.9 + time * 2.4) < -0.15:
                continue
            width_wave = 1.0
            if irregular:
                width_wave += math.sin(index * 0.83 + time * 0.45) * 0.08
                width_wave += math.sin(index * 1.71 + 0.4) * 0.05
            line_width = max(1, round(width * width_wave * self.camera.zoom))
            segment_alpha = max(0, min(255, round((alpha + wave) * opacity)))
            pygame.draw.line(surface, (*color, segment_alpha), p0, p1, line_width)
            if not broken:
                joint_radius = max(1, line_width // 2)
                pygame.draw.circle(surface, (*color, segment_alpha), p0, joint_radius)
                pygame.draw.circle(surface, (*color, segment_alpha), p1, joint_radius)
        cap_radius = max(1, round(width * self.camera.zoom) // 2)
        if cap_start:
            pygame.draw.circle(surface, (*color, round(alpha * opacity * 0.55)), points[0], cap_radius)
        if cap_end:
            pygame.draw.circle(surface, (*color, round(alpha * opacity * 0.55)), points[-1], cap_radius)
    def draw_water_banks(self, surface, points, width, opacity):
        zoom = self.camera.zoom
        bank_width = max(1, round(2.0 * zoom))
        edge_offset = (width * 0.62 + 7) * zoom
        for index, (p0, p1) in enumerate(zip(points, points[1:])):
            direction = p1 - p0
            if direction.length_squared() == 0:
                continue
            normal = pygame.Vector2(-direction.y, direction.x).normalize()
            fade = 0.82 + 0.18 * math.sin(index * 0.9)
            alpha = round(26 * opacity * fade)
            for side in (-1, 1):
                a = p0 + normal * edge_offset * side
                b = p1 + normal * edge_offset * side
                pygame.draw.line(surface, (*WATER_DARK, alpha), a, b, bank_width)
    def draw_channel_junction_blend(self, surface, junction, wet=False, strength=1.0):
        center = self.camera.project(junction.x, junction.y)
        zoom = self.camera.zoom
        strength = max(0.0, min(1.0, strength))
        layers = (
            (130, 62, (12, 24, 26), 20),
            (92, 42, (31, 67, 75), 18),
        )
        if wet:
            layers = (
                (128, 60, (42, 116, 130), 20),
                (86, 38, (96, 190, 205), 18),
                (42, 18, WATER_CORE, 10),
            )
        for width, height, color, alpha in layers:
            rect = pygame.Rect(0, 0, round(width * zoom), round(height * zoom))
            rect.center = (round(center.x), round(center.y))
            pygame.draw.ellipse(surface, (*color, round(alpha * strength)), rect)
    def point_on_world_polyline(self, points, t):
        if len(points) == 1:
            return points[0].copy()
        lengths = []
        total = 0.0
        for p0, p1 in zip(points, points[1:]):
            length = p0.distance_to(p1)
            lengths.append(length)
            total += length
        if total <= 0:
            return points[0].copy()
        target = max(0.0, min(1.0, t)) * total
        walked = 0.0
        for index, length in enumerate(lengths):
            if walked + length >= target:
                local = max(0.0, min(1.0, (target - walked) / max(0.0001, length)))
                return points[index].lerp(points[index + 1], local)
            walked += length
        return points[-1].copy()
    def partial_world_polyline(self, points, reveal):
        reveal = max(0.0, min(1.0, reveal))
        if reveal <= 0 or len(points) < 2:
            return []
        if reveal >= 1:
            return points
        lengths = []
        total = 0.0
        for p0, p1 in zip(points, points[1:]):
            length = p0.distance_to(p1)
            lengths.append(length)
            total += length
        if total <= 0:
            return points[:1]
        target = total * reveal
        partial = [points[0]]
        walked = 0.0
        for index, length in enumerate(lengths):
            if walked + length < target:
                partial.append(points[index + 1])
                walked += length
                continue
            local = (target - walked) / max(0.0001, length)
            partial.append(points[index].lerp(points[index + 1], max(0.0, min(1.0, local))))
            break
        return partial
    def draw_moss_plug(self):
        center = self.camera.project(self.moss_spawn.x, self.moss_spawn.y)
        shapes = [
            (-18, -8, 64, 28, MOSS_GREEN, 110),
            (18, 4, 72, 34, MOSS_BROWN, 88),
            (0, 12, 88, 26, MOSS_GREEN, 78),
            (-42, 9, 44, 22, MOSS_BROWN, 70),
        ]
        for dx, dy, w, h, color, alpha in shapes:
            rect = pygame.Rect(0, 0, round(w * self.camera.zoom), round(h * self.camera.zoom))
            rect.center = (round(center.x + dx * self.camera.zoom), round(center.y + dy * self.camera.zoom))
            pygame.draw.ellipse(self.screen, (*color, alpha), rect)
    def draw_concentrate_rock(self):
        if self.concentrate_rock.lifted and not self.concentrate_rock.held:
            return
        lift = 0
        if self.concentrate_rock.held:
            lift = CONCENTRATE_ROCK_LIFT_HEIGHT + math.sin(self.concentrate_rock.sway_phase) * 6
        depth_scale = self.visual_depth_scale(self.concentrate_rock.pos)
        zoom = self.camera.zoom * depth_scale
        center = self.camera.project(self.concentrate_rock.pos.x, self.concentrate_rock.pos.y, lift)
        floor_center = self.camera.project(self.concentrate_rock.pos.x, self.concentrate_rock.pos.y)
        available = self.concentrate_rock_in_range and not self.concentrating
        sway_x = math.sin(self.concentrate_rock.sway_phase * 1.15) * (4 if self.concentrate_rock.held else 0)
        angle = math.sin(self.concentrate_rock.sway_phase * 0.72) * 22 if self.concentrate_rock.held else 0

        shadow_alpha = 78 if not self.concentrate_rock.held else 34
        if self.concentrate_rock_image:
            self.draw_world_sprite_shadow(self.concentrate_rock_image, self.concentrate_rock.pos, shadow_alpha, angle=angle, squash=0.32, stretch=1.08, screen_offset=(0, 8))
        else:
            shadow = pygame.Surface((126, 38), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, shadow_alpha), shadow.get_rect())
            shadow = pygame.transform.smoothscale(shadow, (round(126 * zoom), round(38 * zoom)))
            self.screen.blit(shadow, shadow.get_rect(center=(round(floor_center.x), round(floor_center.y + 8 * zoom))))

        if self.concentrate_rock.held or available:
            glow_size = round((230 if self.concentrate_rock.held else 160) * zoom)
            glow_alpha = 24 if self.concentrate_rock.held else 14
            glow = make_radial_glow(glow_size, MYCELIUM_FAINT, glow_alpha, 2.55)
            self.screen.blit(glow, glow.get_rect(center=(round(center.x), round(center.y))))

        if available:
            ring = make_elliptical_ring(round(148 * zoom), round(66 * zoom), round(12 * zoom), MYCELIUM_FAINT, 18)
            self.screen.blit(ring, ring.get_rect(center=(round(center.x), round(center.y - 10 * zoom))))

        if self.concentrate_rock_image:
            rock = self.concentrate_rock_image
            self.blit_world_image(rock, self.concentrate_rock.pos, lift, screen_offset=(sway_x, 0), angle=angle)
        else:
            pygame.draw.ellipse(self.screen, (94, 93, 86), pygame.Rect(0, 0, round(110 * zoom), round(62 * zoom)).move(round(center.x - 55 * zoom), round(center.y - 31 * zoom)))
    def draw_pebble_waypoints(self):
        if self.concentrate_mode != "pebble_select":
            return
        time = self.world_time
        waypoints = self.companion_waypoints if self.selected_waypoint_group == "companion" else self.pebble_waypoints
        for index, waypoint in enumerate(waypoints):
            if waypoint.occupied_by is not None or (waypoint.claimed_by is not None and waypoint.claimed_by != -1):
                continue
            screen = self.camera.project(waypoint.pos.x, waypoint.pos.y)
            selected = index == self.selected_waypoint
            pulse = 0.5 + 0.5 * math.sin(time * 4.0 + index)
            alpha = round((22 + pulse * 14) if not selected else (60 + pulse * 42))
            width = round((138 if not selected else 174) * self.camera.zoom)
            height = round(width * DEPTH_SCALE)
            ring = make_elliptical_ring(width, height, round(11 * self.camera.zoom), waypoint.color, alpha)
            self.screen.blit(ring, ring.get_rect(center=(round(screen.x), round(screen.y))))
            if selected:
                glow = make_radial_glow(round(260 * self.camera.zoom), waypoint.color, 46 + round(pulse * 24), 2.7)
                self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
    def draw_stone_charge_glows(self):
        if not self.pebble_waypoints or len(self.companion_waypoints) < len(self.pebble_waypoints) * 2:
            return
        time = self.world_time
        for index, primary in enumerate(self.pebble_waypoints):
            companions = self.companion_waypoints[index * 2 : index * 2 + 2]
            cluster = [primary, *companions]
            if not any(waypoint.occupied_by is not None or waypoint.visible_charge > 0.01 for waypoint in cluster):
                continue
            charge = sum(waypoint.visible_charge for waypoint in cluster) / len(cluster)
            if charge <= 0.01:
                continue
            center = sum((waypoint.pos for waypoint in cluster), pygame.Vector2()) / len(cluster)
            if not self.world_visible(center, margin=320):
                continue
            screen = self.camera.project(center.x, center.y)
            pulse = 0.5 + 0.5 * math.sin(time * 3.1 + index * 0.85)
            intensity = smoothstep(charge)
            zoom = self.camera.zoom * self.visual_depth_scale(center)
            glow_size = round((210 + 310 * intensity) * zoom)
            glow_alpha = min(255, round((18 + 82 * intensity) * (0.88 + pulse * 0.12) * 4))
            glow = make_radial_glow(glow_size, primary.color, glow_alpha, 2.5)
            self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
    def draw_companion_waypoints(self):
        if not self.npc_mushrooms:
            return
        time = self.world_time
        for index, waypoint in enumerate(self.companion_waypoints):
            if not self.world_visible(waypoint.pos, margin=240):
                continue
            screen = self.camera.project(waypoint.pos.x, waypoint.pos.y)
            pulse = 0.5 + 0.5 * math.sin(time * 3.3 + index * 0.5)
            if waypoint.occupied_by is None:
                alpha = 10 + round(pulse * 7)
                width = round(76 * self.camera.zoom)
            else:
                charge = waypoint.charge
                alpha = 22 + round(pulse * 12) + round(charge * 48)
                width = round((112 + charge * 72) * self.camera.zoom)
                glow = make_radial_glow(round((180 + charge * 210) * self.camera.zoom), waypoint.color, 16 + round(pulse * 10) + round(charge * 64), 2.85)
                self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
            height = round(width * DEPTH_SCALE)
            ring = make_elliptical_ring(width, height, max(3, round(8 * self.camera.zoom)), waypoint.color, alpha)
            self.screen.blit(ring, ring.get_rect(center=(round(screen.x), round(screen.y))))
    def draw_concentrate_pebbles(self):
        available_pebble = self.nearest_targetable_pebble
        selected_color = self.selected_primary_waypoint_color()
        for pebble in sorted(self.concentrate_pebbles, key=lambda item: item.pos.y):
            if not self.world_visible(pebble.pos, height=90 if pebble.held or pebble.moving else 0, margin=220):
                continue
            lift = 0
            settle = landing_factor(pebble.move_progress) if pebble.moving else 1.0
            if pebble.held or pebble.moving:
                lift = (CONCENTRATE_PEBBLE_LIFT_HEIGHT + math.sin(pebble.sway_phase) * 5) * settle
            if pebble.moving:
                lift += math.sin(pebble.move_progress * math.pi) * 82
            depth_scale = self.visual_depth_scale(pebble.pos)
            zoom = self.camera.zoom * depth_scale
            screen = self.camera.project(pebble.pos.x, pebble.pos.y, lift)
            available = available_pebble == pebble
            sway_x = math.sin(pebble.sway_phase * 1.1) * (4 if pebble.held or pebble.moving else 0) * settle
            angle = 0
            if pebble.moving:
                angle = math.sin(pebble.move_progress * math.pi) * 34 + math.sin(pebble.sway_phase * 0.65) * 5 * settle
            elif pebble.held:
                angle = math.sin(pebble.sway_phase * 0.75) * 18

            if pebble.held or pebble.moving:
                self.draw_world_sprite_shadow(pebble.image, pebble.pos, 42, angle=angle, squash=0.34, stretch=1.05, screen_offset=(0, 5))

            if pebble.held or pebble.moving or available:
                color = self.pebble_element_color(pebble) if pebble.target_waypoint is not None else selected_color if pebble.held or pebble.moving else MYCELIUM_FAINT
                glow_size = round((190 if pebble.held or pebble.moving else 130) * zoom)
                glow_alpha = 70 if pebble.held or pebble.moving else 13
                glow = make_radial_glow(glow_size, color, glow_alpha, 2.6)
                self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))

            if available:
                ring = make_elliptical_ring(round(118 * zoom), round(52 * zoom), round(10 * zoom), MYCELIUM_FAINT, 17)
                self.screen.blit(ring, ring.get_rect(center=(round(screen.x), round(screen.y - 8 * zoom))))

            stable_placed = pebble.placed and not pebble.moving and not pebble.held
            self.blit_world_image(
                pebble.image,
                pebble.pos,
                lift,
                screen_offset=(sway_x, 0),
                angle=angle,
                quantize=not stable_placed,
            )
    def draw_regen_colonies(self):
        for _, _, waypoint in self.all_stone_waypoints():
            if not waypoint.regen_offsets:
                continue
            for index, offset in enumerate(waypoint.regen_offsets):
                pos = waypoint.pos + offset
                if not self.world_visible(pos, height=24, margin=180):
                    continue
                height = 14
                sprite_scale = 0.86 + (index % 4) * 0.07
                if self.sprites.regen_sprites:
                    sprite_index = (round(abs(waypoint.pos.x) + abs(waypoint.pos.y)) + index * 3) % len(self.sprites.regen_sprites)
                    sprite = self.sprites.regen_sprites[sprite_index]
                    self.blit_world_image(sprite, pos, height, scale=sprite_scale)
                else:
                    screen = self.camera.project(pos.x, pos.y, height)
                    scale = self.camera.zoom * sprite_scale
                    stem = pygame.Rect(0, 0, max(4, round(12 * scale)), max(7, round(24 * scale)))
                    stem.midbottom = (round(screen.x), round(screen.y))
                    pygame.draw.ellipse(self.screen, (*STEM, 210), stem)
                    cap = pygame.Rect(0, 0, max(9, round(36 * scale)), max(6, round(19 * scale)))
                    cap.midbottom = (round(screen.x), stem.top + round(7 * scale))
                    pygame.draw.ellipse(self.screen, (*CAP, 176), cap)
                    pygame.draw.ellipse(self.screen, (*LUMEN_CORE, 58), cap.inflate(round(7 * scale), round(4 * scale)), 1)
    def draw_fern_fronds(self):
        time = self.world_time
        available_fern = self.nearest_targetable_fern
        for fern in sorted(self.fern_fronds, key=lambda item: item.pos.y):
            if not self.world_visible(fern.pos, height=90 if fern.held or fern.moving else 0, margin=220):
                continue
            lift = 0
            settle = landing_factor(fern.move_progress) if fern.moving else 1.0
            if fern.held or fern.moving:
                lift = (FERN_LIFT_HEIGHT + math.sin(fern.sway_phase) * 5) * settle
            if fern.moving:
                lift += math.sin(fern.move_progress * math.pi) * 70
            screen = self.camera.project(fern.pos.x, fern.pos.y, lift)
            floor = self.camera.project(fern.pos.x, fern.pos.y)
            if fern.placed:
                glow = make_radial_glow(round(180 * self.camera.zoom), MYCELIUM_FAINT, 18, 2.9)
                self.screen.blit(glow, glow.get_rect(center=(round(floor.x), round(floor.y))))
            if available_fern == fern:
                ring = make_elliptical_ring(round(150 * self.camera.zoom), round(66 * self.camera.zoom), round(10 * self.camera.zoom), MYCELIUM_FAINT, 18)
                self.screen.blit(ring, ring.get_rect(center=(round(screen.x), round(screen.y - 8 * self.camera.zoom))))
            if fern.held or fern.moving:
                angle = (
                    math.sin(fern.move_progress * math.pi) * 26 + math.sin(fern.sway_phase * 0.55) * 7 * settle
                    if fern.moving
                    else math.sin(fern.sway_phase * 0.55) * 7
                )
                pulse = 0.5 + 0.5 * math.sin(time * 4.0 + fern.id)
                glow = make_radial_glow(round(210 * self.camera.zoom), MYCELIUM_FAINT, 32 + round(pulse * 12), 2.65)
                self.screen.blit(glow, glow.get_rect(center=(round(screen.x), round(screen.y))))
                self.draw_world_sprite_shadow(fern.image, fern.pos, 36, angle=angle, squash=0.24, stretch=1.08, screen_offset=(0, 4))
            else:
                angle = 0
            self.blit_world_image(fern.image, fern.pos, lift, scale=1.0, angle=angle)
    def draw_puddle_ripples(self):
        for ripple in self.ripples:
            t = ripple.age / 1.6
            fade = max(0, 1 - t)
            center = self.camera.project(ripple.x, ripple.z)
            for offset in (0.0, 0.18, 0.34):
                rt = max(0, min(1, t - offset))
                if rt <= 0:
                    continue
                radius = (16 + rt * 92) * ripple.radius_scale
                width = round(radius * 2 * self.camera.zoom)
                height = round(radius * 2 * DEPTH_SCALE * self.camera.zoom)
                band = max(3, round(8 * self.camera.zoom))
                alpha = round(58 * fade * (1 - offset * 1.8))
                ring = make_elliptical_ring(width, height, band, WATER_CORE, alpha)
                self.screen.blit(ring, ring.get_rect(center=(round(center.x), round(center.y))))
    def draw_puddle_wet_rim(self):
        center = self.camera.project(self.puddle_pos.x, self.puddle_pos.y)
        zoom = self.camera.zoom
        for width, height, color, alpha in (
            (360, 176, (3, 5, 7), 54),
            (318, 142, WATER_DARK, 28),
        ):
            rect = pygame.Rect(0, 0, round(width * zoom), round(height * zoom))
            rect.center = (round(center.x), round(center.y + 4 * zoom))
            pygame.draw.ellipse(self.screen, (*color, alpha), rect)
    def draw_puddle_surface(self, time):
        center = self.camera.project(self.puddle_pos.x, self.puddle_pos.y)
        zoom = self.camera.zoom
        shimmer = 0.5 + 0.5 * math.sin(time * 1.8)
        glow = make_radial_glow(round(250 * zoom), WATER_CORE, round(12 + shimmer * 7), 2.4)
        self.screen.blit(glow, glow.get_rect(center=(round(center.x - 8 * zoom), round(center.y - 3 * zoom))))
        glints = (
            (-58, -18, 72, 0.0),
            (24, -10, 96, 0.7),
            (-18, 12, 54, 1.4),
        )
        for x, y, length, phase in glints:
            drift = math.sin(time * 0.85 + phase) * 5 * zoom
            start = pygame.Vector2(center.x + (x - length * 0.5) * zoom + drift, center.y + y * zoom)
            end = pygame.Vector2(center.x + (x + length * 0.5) * zoom + drift, center.y + (y + 2) * zoom)
            alpha = round(18 + shimmer * 12)
            pygame.draw.aaline(self.screen, (*WATER_CORE, alpha), start, end)
    def draw_water_drop(self):
        if not self.drop_active:
            return
        impact_world = self.puddle_pos + self.puddle_drop_offset
        impact = self.camera.project(impact_world.x, impact_world.y, 8)
        start = impact + pygame.Vector2(0, -255 * self.camera.zoom)
        t = max(0, min(1, self.drop_progress))
        y = start.y + (impact.y - start.y) * (t * t)
        x = impact.x + math.sin(t * math.pi * 2) * 1.5
        top = pygame.Vector2(x, max(start.y, y - 20 * self.camera.zoom))
        bottom = pygame.Vector2(x, y)
        pygame.draw.aaline(self.screen, (*WATER_CORE, 120), top, bottom)
        pygame.draw.circle(self.screen, (*WATER_CORE, 120), bottom, max(1, round(2 * self.camera.zoom)))
    def draw_leaf_connections(self):
        return
    def draw_darkness_overlay(self, time):
        if self.render_profile["disable_darkness"]:
            return
        if self.story_beat_locked:
            self.draw_story_beat_darkness(time)
            return

        darkness = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        darkness.fill((*DARKNESS, 111))

        player_screen = self.camera.project(self.player.pos.x, self.player.pos.y, self.player.height + self.player.terrain_lift)
        player_luminosity = self.intro_mushroom_luminosity if not self.intro_complete else self.player_transit_visibility
        player_strength = round((96 + self.growth_state * 36) * player_luminosity * 0.5)
        if player_strength > 0:
            self.cut_light(darkness, player_screen, 330 + self.growth_state * 42, player_strength, 2.8)

        mushroom_intro = self.intro_mushroom_pulse
        if mushroom_intro is not None:
            intro_peak = math.sin(mushroom_intro * math.pi)
            self.cut_light(darkness, player_screen, 210 + round(intro_peak * 80), round(68 * intro_peak), 2.9)

        spawn_screen = self.camera.project(self.spawn.x, self.spawn.y)
        spawn_pulse = 0.5 + 0.5 * math.sin(time * 3.2)
        spawn_strength = round(128 * self.post_intro_reveal)
        if spawn_strength > 0:
            self.cut_light(darkness, spawn_screen, 500 + round(spawn_pulse * 45), spawn_strength, 3.0)
        mycelial_intro = self.intro_mycelial_pulse
        if mycelial_intro is not None:
            intro_peak = math.sin(mycelial_intro * math.pi)
            self.cut_light(darkness, spawn_screen, 300 + round(intro_peak * 160), round(92 * intro_peak), 2.9)

        if not self.intro_complete:
            self.screen.blit(darkness, (0, 0))
            return

        if 0 < len(self.npc_mushrooms) <= 2:
            for npc in self.npc_mushrooms[:2]:
                visibility = smoothstep(min(1.0, npc.spawn_age / NPC_GROW_SECONDS))
                if npc.transit_phase == "shrink":
                    visibility *= max(0.0, 1.0 - smoothstep(min(1.0, npc.transit_time / NPC_TRANSIT_SHRINK_SECONDS)))
                elif npc.transit_phase == "grow":
                    visibility *= smoothstep(min(1.0, npc.transit_time / NPC_TRANSIT_GROW_SECONDS))
                strength = round(100 * visibility)
                if strength > 0:
                    self.cut_light(darkness, self.camera.project(npc.pos.x, npc.pos.y, npc.terrain_lift), 200, strength, 2.9)

        if self.lumen_count >= REQUIRED_LUMEN:
            charge_pulse = 0.5 + 0.5 * math.sin(time * 4.5)
            ready_fade = self.mycelial_lumen_ready_fade
            self.cut_light(darkness, spawn_screen, 470 + round(charge_pulse * 80), round(150 * ready_fade), 2.85)

        if self.phase == "concentrate_unlock":
            self.cut_light(darkness, spawn_screen, 560, 145, 2.85)
        if self.phase == "transit_unlock":
            self.cut_light(darkness, spawn_screen, 640, 170, 2.85)
        if self.collect_pebbles_02_complete:
            self.cut_light(darkness, spawn_screen, 760, 210, 2.85)
        if self.concentrate_unlocked or self.concentrate_rock.lifted:
            rock_screen = self.camera.project(self.concentrate_rock.pos.x, self.concentrate_rock.pos.y, CONCENTRATE_ROCK_LIFT_HEIGHT if self.concentrate_rock.held else 0)
            rock_strength = 78 if self.concentrate_rock.held else 42
            self.cut_light(darkness, rock_screen, 200, rock_strength, 2.9)
        if self.phase == "transit_select":
            if self.transit_destinations:
                pos = self.transit_destinations[self.selected_transit_destination]
                self.cut_light(darkness, self.camera.project(pos.x, pos.y), 240, 70, 2.95)
        if self.phase in ("transit_disappear", "transit_pan", "transit_appear"):
            transit_pulse = 0.5 + 0.5 * math.sin(time * 5.0)
            if self.transit_origin is not None:
                origin_screen = self.camera.project(self.transit_origin.x, self.transit_origin.y)
                origin_visibility = 1.0
                if self.phase == "transit_disappear":
                    origin_visibility = 1.0 - smoothstep(min(1.0, self.transit_time / TRANSIT_SHRINK_SECONDS))
                elif self.phase in ("transit_pan", "transit_appear"):
                    origin_visibility = 0.0
                if origin_visibility > 0:
                    self.cut_light(darkness, origin_screen, 360 + round(transit_pulse * 70), round(122 * origin_visibility), 2.75)
            if self.transit_target is not None:
                target_screen = self.camera.project(self.transit_target.x, self.transit_target.y)
                target_visibility = 0.0
                if self.phase == "transit_appear":
                    t = min(1.0, self.transit_time / TRANSIT_GROW_SECONDS)
                    target_visibility = math.sin(t * math.pi) * 0.52
                if target_visibility > 0:
                    self.cut_light(darkness, target_screen, 360 + round(transit_pulse * 58), round(104 * target_visibility), 2.75)
        for spell in self.elemental_spells:
            if spell.delay > 0:
                continue
            fade = max(0.0, 1.0 - spell.age / SPELL_LIFETIME)
            self.cut_light(darkness, self.camera.project(spell.pos.x, spell.pos.y, 62), round(190 * spell.size_scale * fade), round(92 * fade), 2.35)

        self.screen.blit(darkness, (0, 0))
    def draw_story_beat_darkness(self, time):
        darkness = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        darkness.fill((*DARKNESS, 108))

        player_screen = self.camera.project(self.player.pos.x, self.player.pos.y, self.player.height + self.player.terrain_lift)
        player_luminosity = self.intro_mushroom_luminosity if not self.intro_complete else self.player_transit_visibility
        player_strength = round((78 + self.growth_state * 24) * player_luminosity)
        if player_strength > 0:
            self.cut_light(darkness, player_screen, 300 + self.growth_state * 28, player_strength, 2.8)

        spawn_screen = self.camera.project(self.spawn.x, self.spawn.y)
        pulse = 0.5 + 0.5 * math.sin(time * 2.4)
        center_strength = 118 + round(pulse * 24)
        center_radius = 560
        if self.phase in TRANSIT_UNLOCK_PHASES:
            center_strength = 138 + round(pulse * 22)
            center_radius = 640
        self.cut_light(darkness, spawn_screen, center_radius, center_strength, 2.85)
        self.screen.blit(darkness, (0, 0))
    def cut_light(self, darkness, center, radius, strength, falloff_power):
        mask = self.make_reveal_mask(radius, strength, falloff_power)
        darkness.blit(mask, mask.get_rect(center=(round(center.x), round(center.y))), special_flags=pygame.BLEND_RGBA_SUB)
    def make_reveal_mask(self, radius, strength, falloff_power):
        radius = max(4, browser_bucket(radius, maximum=BROWSER_MAX_REVEAL_RADIUS))
        cache_key = (radius, strength, falloff_power)
        if cache_key in self.reveal_cache:
            return self.reveal_cache[cache_key]

        size = radius * 2
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        for current in range(radius, 0, -1):
            t = current / radius
            smooth = 1 - (t * t * (3 - 2 * t))
            alpha = round(strength * (smooth ** falloff_power))
            if alpha <= 0:
                continue
            rect = pygame.Rect(0, 0, current * 2, current * 2)
            rect.center = (radius, radius)
            pygame.draw.ellipse(mask, (255, 255, 255, alpha), rect)

        self.reveal_cache[cache_key] = mask
        return mask
    def draw_hud(self):
        lines = [
            f"Lumen: {self.lumen_count} / {REQUIRED_LUMEN}",
            f"Beat: {self.phase.title()}",
            "WASD/arrows move  Space concentrate  Enter options  C cheat advance  R restart  Esc quit",
        ]
        if self.cinematic_locked:
            lines.insert(2, "Cinematic: controls paused. Press Space, C, or click to skip.")
        if self.phase == "explore" and self.lumen_count >= REQUIRED_LUMEN:
            percent = round(self.charge_progress * 100)
            lines.insert(2, f"Return to the mycelial center: charging {percent}%")
        elif self.phase == "feed":
            lines.insert(2, "The mycelium is charged. Next beat unlocked: Feed.")

        y = 18
        for index, line in enumerate(lines):
            font = self.font if index < 2 else self.small_font
            color = QUEST if "Feed" in line or "charging" in line else TEXT
            image = font.render(line, True, color)
            self.screen.blit(image, (22, y))
            y += image.get_height() + 8
    def draw_auto_guide_ui(self):
        self.auto_guide_prompt_rect = pygame.Rect(0, 0, 0, 0)
        self.auto_guide_start_rect = pygame.Rect(0, 0, 0, 0)
        self.auto_guide_dismiss_rect = pygame.Rect(0, 0, 0, 0)
        if self.auto_guide_enabled:
            return
        fade = max(0.0, min(1.0, self.auto_guide_prompt_fade))
        if fade <= 0:
            return
        fade = fade * fade * (3 - 2 * fade)

        countdown = max(0, math.ceil(self.auto_guide_prompt_time))
        start_label = f"Yes ({countdown})" if self.auto_guide_prompt_countdown_active else "Yes"
        start_text = self.small_font.render(start_label, True, TEXT)
        dismiss_text = self.small_font.render("No", True, TEXT)
        width = 380
        height = 126
        player_screen = self.camera.project(self.player.pos.x, self.player.pos.y, self.player.height + 100)
        x = round(player_screen.x - width * 0.5)
        y = round(player_screen.y - height * 0.5)
        x = max(18, min(SCREEN_WIDTH - width - 18, x))
        y = max(18, min(SCREEN_HEIGHT - height - 18, y))
        self.auto_guide_prompt_rect = pygame.Rect(x, y, width, height)

        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((6, 10, 12, 246))
        pygame.draw.rect(panel, (92, 70, 38), panel.get_rect(), 1)
        pygame.draw.rect(panel, (*MYCELIUM, 80), panel.get_rect().inflate(-6, -6), 1)
        self.draw_branded_menu_title(panel, "AUTO PLAY", width // 2, 31)
        pygame.draw.line(panel, (92, 70, 38), (24, 58), (width - 24, 58), 1)

        button_y = height - 50
        start_rect = pygame.Rect((width - 250) // 2, button_y, 118, 34)
        dismiss_rect = pygame.Rect(start_rect.right + 14, button_y, 118, 34)
        for index, (rect, text, primary) in enumerate(((start_rect, start_text, True), (dismiss_rect, dismiss_text, False))):
            selected = index == self.auto_guide_prompt_selected
            fill = (9, 44, 58, 238) if selected else (10, 16, 17, 224)
            border = MYCELIUM if selected else MYCELIUM_FAINT
            pygame.draw.rect(panel, fill, rect)
            pygame.draw.rect(panel, border, rect, 2 if selected else 1)
            if selected:
                pygame.draw.rect(panel, (*MYCELIUM, 48), rect.inflate(-6, -6), 1)
            panel.blit(text, text.get_rect(center=rect.center))
        panel.set_alpha(round(255 * fade))
        self.screen.blit(panel, self.auto_guide_prompt_rect)
        self.auto_guide_start_rect = start_rect.move(x, y)
        self.auto_guide_dismiss_rect = dismiss_rect.move(x, y)
    def draw_debug_overlay(self):
        if not self.debug_overlay:
            return
        fps = self.clock.get_fps()
        frame_ms = self.last_dt * 1000
        target_fps = self.browser_fps_cap
        budget_ms = 1000 / max(1, target_fps)
        timing_color = (255, 150, 120) if frame_ms > budget_ms * 1.15 else TEXT
        lines = [
            (f"fps {fps:5.1f}/{target_fps}  dt {frame_ms:5.1f}/{budget_ms:4.1f}ms", timing_color),
            (f"profile {self.render_profile['name']}  quality {self.visual_quality}", TEXT),
            (f"cache world {len(self.world_image_cache)}  bg {len(self.background_cache)}", TEXT),
            (f"drawn {self.debug_draw_count}  phase {self.phase}", TEXT),
            (f"player {self.player.pos.x:5.0f},{self.player.pos.y:5.0f}  zoom {self.camera.zoom:.2f}", TEXT),
            (f"auto {self.auto_guide_debug_state()}", TEXT),
        ]
        if self.last_mouse_debug_time > 0:
            lines.append((self.last_mouse_debug, TEXT))
        padding = 10
        rendered = [self.small_font.render(line, True, color) for line, color in lines]
        width = max(image.get_width() for image in rendered) + padding * 2
        height = sum(image.get_height() for image in rendered) + padding * 2 + 6 * (len(rendered) - 1)
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        panel_x = 18
        panel_y = SCREEN_HEIGHT - height - 18
        self.screen.blit(panel, (panel_x, panel_y))
        y = panel_y + padding
        for image in rendered:
            self.screen.blit(image, (panel_x + padding, y))
            y += image.get_height() + 6
    def draw_options_ui(self):
        if self.title_screen and not self.options_open and self.options_fade <= 0:
            self.options_button_rect = pygame.Rect(0, 0, 0, 0)
            self.options_row_rects = []
            return
        button_width = 42
        button_height = 42
        self.options_button_rect = pygame.Rect(SCREEN_WIDTH - button_width - 18, 18, button_width, button_height)
        if not self.title_screen:
            button = pygame.Surface((button_width, button_height), pygame.SRCALPHA)
            button.fill((10, 18, 20, 218))
            pygame.draw.rect(button, MYCELIUM_FAINT, button.get_rect(), 1)
            if self.options_gear_icon is not None:
                button.blit(self.options_gear_icon, self.options_gear_icon.get_rect(center=button.get_rect().center))
            else:
                fallback = self.small_font.render("O", True, TEXT)
                button.blit(fallback, fallback.get_rect(center=button.get_rect().center))
            self.screen.blit(button, self.options_button_rect)

        self.options_row_rects = []
        fade = max(0.0, min(1.0, self.options_fade))
        if fade <= 0:
            return
        fade = fade * fade * (3 - 2 * fade)

        rows = self.options_rows()
        self.options_selected = self.valid_option_index(self.options_selected)
        option_row_height = 28 if SCREEN_HEIGHT <= 600 else 40
        section_row_height = 20 if SCREEN_HEIGHT <= 600 else 28
        padding = 14 if SCREEN_HEIGHT <= 600 else 28
        tooltip_height = self.small_font.get_height() * 2 + (18 if SCREEN_HEIGHT <= 600 else 28)
        row_heights = [section_row_height if self.is_section_option(label) else option_row_height for label in rows]
        panel_width = min(SCREEN_WIDTH - 64, 680 if WEB_BUILD else 560)
        warning_height = 0
        header_height = 48 if SCREEN_HEIGHT <= 600 else 56
        panel_height = padding * 2 + header_height + sum(row_heights) + warning_height + tooltip_height
        if panel_height > SCREEN_HEIGHT - 28:
            excess = panel_height - (SCREEN_HEIGHT - 28)
            shrink = math.ceil(excess / max(1, len(rows)))
            option_row_height = max(24, option_row_height - shrink)
            section_row_height = max(18, section_row_height - shrink)
            row_heights = [section_row_height if self.is_section_option(label) else option_row_height for label in rows]
            panel_height = padding * 2 + header_height + sum(row_heights) + warning_height + tooltip_height
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = (SCREEN_HEIGHT - panel_height) // 2
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((6, 10, 12, 246))
        self.draw_wood_grain_panel_border(panel)
        self.draw_panel_corner_ornaments(panel)

        self.draw_branded_menu_title(panel, "OPTIONS", panel_width // 2, padding + 20)
        pygame.draw.line(panel, WOOD_GRAIN_LIGHT, (padding + 12, padding + 46), (panel_width - padding - 12, padding + 46), 1)
        y = padding + header_height
        for index, label in enumerate(rows):
            current_row_height = row_heights[index]
            row_rect = pygame.Rect(panel_x + padding, panel_y + y, panel_width - padding * 2, current_row_height - 4)
            self.options_row_rects.append(row_rect if self.options_open else pygame.Rect(0, 0, 0, 0))
            local_rect = pygame.Rect(padding, y, panel_width - padding * 2, current_row_height - 4)
            is_section = self.is_section_option(label)
            selected = index == self.options_selected and not is_section
            if selected:
                pygame.draw.rect(panel, (9, 44, 58, 232), local_rect)
                pygame.draw.rect(panel, MYCELIUM, local_rect, 2)
                pygame.draw.rect(panel, (*MYCELIUM, 46), local_rect.inflate(-6, -6), 1)
            if is_section:
                if label:
                    label_image = self.small_font.render(label, True, (248, 206, 122))
                    panel.blit(label_image, (padding + 10, y + max(1, (current_row_height - label_image.get_height()) // 2)))
                    line_x = padding + 92
                else:
                    line_x = padding + 10
                pygame.draw.line(panel, (92, 70, 38), (line_x, y + current_row_height // 2), (panel_width - padding - 10, y + current_row_height // 2), 1)
                y += current_row_height
                continue
            label_color = TEXT if selected else (218, 194, 137)
            label_image = self.small_font.render(label, True, label_color)
            value_text = self.option_display_value(label)
            value_image = self.small_font.render(value_text, True, MYCELIUM if selected else TEXT)
            indent = 28 if label not in ("End Game", "Close") else 10
            text_y = y + max(1, (current_row_height - label_image.get_height()) // 2)
            panel.blit(label_image, (padding + indent, text_y))
            if value_text:
                panel.blit(value_image, (panel_width - padding - value_image.get_width() - 10, y + max(1, (current_row_height - value_image.get_height()) // 2)))
            y += current_row_height

        tooltip = self.option_tooltip(rows[self.options_selected])
        if tooltip != self.options_tooltip_text:
            self.options_tooltip_previous = self.options_tooltip_text
            self.options_tooltip_text = tooltip
            self.options_tooltip_fade = 0.0
        tooltip_width = panel_width - padding * 2 - 20
        tip_y = panel_height - tooltip_height + 8
        pygame.draw.line(panel, (*MYCELIUM, 80), (padding + 10, tip_y - 7), (panel_width - padding - 10, tip_y - 7), 1)
        tooltip_fade = max(0.0, min(1.0, self.options_tooltip_fade))
        tooltip_fade = tooltip_fade * tooltip_fade * (3 - 2 * tooltip_fade)
        for text, alpha in ((self.options_tooltip_previous, round(255 * (1 - tooltip_fade))), (self.options_tooltip_text, round(255 * tooltip_fade))):
            if not text or alpha <= 0:
                continue
            line_y = tip_y
            for line in self.wrap_text(text, self.small_font, tooltip_width)[:2]:
                tip_image = self.small_font.render(line, True, MYCELIUM)
                tip_image.set_alpha(alpha)
                panel.blit(tip_image, tip_image.get_rect(centerx=panel_width // 2, y=line_y))
                line_y += tip_image.get_height() + 3

        panel.set_alpha(round(255 * fade))
        self.screen.blit(panel, (panel_x, panel_y))
