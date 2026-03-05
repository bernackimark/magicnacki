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

@dataclass
class PGCard:
    card: GameCard
    rect: pg.Rect
    index: int
    hovered: bool = False
    selected: bool = False

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
        self.build_hand_layout()
        self.build_action_layout()
        self.update_action_hover()

        self.mouse_pos = pg.mouse.get_pos()
        self.hovered_card = None

        # Determine if mouse is over a card in hand
        for hand_card in self.hand_layout:
            if hand_card.rect.collidepoint(self.mouse_pos):
                self.hovered_card = hand_card
                break

    def update_action_hover(self):
        mouse_pos = pg.mouse.get_pos()
        for info in self.action_layout:
            info.hovered = info.rect.collidepoint(mouse_pos)

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

        if top:
            y_base = 50
            hand_y = 10
        else:
            y_base = height - 300
            hand_y = height - 180

        # Draw life total
        life_text = self.font.render(str(self.state.life[self.p_idx]), True, (255, 255, 255))
        self.game.screen.blit(life_text, (20, y_base))

        # Draw library (face down)
        self.draw_library(p_idx, x=150, y=y_base)

        # Draw graveyard
        self.draw_graveyard(p_idx, x=250, y=y_base)

        # Draw battlefield
        self.draw_battlefield(p_idx, y=y_base + 100)

        # Draw hand (only visible if bottom player)
        if not top:
            self.draw_hand()

    def draw_hand(self):
        for card in self.hand_layout:
            self.draw_card(card)

    def draw_battlefield(self, p_id: int, y):
        x = 200
        spacing = 100

        for i, permanent in enumerate(self.state.boards[p_id]):
            rect = pg.Rect(x, y, 80, 120)
            pg_card = PGCard(permanent, rect, i)
            self.draw_card(pg_card)
            x += spacing

    def draw_card(self, card: PGCard):
        pg.draw.rect(self.game.screen, (240, 240, 200), card.rect)
        pg.draw.rect(self.game.screen, (0, 0, 0), card.rect, 2)

        name_text = self.small_font.render(card.card.props.name, True, (0, 0, 0))
        self.game.screen.blit(name_text, (card.rect.x + 5, card.rect.y + 5))

    def draw_library(self, player, x, y):
        rect = pg.Rect(x, y, 80, 120)
        pg.draw.rect(self.game.screen, (50, 50, 150), rect)
        pg.draw.rect(self.game.screen, (0, 0, 0), rect, 2)

    def draw_graveyard(self, p_idx: int, x, y):
        rect = pg.Rect(x, y, 80, 120)
        pg.draw.rect(self.game.screen, (120, 120, 120), rect)

        if self.state.graveyards[p_idx]:
            top_card = self.state.graveyards[p_idx][-1]
            name = self.small_font.render(top_card.props.name, True, (0, 0, 0))
            self.game.screen.blit(name, (x + 5, y + 5))

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

    def build_hand_layout(self):
        p_id = self.state.player_turn_idx
        screen = self.game.screen
        width, height = screen.get_size()

        cards = self.state.hands[p_id].cards
        count = len(cards)

        if count == 0:
            self.hand_layout = []
            return

        card_width = 80
        card_height = 120
        spacing = 90

        total_width = (count - 1) * spacing + card_width
        start_x = (width - total_width) // 2
        y = height - card_height - 20

        layout = []

        for i, card in enumerate(cards):
            x = start_x + i * spacing
            rect = pg.Rect(x, y, card_width, card_height)

            layout.append(PGCard(card, rect, i))

        self.hand_layout = layout

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
