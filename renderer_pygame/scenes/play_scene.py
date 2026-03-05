from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.actions.base import Action

import pygame as pg

from engine import Engine
from game_state import GameState
from models.game_card import GameCard
from models.utils import flip
from renderer_pygame.scenes.scene_abc import Scene

CARD_W = 100
CARD_H = 142

@dataclass
class PGCard:
    card: GameCard
    surf: pg.Surface
    index: int
    rect: pg.Rect = None
    hovered: bool = False
    selected: bool = False
    face_down_color = (50, 50, 150)
    face_up_color = (240, 240, 200)

    def __post_init__(self):
        self.surf = pg.transform.smoothscale(self.surf, (CARD_W, CARD_H))

@dataclass
class ActionRenderInfo:
    action: Action
    rect: pg.Rect
    index: int
    hovered: bool = False

class PlayScene(Scene):
    def __init__(self, game, engine):
        super().__init__(game)
        self.engine: Engine = engine
        self.font = pg.font.SysFont("arial", 48)
        self.small_font = pg.font.SysFont("arial", 12)
        self.mouse_pos = 0, 0
        self.hand_layout: list[PGCard] = []
        self.hovered_card = None
        self.selected_card = None
        self.state: GameState = self.engine.gs

        self.p_idx = 0

        self.hand_cards: list[PGCard] = []

        self.available_actions = []
        self.action_layout = []  # list of ActionRenderInfo
        self.pending_action = None

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
        self.build_action_layout()
        self.update_action_hover()

    def update_action_hover(self):
        mouse_pos = pg.mouse.get_pos()
        for info in self.action_layout:
            info.hovered = info.rect.collidepoint(mouse_pos)

        for card in self.hand_cards:
            if card.rect.collidepoint(mouse_pos):
                self.hovered_card = card
                break

    def draw(self):
        screen = self.game.screen
        screen.fill((30, 100, 30))  # green felt table

        # Draw opponent zones (top half)
        self.draw_player_area(flip(self.p_idx), top=True)

        # Draw stack (center)
        # self.draw_stack(state)  # skipping this for now; would probably want to use gs.action_stack

        # Draw current player zones (bottom half)
        self.draw_player_area(self.p_idx, top=False)

        self.draw_action_panel()

        # Hover preview on top of everything
        self.draw_hover_preview()

    def handle_action_click(self, mouse_pos):
        for info in self.action_layout:
            if info.rect.collidepoint(mouse_pos):
                # This is the clicked action
                self.pending_action = info.action
                print(f"Clicked action: {info.action}")

                # Execute immediately like the console
                info.action.play()
                self.state.game_history.append((self.state.turn_number, info.action))

                # After action is played, refresh available actions for the next player
                self.available_actions = self.state.get_available_actions(self.state.action_on_idx)
                self.build_action_layout()
                break

    def draw_player_area(self, p_idx: int, top: bool):
        width, height = self.game.screen.get_size()
        y_base = 180 if top else height - 300

        life_text = self.font.render(str(self.state.life[p_idx]), True, (255, 255, 255))
        self.game.screen.blit(life_text, (20, y_base))

        self.draw_library(p_idx, 150, y_base)
        self.draw_graveyard(p_idx, 150, y_base - 150 if top else y_base + 150)
        self.draw_exile(p_idx, 20, y_base - 150 if top else y_base + 150)
        self.draw_battlefield(p_idx, 350, y_base)
        self.draw_hand(p_idx, 350, y_base - 150 if top else y_base + 150, top)

    def draw_hand(self, p_idx: int, x: int, y: int, top: bool):
        # I want to draw the opponent's cards face down; self.hand_layout is really focused on the bottom player's hand
        spacing = CARD_W + 20

        for i, card in enumerate(self.state.hands[p_idx].cards):
            first_image_surf = next(iter(self.game.images[card.props.slug].values()))
            pg_card = PGCard(card, first_image_surf, i)
            self.draw_card(pg_card, x, y, face_down=top)
            x += spacing

            if not top:
                # Store x, y, width, height along with PGCard
                pg_card.rect = pg.Rect(x, y, CARD_W, CARD_H)
                self.hand_cards.append(pg_card)

    def draw_battlefield(self, p_id: int, x: int, y: int):
        spacing = CARD_W + 20

        for i, card in enumerate(self.state.boards[p_id]):
            first_image_surf = next(iter(self.game.images[card.props.slug].values()))
            pg_card = PGCard(card, first_image_surf, i)
            self.draw_card(pg_card, x, y, is_rotated=card.is_tapped)
            x += spacing

    def draw_card(self, card: PGCard, x: int, y: int, width=CARD_W, height=CARD_H,
                  face_down: bool = False, is_rotated: bool = False):
        """Draws a card at the given position (x, y) with the given width/height. Rotated 90 degrees if is_rotated."""
        card.rect = pg.Rect(x, y, width, height)
        screen = self.game.screen

        if face_down:
            pg.draw.rect(screen, card.face_down_color, card.rect)
            pg.draw.rect(screen, (0, 0, 0), card.rect, 2)
            return

        card_surf = pg.transform.smoothscale(card.surf, (width, height))

        if is_rotated:
            rotated_surf = pg.transform.rotate(card_surf, -90)
            draw_rect = rotated_surf.get_rect(center=card.rect.center)
            screen.blit(rotated_surf, draw_rect.topleft)
        else:
            screen.blit(card_surf, card.rect.topleft)

        # Optional: highlight if hovered
        if getattr(card, "hovered", False):
            highlight_rect = card.rect.inflate(4, 4)
            pg.draw.rect(screen, (255, 0, 0), highlight_rect, 2)

    def draw_library(self, p_id: int, x: int, y: int):
        rect = pg.Rect(x, y, CARD_W, CARD_H)
        pg.draw.rect(self.game.screen, (50, 50, 150), rect)
        pg.draw.rect(self.game.screen, (0, 0, 0), rect, 2)
        card_cnt = len(self.state.libraries[p_id].cards)
        card_cnt_text = self.small_font.render(str(card_cnt), True, (0, 0, 0))
        self.game.screen.blit(card_cnt_text, (rect.x + 5, rect.y + 5))

    def draw_graveyard(self, p_idx: int, x, y):
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
        self.draw_card(pg_card, x, y, is_rotated=True)

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

    def draw_action_panel(self):
        screen = self.game.screen
        screen_w, screen_h = screen.get_size()

        panel_width = 300
        panel_rect = pg.Rect(screen_w - panel_width, 0, panel_width, screen_h)

        # Background
        pg.draw.rect(screen, (40, 40, 40), panel_rect)

        # Title
        title = self.small_font.render("Available Actions", True, (255, 255, 255))
        screen.blit(title, (panel_rect.x + 20, 40))

        # Actions
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

    def build_action_layout(self):
        self.action_layout = []

        if not self.available_actions:
            return

        screen_w, screen_h = self.game.screen.get_size()

        panel_width = 300
        x = screen_w - panel_width + 20
        y = 100
        spacing = 40

        for i, action in enumerate(self.available_actions):
            rect = pg.Rect(x, y, panel_width - 40, 30)
            self.action_layout.append(ActionRenderInfo(action, rect, i))
            y += spacing

    def draw_hover_preview(self):
        if self.hovered_card is None:
            return

        card = self.hovered_card

        # Face-up only
        if getattr(card, "face_down", False):
            return

        screen = self.game.screen
        screen_w, screen_h = screen.get_size()

        preview_width = 200
        preview_height = 285

        first_image_surf = next(iter(self.game.images[card.card.props.slug].values()))
        preview_surf = pg.transform.smoothscale(first_image_surf, (preview_width, preview_height))

        padding = 20
        x = screen_w - preview_width - padding
        y = screen_h - preview_height - padding

        # Draw border
        border_rect = pg.Rect(x - 2, y - 2, preview_width + 4, preview_height + 4)
        pg.draw.rect(screen, (200, 200, 200), border_rect)

        # Blit the preview
        screen.blit(preview_surf, (x, y))
