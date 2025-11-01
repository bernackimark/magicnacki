from dataclasses import dataclass

from build_deck import DeckBuilder
import pygame as pg
from renderer_pygame.config import COLOR_DICT
from renderer_pygame.scenes.scene_abc import Scene
from renderer_pygame.common.components import ColoredBoxButton, Toggle
from renderer_pygame.common.table import Table

@dataclass
class CardImage:
    slug: str
    colors: str
    card_types: list[str]
    image: pg.Surface  # only loading one image per card


class BuildDeckScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.font = pg.font.SysFont("arial", 32)
        self.font_smaller = pg.font.SysFont("arial", 14)

        # ----- Selecting Cards -----
        # Layout and style
        self.BG_COLOR = (25, 25, 25)
        self.FILTERS_X = 10
        self.FILTERS_Y = 10
        self.CAROUSEL_Y = 100
        self.IMG_SIZE = (200, 285)
        self.IMG_SPACING = 15
        self.VISIBLE_COUNT = 5
        self.SLIDE_SPEED = 8.0

        self.deck_builder = DeckBuilder(self.game.card_univ, 0)

        # For all cards in the universe, load those images to a nested dictionary
        self.images = []
        for card in sorted(self.game.card_univ.cards, key=lambda c: c.slug):
            for img in self.game.images[card.slug].values():  # load the first image for each card
                self.images.append(CardImage(card.slug, card.colors, card.card_types,
                                             pg.transform.smoothscale(img, self.IMG_SIZE)))
                break

        if not self.images:
            raise SystemExit("No images found!")

        self.active_carousel_images = self.images.copy()

        # Card Carousel Filters
        self.color_boxes: dict[str, ColoredBoxButton | None] = {c: None for c in COLOR_DICT}
        x = self.FILTERS_X + 10
        for color_letter, color_name in COLOR_DICT.items():
            self.color_boxes[color_letter] = ColoredBoxButton(x, self.FILTERS_Y + 10, color_name)
            x += 40

        self.creatures_only_btn = Toggle(self.FILTERS_X + 300, self.FILTERS_Y + 10, 'Creatures Only')

        # Carousel logic
        self.index_offset = 0
        self.target_offset = 0.0
        self.slide_offset = 0.0

        self.select_this_card_outline = pg.Rect(self.game.width // 2 - 110, self.CAROUSEL_Y - 15, 220, self.IMG_SIZE[1] + 30)

        # Carousel accessories (initialized later, depend on layout)
        self.left_btn = None
        self.right_btn = None
        self.add_to_deck_btn = None

        # ----- Your Deck table -----
        self.table = Table(self.game.screen, 50, 550, 50, 35, pg.font.SysFont('arial', 24, bold=True),
                           pg.font.SysFont('arial', 16),
                           [200, 150, 150, 150, 150, 150, 150],
                           ['Card', 'Count', 'Casting Cost', 'Types', 'P/T', 'KW Abilities', 'Image'])
        self.rows_built = False

    @property
    def in_focus_card_idx(self) -> int:
        return self.index_offset + (self.VISIBLE_COUNT // 2)

    @property
    def selected_slug(self) -> str | None:
        if self.in_focus_card_idx > len(self.active_carousel_images) - 1:
            return None
        return self.active_carousel_images[self.in_focus_card_idx].slug
        # for i, card_image in enumerate(self.images):
        #     if i == self.in_focus_card_idx:
        #         return card_image.slug

    # --- Helper: draw a button ---
    def draw_button(self, surface, rect, text):
        pg.draw.rect(surface, (70, 70, 70), rect, border_radius=6)
        label = self.font.render(text, True, (220, 220, 220))
        label_rect = label.get_rect(center=rect.center)
        surface.blit(label, label_rect)

    # --- Handle events (mouse clicks) ---
    def handle_events(self, events):
        for event in events:
            if event.type == pg.K_m:
                self.game.scenes.set_scene("menu", use_fade=True)

            for color_box in self.color_boxes.values():
                color_box.handle_event(event)

            self.creatures_only_btn.handle_event(event)

            if event.type == pg.MOUSEBUTTONDOWN:
                x, y = event.pos

                if self.left_btn and self.left_btn.collidepoint(x, y):
                    if self.index_offset > -(self.VISIBLE_COUNT // 2):
                        self.index_offset -= 1
                        self.target_offset += self.IMG_SIZE[0] + self.IMG_SPACING

                elif self.right_btn and self.right_btn.collidepoint(x, y):
                    if self.index_offset < len(self.active_carousel_images) - self.VISIBLE_COUNT // 2 - 1:
                        self.index_offset += 1
                        self.target_offset -= self.IMG_SIZE[0] + self.IMG_SPACING

                elif self.add_to_deck_btn and self.add_to_deck_btn.collidepoint(x, y):
                    if not self.selected_slug:
                        continue
                    card = self.game.card_univ[self.selected_slug]
                    self.deck_builder.add_card(card)
                    self.rows_built = False
                    print("Your deck now has these cards:")
                    for c in self.deck_builder.cards:
                        print(c)

    # --- Update slide animation ---
    def update(self, dt):
        # Smooth interpolation
        self.slide_offset += (self.target_offset - self.slide_offset) * min(self.SLIDE_SPEED * dt, 1)

        # only build rows once per deck state change
        if not self.rows_built:
            self.build_table_rows()
            self.rows_built = True

        # update the active carousel images
        self.active_carousel_images = [i for i in self.images if self.color_boxes[i.colors[0]].checked and
                                       ('Creature' in i.card_types or not self.creatures_only_btn.checked)]

    def build_table_rows(self) -> None:
        """Rebuild the table when deck contents change"""
        self.table.clear_rows()
        for c in self.deck_builder.unique_cards_sorted:
            p_t_text = f'{c.props.power}/{c.props.toughness}' if c.props.power or c.props.toughness else ''
            self.table.add_row([c.props.name, str(self.deck_builder.get_slug_cnt(c.props.slug)),
                                c.props.casting_cost, ', '.join(c.props.card_types),
                                p_t_text, ', '.join(c.props.keyword_abilities),
                                'Something re: Image'])

    # --- Draw everything ---
    def draw(self):
        screen = self.game.screen
        screen.fill(self.BG_COLOR)

        total_width = self.IMG_SIZE[0] * self.VISIBLE_COUNT + self.IMG_SPACING * (self.VISIBLE_COUNT - 1)
        start_x = (self.game.width - total_width) // 2 + self.slide_offset

        # Draw filters
        pg.draw.rect(screen, (220, 220, 220), pg.Rect(10, 10, 800, 60), 1, 6)
        text = self.font_smaller.render('Filters', True, (220, 220, 220))
        screen.blit(text, (15, 0))

        self.creatures_only_btn.draw(screen)

        for color_box in self.color_boxes.values():
            color_box.draw(screen)

        # Draw placeholder spaces at the front of carousel, else can never grab index 0
        placeholder_card_surf = pg.Surface((self.IMG_SIZE[0], self.IMG_SIZE[1]))
        screen.blit(placeholder_card_surf, (start_x - self.IMG_SPACING - self.IMG_SIZE[0], self.CAROUSEL_Y))
        screen.blit(placeholder_card_surf, (start_x - (self.IMG_SPACING + self.IMG_SIZE[0]) * 2, self.CAROUSEL_Y))
        # Draw all images based on filters
        displayed_card_cnt = 0
        for card_image in self.active_carousel_images:
            x = start_x + displayed_card_cnt * (self.IMG_SIZE[0] + self.IMG_SPACING)
            displayed_card_cnt += 1
            if -self.IMG_SIZE[0] <= x <= self.game.width:
                screen.blit(card_image.image, (x, self.CAROUSEL_Y))

        # Carousel buttons
        self.left_btn = pg.Rect(80, self.CAROUSEL_Y + self.IMG_SIZE[1] // 2 - 25, 50, 50)
        self.right_btn = pg.Rect(self.game.width - 130, self.CAROUSEL_Y + self.IMG_SIZE[1] // 2 - 25, 50, 50)
        self.draw_button(screen, self.left_btn, "<")
        self.draw_button(screen, self.right_btn, ">")

        # Select This Card rectangle outline
        pg.draw.rect(screen, (220, 220, 220), self.select_this_card_outline, width=5, border_radius=6)

        # Add to Deck button
        self.add_to_deck_btn = pg.Rect(self.game.width // 2 - 100, self.CAROUSEL_Y + self.IMG_SIZE[1] + 50, 200, 50)
        self.draw_button(screen, self.add_to_deck_btn, "Add to Deck")

        # Optionally: show current image keys (for debugging)
        # for i, (slug, _) in enumerate(self.images.items()):
        #     if i == self.in_focus_card_idx:
        #         in_focus_text = self.font.render(f"In-focus slug: {slug}", True, (200, 200, 200))
        #         screen.blit(in_focus_text, (40, 70))
        #         break

        screen.fill((128, 128, 128), self.table.table_rect)
        for surf, pos in self.table.items_to_blit:
            screen.blit(surf, pos)


# TODO:
#  create remove buttons for each row & tie it to a card

