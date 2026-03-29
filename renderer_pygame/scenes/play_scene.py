from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from renderer_pygame.common.pg_card import CARD_W, CARD_H, CARD_BACK_IMG, PGCard

if TYPE_CHECKING:
    from engine import Engine
    from game_state import GameState

import pygame as pg
from models.actions.base import Action
from models.utils import flip
from renderer_pygame.common.animations import Animation, jiggle
from renderer_pygame.common.dice import make_pg_dice, int_to_dice_values
from renderer_pygame.common.fan import get_fan_positions
from renderer_pygame.game import Game
from renderer_pygame.scenes.scene_abc import Scene

BASIC_LANDS = {'forest', 'island', 'mountain', 'plains', 'swamp'}


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
    def __init__(self, game: Game, engine: Engine, p_idx: int):
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

        self.p_idx = p_idx

        self.dice: dict[int: pg.Surface] = {i: make_pg_dice(40, 40, i) for i in range(1, 7)}

        self.active_animations: list[Animation] = []
        self.life_jiggle_offsets: list[list[tuple[float, float]]] = [
            [(0, 0) for _ in range(len(int_to_dice_values(life)))] for life in self.state.life]
        self.flash_surface = pg.Surface(self.game.screen.get_size(), pg.SRCALPHA)

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

    def handle_action_click(self, mouse_pos):
        """Handle if one of the action option boxes are clicked"""
        for info in self.action_layout:
            if info.rect.collidepoint(mouse_pos):
                # This is the clicked action
                self.pending_action = info.action
                print(f"Clicked action: {info.action}")

                # Execute immediately like the console
                info.action.play()
                self.state.game_history.append_action(info.action, self.state)
                break

    def update(self, dt):
        """Executes once per frame; processes animations if applicable change occurs"""
        self.available_actions = self.state.get_available_actions(self.state.action_on_idx)
        self.build_action_layout(self.cols[10], self.rows[0])
        self.build_recent_actions_layout(self.cols[10], self.rows[3])
        self.update_action_hover()

        # detect life changes
        for p_idx, life_total in enumerate(self.state.life):
            if self.prev_state['life'][p_idx] != self.state.life[p_idx]:
                new_life_total = self.state.life[p_idx]
                is_opp = p_idx != self.p_idx
                color = (0, 125, 0, 100) if life_total > self.prev_state['life'][p_idx] else (125, 0, 0, 100)
                self.life_change_animations(p_idx, new_life_total, is_opp, color)

        # update active animations
        for anim in self.active_animations[:]:
            anim.update(dt)
            if anim.finished:
                self.active_animations.remove(anim)

        # assign current to previous state
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

        self.game.screen.blit(self.flash_surface, (0, 0))

    def draw_player_area(self, p_idx: int, top: bool):
        self.draw_dice(p_idx, self.cols[0], self.rows[1] if top else self.rows[4])
        self.draw_library(p_idx, self.cols[1], self.rows[1] if top else self.rows[4])
        self.draw_graveyard(p_idx, self.cols[1], self.rows[0] if top else self.rows[5])
        self.draw_exile(p_idx, self.cols[0], self.rows[0] if top else self.rows[5])
        self.draw_battlefield(p_idx, 2, 1 if top else 4)
        self.draw_hand(p_idx, 2, 0 if top else 5, top, top)

    def draw_dice(self, p_idx: int, x: int, y: int):
        """draw dice in a 2-wide by 3-tall (max) configuration"""
        dice_values = int_to_dice_values(self.state.life[p_idx])
        x += 5  # the dice are slightly too far left

        for i, value in enumerate(dice_values):
            offset_x, offset_y = self.life_jiggle_offsets[p_idx][i]
            die_x = x + (50 * (i % 2)) + offset_x
            die_y = y + (50 * (i // 2)) + offset_y
            self.game.screen.blit(self.dice[value], (die_x, die_y))

    def draw_hand(self, p_idx: int, col: int, row: int, face_down: bool, is_opp: bool):
        """Opponent hand is a straight line atop screen; player hand is fanned along an invisible arc"""
        mouse_pos = pg.mouse.get_pos()
        cards = self.state.hands[p_idx].cards
        if not len(cards):
            return

        # arc/fan parameters
        center_x = self.cols[col + 3]  # shift right for centering
        center_y = self.rows[row] + 170  # below cards
        radius = 200

        if not is_opp:
            positions = get_fan_positions(len(cards), center_x, center_y, radius)
        else:
            positions = [(self.cols[col + i], self.rows[row], 0) for i in range(len(cards))]

        for i, (card, (x, y, angle)) in enumerate(zip(cards, positions)):
            first_image_surf = next(iter(self.game.images[card.props.slug].values()))
            pg_card = PGCard(card, first_image_surf, i)
            pg_card.draw(self.game.screen, int(x), int(y), face_down=face_down, rotation_angle=angle,
                         crop_ratio=0.61 if not is_opp else 1.0, scale=1.4 if not is_opp else 1.0)

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
            pg_card.draw(self.game.screen, x, y)

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
        pg_card.draw(self.game.screen, x, y)

    def draw_exile(self, p_idx: int, x, y):
        if not self.state.exiles[p_idx]:
            return

        top_card = self.state.exiles[p_idx][-1]
        first_image_surf = next(iter(self.game.images[top_card.props.slug].values()))
        pg_card = PGCard(top_card, first_image_surf, 0)
        pg_card.draw(self.game.screen, x, y, rotation_angle=-90)

    def draw_library(self, p_id: int, x: int, y: int):
        card_cnt = len(self.state.libraries[p_id].cards)
        if not card_cnt:
            return
        card_back_surf = pg.transform.smoothscale(CARD_BACK_IMG, (CARD_W, CARD_H))
        self.game.screen.blit(card_back_surf, (x, y))
        card_cnt_text = self.small_font.render(str(card_cnt), True, (200, 200, 200))
        self.game.screen.blit(card_cnt_text, (x + 5, y + 5))

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
        if self.hovered_card is None or getattr(self.hovered_card, "face_down", False):
            return

        first_image_surf = next(iter(self.game.images[self.hovered_card.card.props.slug].values()))
        preview_surf = pg.transform.smoothscale(first_image_surf, (preview_w, preview_h))
        self.game.screen.blit(preview_surf, (x + 20, y))

    def life_change_animations(self, p_idx: int, life_total: int, is_opp: bool,
                               color: tuple[int, int, int, int]) -> None:
        # Flash green/red for the half of the screen of the player whose life total changed
        half_screen_rect = pg.Rect(0, 0 if is_opp else self.rows[3],
                                   self.game.screen.get_width(), self.game.screen.get_height() // 2)

        def flash_update(progress, col=color):
            fade_progress = progress * 2 if progress < 0.5 else (1 - progress) * 2  # fade in then out
            alpha = int(100 * fade_progress)
            self.flash_surface.fill((0, 0, 0, 0))
            temp = pg.Surface(half_screen_rect.size, pg.SRCALPHA)
            temp.fill((*col[:3], alpha))
            self.flash_surface.blit(temp, half_screen_rect.topleft)

        self.active_animations.append(Animation(flash_update, 0.5))

        dice_values = int_to_dice_values(life_total, 36)
        for i in range(len(dice_values)):  # each die has its own animation
            # Expand the list if necessary to accommodate when life is added & another die is needed
            while len(self.life_jiggle_offsets[p_idx]) <= i:
                self.life_jiggle_offsets[p_idx].append((0.0, 0.0))

            def make_update_fn(idx, player_idx):
                def update_fn(progress):
                    self.life_jiggle_offsets[player_idx][idx] = jiggle(progress, slows_over_time=True)

                return update_fn

            self.active_animations.append(Animation(make_update_fn(i, p_idx), 1))

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
