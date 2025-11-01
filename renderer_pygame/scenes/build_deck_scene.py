from dataclasses import dataclass

from build_deck import DeckBuilder
import pygame as pg
from renderer_pygame.config import COLOR_DICT
from renderer_pygame.scenes.scene_abc import Scene
from renderer_pygame.common.components import ColoredBoxButton, Toggle, Button
from renderer_pygame.common.image_carousel import ImageCarousel
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
        self.IMG_SIZE = (200, 285)

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

        self.img_carousel = ImageCarousel(50, 100, 1200, self.IMG_SIZE[1], self.IMG_SIZE, 5, self.images)

        # Card Carousel Filters
        self.color_boxes: dict[str, ColoredBoxButton | None] = {c: None for c in COLOR_DICT}
        x = self.FILTERS_X + 10
        for color_letter, color_name in COLOR_DICT.items():
            self.color_boxes[color_letter] = ColoredBoxButton(x, self.FILTERS_Y + 10, color_name)
            x += 40

        self.creatures_only_btn = Toggle(self.FILTERS_X + 300, self.FILTERS_Y + 10, 'Creatures Only')

        self.select_this_card_outline = pg.Rect(self.img_carousel.x + (self.img_carousel.visible_count // 2 * (self.IMG_SIZE[0] + self.img_carousel.img_spacing)) - 10, self.img_carousel.y - 15, 220, self.IMG_SIZE[1] + 30)
        self.add_to_deck_btn: Button = None

        # ----- Your Deck table -----
        self.table = Table(self.game.screen, 50, 550, 50, 35, pg.font.SysFont('arial', 24, bold=True),
                           pg.font.SysFont('arial', 16),
                           [200, 150, 150, 150, 150, 150, 150],
                           ['Card', 'Count', 'Casting Cost', 'Types', 'P/T', 'KW Abilities', 'Image'])
        self.rows_built = False

    @property
    def selected_slug(self) -> str | None:
        if self.img_carousel.in_focus_idx > len(self.img_carousel.images) - 1:
            return None
        return self.img_carousel.images[self.img_carousel.in_focus_idx].slug

    # --- Handle events (ex: mouse clicks) ---
    def handle_events(self, events):
        for event in events:
            if event.type == pg.K_m:
                self.game.scenes.set_scene("menu", use_fade=True)

            for color_box in self.color_boxes.values():
                color_box.handle_event(event)

            self.creatures_only_btn.handle_event(event)

            self.img_carousel.handle_event(event)

            if event.type == pg.MOUSEBUTTONDOWN:
                if self.add_to_deck_btn and self.add_to_deck_btn.rect.collidepoint(event.pos):
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
        self.img_carousel.slide_offset += (self.img_carousel.target_offset - self.img_carousel.slide_offset) * min(self.img_carousel.slide_speed * dt, 1)

        # only build rows once per deck state change
        if not self.rows_built:
            self.build_table_rows()
            self.rows_built = True

        # update the active carousel images
        self.img_carousel.images = [i for i in self.images if self.color_boxes[i.colors[0]].checked and
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

        # Draw filters
        pg.draw.rect(screen, (220, 220, 220), pg.Rect(10, 10, 800, 60), 1, 6)
        text = self.font_smaller.render('Filters', True, (220, 220, 220))
        screen.blit(text, (15, 0))

        self.creatures_only_btn.draw(screen)

        for color_box in self.color_boxes.values():
            color_box.draw(screen)

        self.img_carousel.draw(screen)

        # Select This Card rectangle outline
        pg.draw.rect(screen, (220, 220, 220), self.select_this_card_outline, width=5, border_radius=6)

        # Add to Deck button
        self.add_to_deck_btn = Button(self.game.width // 2 - 100, self.img_carousel.y + self.IMG_SIZE[1] + 50, 200, 50, "Add to Deck")
        self.add_to_deck_btn.draw(screen)

        screen.fill((128, 128, 128), self.table.table_rect)
        for surf, pos in self.table.items_to_blit:
            screen.blit(surf, pos)


# TODO:
#  create remove buttons for each row & tie it to a card

