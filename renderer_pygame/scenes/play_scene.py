from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from renderer_pygame.common.animations import jiggle_and_slow
from renderer_pygame.common.dice import make_pg_dice, int_to_dice_values
from renderer_pygame.common.fan import get_fan_positions

if TYPE_CHECKING:
    from models.actions.base import Action
    from renderer_pygame.game import Game

import pygame as pg

from engine import Engine
from game_state import GameState
from models.game_card import GameCard
from models.utils import flip
from renderer_pygame.scenes.scene_abc import Scene

BASIC_LANDS = {'forest', 'island', 'mountain', 'plains', 'swamp'}
CARD_W = 100
CARD_H = 142
CARD_BACK_IMG = pg.image.load(Path("renderer_pygame/assets/card_back.jpg"))

@dataclass
class PGCard:
    card: GameCard
    surf: pg.Surface
    index: int
    rect: pg.Rect = None
    hovered: bool = False
    selected: bool = False
    back_surf: pg.Surface = CARD_BACK_IMG

    def __post_init__(self):
        self.surf = pg.transform.smoothscale(self.surf, (CARD_W, CARD_H))
        self.back_surf = self.back_surf.convert_alpha()
        self.back_surf = pg.transform.smoothscale(self.back_surf, (CARD_W, CARD_H))

@dataclass
class ActionRenderInfo:
    action: Action
    rect: pg.Rect
    index: int
    hovered: bool = False

@dataclass(frozen=True)
class RecentEventRow:
    p_idx: int
    event_text: str
    rect: pg.Rect
    index: int

    @property
    def display_text(self) -> str:
        if self.p_idx is not None:
            return f'P{self.p_idx}: ' + (self.event_text or '')
        return self.event_text

class PlayScene(Scene):
    def __init__(self, game: Game, engine):
        super().__init__(game)
        self.engine: Engine = engine
        self.state: GameState = self.engine.gs
        self.font = pg.font.SysFont("arial", 48)
        self.small_font = pg.font.SysFont("arial", 12)
        self.mouse_pos = 0, 0

        # grid 12 units (125 pixels each) wide by 9 units (100 pixels each) tall
        self.cols = {i: i * 125 + self.game.gutter for i in range(12)}
        self.rows = {i: i * 150 + self.game.gutter for i in range(6)}
        self.combat_y_offset = 150
        self.seen_on_battlefield = {'attackers': 0, 'non_basics': 0} | {slug: 0 for slug in BASIC_LANDS}

        self.hovered_card = None
        self.selected_card = None

        self.p_idx = 0

        self.dice: dict[int: pg.Surface] = {i: make_pg_dice(40, 40, i) for i in range(1, 7)}
        self.life_shake_timer = [0.0 for _ in self.state.life]
        self.life_shake_duration = 0.5

        self.available_actions = []
        self.action_layout: list[ActionRenderInfo] = []
        self.recent_actions: list[RecentEventRow] = []  # game history
        self.pending_action = None

        self.prev_state = {'life': self.state.life.copy()}

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_m:
                    self.game.scenes.set_scene("menu", use_fade=True)
                elif event.key == pg.K_q:
                    self.game.running = False
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click
                    self.handle_action_click(event.pos)

    def update(self, dt):
        self.available_actions = self.state.get_available_actions(self.state.action_on_idx)
        self.build_action_layout(self.cols[10], self.rows[0])
        self.build_recent_actions_layout(self.cols[10], self.rows[3])
        self.update_action_hover()

        for p_idx in (0, 1):
            if self.prev_state['life'][p_idx] != self.state.life[p_idx]:
                self.life_shake_timer[p_idx] = self.life_shake_duration

        # decrement shake timers
        for p_idx in range(len(self.life_shake_timer)):
            if self.life_shake_timer[p_idx] > 0:
                self.life_shake_timer[p_idx] -= dt  # dt = time since last frame in seconds
                if self.life_shake_timer[p_idx] < 0:
                    self.life_shake_timer[p_idx] = 0

        self.prev_state['life'] = self.state.life.copy()

    def update_action_hover(self):
        mouse_pos = pg.mouse.get_pos()
        self.hovered_card = None

        for info in self.action_layout:
            info.hovered = info.rect.collidepoint(mouse_pos)

    def draw(self):
        screen = self.game.screen
        screen.fill((30, 100, 30))  # green felt table

        self.draw_player_area(flip(self.p_idx), top=True)
        self.draw_player_area(self.p_idx, top=False)
        # self.draw_stack(state)  # skipping this for now; would probably want to use gs.action_stack
        self.draw_action_panel(self.cols[10], self.rows[0])
        self.draw_recent_actions(self.cols[10], self.rows[3])
        self.draw_hover_preview(self.cols[10], self.rows[4])

    def handle_action_click(self, mouse_pos):
        for info in self.action_layout:
            if info.rect.collidepoint(mouse_pos):
                # This is the clicked action
                self.pending_action = info.action
                print(f"Clicked action: {info.action}")

                # Execute immediately like the console
                info.action.play()
                self.state.game_history.append_action(info.action, self.state)

                break

    def draw_player_area(self, p_idx: int, top: bool):
        self.draw_dice(p_idx, self.cols[0], self.rows[1] if top else self.rows[4])
        self.draw_library(p_idx, self.cols[1], self.rows[1] if top else self.rows[4])
        self.draw_graveyard(p_idx, self.cols[1], self.rows[0] if top else self.rows[5])
        self.draw_exile(p_idx, self.cols[0], self.rows[0] if top else self.rows[5])
        self.draw_battlefield(p_idx, 2, 1 if top else 4)
        self.draw_hand(p_idx, 2, 0 if top else 5, top)

    def draw_dice(self, p_idx: int, x: int, y: int):
        # draw dice in a 2-wide by 3-tall (max) configuration
        dice_values = int_to_dice_values(self.state.life[p_idx])
        x += 5  # the dice are slightly too far left

        shaking = self.life_shake_timer[p_idx] > 0
        for i, value in enumerate(dice_values):
            die_x = x + (50 * (i % 2))
            die_y = y + (50 * (i // 2))
            if shaking:
                die_x, die_y = jiggle_and_slow(die_x, die_y, 6, self.life_shake_timer[p_idx] / self.life_shake_duration)
            self.game.screen.blit(self.dice[value], (die_x, die_y))

    def draw_hand(self, p_idx: int, col: int, row: int, face_down: bool):
        mouse_pos = pg.mouse.get_pos()
        cards = self.state.hands[p_idx].cards
        if not len(cards):
            return

        # arc/fan parameters
        center_x = self.cols[col + 3]  # shift right for centering
        center_y = self.rows[row] + 200  # below cards
        radius = 300
        angle_spread = min(60, 10 * len(cards))  # dynamic spread

        positions = get_fan_positions(len(cards), center_x, center_y, radius, angle_spread)

        for i, (card, (x, y, angle)) in enumerate(zip(cards, positions)):
            first_image_surf = next(iter(self.game.images[card.props.slug].values()))
            pg_card = PGCard(card, first_image_surf, i)
            self.draw_card(pg_card, int(x), int(y), face_down=face_down, rotation_angle=angle)

            if not face_down and pg_card.rect.collidepoint(mouse_pos):
                self.hovered_card = pg_card

    def draw_battlefield(self, p_id: int, col: int, row: int):
        """Lands stacked & staggered by slug on left; attackers promoted to middle, else rest of piles start on right"""
        # TODO: marry-up blockers to their attackers
        mouse_pos = pg.mouse.get_pos()
        top = True if p_id != self.p_idx else False

        attackers = self.state.card_filter.attackers().result()
        seen = self.seen_on_battlefield.copy()
        basic_lands_seen = []

        for i, c in enumerate(self.state.boards[p_id]):
            first_image_surf = next(iter(self.game.images[c.props.slug].values()))
            pg_card = PGCard(c, first_image_surf, i)

            if c in attackers:
                x = self.cols[col + seen['attackers']]
                y = self.rows[row + 1] if top else self.rows[row - 1]
                seen['attackers'] += 1
            elif c.props.slug in BASIC_LANDS:
                slug = c.props.slug
                if slug not in basic_lands_seen:
                    basic_lands_seen.append(slug)
                x = self.cols[col + basic_lands_seen.index(slug)] + (seen[slug] * 2)
                y = self.rows[row] + (seen[slug] * -10)
                seen[slug] += 1
            else:
                x = self.cols[8 - seen['non_basics']]
                y = self.rows[row]
                seen['non_basics'] += 1
            self.draw_card(pg_card, x, y, is_tapped=c.is_tapped)

            if pg_card.rect.collidepoint(mouse_pos):
                self.hovered_card = pg_card

    def draw_graveyard(self, p_idx: int, x: int, y: int):
        if not self.state.graveyards[p_idx]:
            rect = pg.Rect(x, y, CARD_W, CARD_H)
            pg.draw.rect(self.game.screen, (120, 120, 120), rect)
            return

        top_card = self.state.graveyards[p_idx][-1]
        first_image_surf = next(iter(self.game.images[top_card.props.slug].values()))
        pg_card = PGCard(top_card, first_image_surf, 0)
        self.draw_card(pg_card, x, y)

    def draw_exile(self, p_idx: int, x, y):
        if not self.state.exiles[p_idx]:
            return

        top_card = self.state.exiles[p_idx][-1]
        first_image_surf = next(iter(self.game.images[top_card.props.slug].values()))
        pg_card = PGCard(top_card, first_image_surf, 0)
        self.draw_card(pg_card, x, y, is_tapped=True)

    def draw_library(self, p_id: int, x: int, y: int):
        card_cnt = len(self.state.libraries[p_id].cards)
        if not card_cnt:
            return
        card_back_surf = pg.transform.smoothscale(CARD_BACK_IMG, (CARD_W, CARD_H))
        self.game.screen.blit(card_back_surf, (x, y))
        card_cnt_text = self.small_font.render(str(card_cnt), True, (200, 200, 200))
        self.game.screen.blit(card_cnt_text, (x + 5, y + 5))

    def draw_card(self, card: PGCard, x: int, y: int, width=CARD_W, height=CARD_H,
                  face_down: bool = False, is_tapped: bool = False, rotation_angle: int = 0):
        """Draws a card at the given position (x, y) with the given width/height. Rotated 90 degrees if is_rotated."""
        card.rect = pg.Rect(x, y, width, height)
        screen = self.game.screen

        card_surf = card.surf if not face_down else card.back_surf
        card_surf = pg.transform.smoothscale(card_surf, (width, height))

        if is_tapped or rotation_angle is not 0:
            if is_tapped:
                rotation_angle = 90
            rotated_surf = pg.transform.rotate(card_surf, -rotation_angle)
            rotated_rect = rotated_surf.get_rect(center=card.rect.center)
            screen.blit(rotated_surf, rotated_rect.topleft)
            card.rect = rotated_rect
        else:
            screen.blit(card_surf, card.rect.topleft)

    def draw_action_panel(self, x: int, y: int):
        screen = self.game.screen
        width = screen.width - self.game.gutter - x
        height = self.rows[max(self.rows)] + 150 - self.game.gutter

        # Background
        pg.draw.rect(screen, (40, 40, 40), pg.Rect(x, y, width, height))

        # Title
        title = self.small_font.render("Available Actions", True, (255, 255, 255))
        screen.blit(title, (x + 10, 20))

        for info in self.action_layout:
            rect = info.rect

            # Background
            bg_color = (255, 255, 0) if info.hovered else (70, 70, 70)
            pg.draw.rect(screen, bg_color, rect)

            # Border
            border_color = (150, 150, 150)
            pg.draw.rect(screen, border_color, rect, 1)

            # Text
            text_color = (0, 0, 0) if info.hovered else (255, 255, 255)
            text_surf = self.small_font.render(f"{info.index}: {info.action}", True, text_color)
            screen.blit(text_surf, (rect.x + 5, rect.y + 5))

    def build_action_layout(self, x: int, y: int, row_spacing: int = 40, padding: int = 10):
        self.action_layout = []

        if not self.available_actions:
            return

        for i, action in enumerate(self.available_actions):
            rect = pg.Rect(x + padding, y + 40, 250 - (padding * 2), 30)
            self.action_layout.append(ActionRenderInfo(action, rect, i))
            y += row_spacing

    def build_recent_actions_layout(self, x: int, y: int, row_spacing: int = 20, padding: int = 10):
        self.recent_actions = []
        if not self.state.game_history.items:
            return

        for i, record in enumerate(self.state.game_history.get_last_n(10)[::-1]):
            rect = pg.Rect(x + 10, y + 20, self.cols[11] - (padding * 2), 15)
            if record.get('type'):
                title = f'Cast {record["card"]}' if record['type'] == 'CastToBoard' else record['type']
            else:
                title = record.get('text')
            self.recent_actions.append(RecentEventRow(record.get('player_idx'), title, rect, i))
            y += row_spacing

    def draw_recent_actions(self, x: int, y: int):
        text_surf = self.small_font.render("Last 10 Events", True, (255, 255, 255))
        self.game.screen.blit(text_surf, (x + 10, y))

        for act in self.recent_actions:
            text_surf = self.small_font.render(act.display_text, True, (255, 255, 255))
            self.game.screen.blit(text_surf, (act.rect.x, act.rect.y))

    def draw_hover_preview(self, x: int, y: int, preview_w: int = 200, preview_h: int = 285):
        if self.hovered_card is None:
            return

        card = self.hovered_card

        # Face-up only
        if getattr(card, "face_down", False):
            return

        first_image_surf = next(iter(self.game.images[card.card.props.slug].values()))
        preview_surf = pg.transform.smoothscale(first_image_surf, (preview_w, preview_h))

        # Blit the preview
        self.game.screen.blit(preview_surf, (x + 20, y))

    def draw_stack(self, state):
        stack = state.stack
        if not stack:
            return

        screen = self.game.screen
        width, height = screen.get_size()

        card_width = 200
        card_height = 100

        # Center of the screen
        center_x = width // 2
        center_y = height // 2

        # Offset so items look stacked
        x_offset = 12
        y_offset = -18

        # Draw from bottom to top
        for i, stack_obj in enumerate(stack):
            x = center_x - card_width // 2 + (i * x_offset)
            y = center_y - card_height // 2 + (i * y_offset)

            rect = pg.Rect(x, y, card_width, card_height)

            # Background
            pg.draw.rect(screen, (60, 60, 60), rect)
            pg.draw.rect(screen, (255, 255, 255), rect, 2)

            # Draw name
            name_surface = self.small_font.render(stack_obj.name, True, (255, 255, 255),)
            screen.blit(name_surface, (x + 8, y + 8))

            # Optional: controller
            controller_surface = self.small_font.render(
                f"Controller: {stack_obj.controller.name}", True, (200, 200, 200))
            screen.blit(controller_surface, (x + 8, y + 35))

            # Highlight top of stack
            if i == len(stack) - 1:
                pg.draw.rect(screen, (255, 215, 0), rect, 3)
