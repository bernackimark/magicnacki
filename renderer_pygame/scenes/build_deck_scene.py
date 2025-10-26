from build_deck import DeckBuilder
import pygame as pg
from renderer_pygame.scenes.scene_abc import Scene
from renderer_pygame.common.table import Table


class BuildDeckScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.font = pg.font.SysFont("arial", 32)

        # ----- Selecting Cards -----
        # Layout and style
        self.BG_COLOR = (25, 25, 25)
        self.CAROUSEL_Y = 150
        self.IMG_SIZE = (200, 285)
        self.IMG_SPACING = 15
        self.VISIBLE_COUNT = 5
        self.SLIDE_SPEED = 8.0

        self.deck_builder = DeckBuilder(self.game.card_univ, 0)

        # For all cards in the universe, load those images to a nested dictionary
        self.images = {}
        for card in sorted(self.game.card_univ.cards, key=lambda c: c.slug):
            for set_code, image in card.images.items():
                card_img = self.game.images[card.slug][set_code]
                if card.slug not in self.images:
                    self.images[card.slug] = {}
                self.images[card.slug][set_code] = pg.transform.smoothscale(card_img, self.IMG_SIZE)
        if not self.images:
            raise SystemExit("No images found!")

        # Carousel logic
        self.index_offset = 0
        self.target_offset = 0.0
        self.slide_offset = 0.0

        self.in_focus_card_slug = ''

        # Buttons (initialized later, depend on layout)
        self.left_btn = None
        self.right_btn = None
        self.add_to_deck_btn = None

        # ----- Your Deck table -----
        self.table = Table(self.game.screen, 50, 550, 50, 35, pg.font.SysFont('arial', 24, bold=True),
                           pg.font.SysFont('arial', 16),
                           [200, 150, 150, 150, 150, 150, 150],
                           ['Card', 'Count', 'Casting Cost', 'Types', 'P/T', 'KW Abilities', 'Image'])
        self.rows_built = False

        # # Precompute button rectangles
        # # TODO: this may need to be resurrected ... need to relate each button on the screen w a row ID
        # self.my_deck_remove_card_buttons = []
        # x_positions = [50]
        # for w in self.column_widths[:-1]:
        #     x_positions.append(x_positions[-1] + w)
        #
        # for i, (_, _) in enumerate(self.my_deck_rows):
        #     y = self.start_y + i * self.row_height
        #     btn_rect = pg.Rect(x_positions[2], y + 25, self.column_widths[2] - 20, 40)
        #     self.my_deck_remove_card_buttons.append(btn_rect)
        #
        # self.clicked_row = None

    @property
    def in_focus_card_idx(self) -> int:
        return self.index_offset + (self.VISIBLE_COUNT // 2)

    @property
    def selected_slug(self) -> str:
        for i, slug in enumerate(self.images):
            if i == self.in_focus_card_idx:
                return slug

    # --- Helper: draw a button ---
    def draw_button(self, surface, rect, text):
        pg.draw.rect(surface, (70, 70, 70), rect, border_radius=6)
        label = self.font.render(text, True, (255, 255, 255))
        label_rect = label.get_rect(center=rect.center)
        surface.blit(label, label_rect)

    # --- Handle events (mouse clicks) ---
    def handle_events(self, events):
        for event in events:
            if event.type == pg.K_m:
                self.game.scenes.set_scene("menu", use_fade=True)

            if event.type == pg.MOUSEBUTTONDOWN:
                x, y = event.pos

                if self.left_btn and self.left_btn.collidepoint(x, y):
                    if self.index_offset > 0:
                        self.index_offset -= 1
                        self.target_offset += self.IMG_SIZE[0] + self.IMG_SPACING

                elif self.right_btn and self.right_btn.collidepoint(x, y):
                    if self.index_offset < len(self.images) - self.VISIBLE_COUNT:
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

                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    # TODO: need to re-write how each button relates to a specific card
                    for i, btn_rect in enumerate(self.my_deck_remove_card_buttons):
                        if btn_rect.collidepoint(event.pos):
                            print(f"Minus button clicked on row {i}: {self.my_deck_rows[i][0]}")
                            self.clicked_row = i

    # --- Update slide animation ---
    def update(self, dt):
        # Smooth interpolation
        self.slide_offset += (self.target_offset - self.slide_offset) * min(self.SLIDE_SPEED * dt, 1)

        # only build rows once per deck state change
        if not self.rows_built:
            self.build_table_rows()
            self.rows_built = True

    def build_table_rows(self) -> None:
        """Rebuild the table when deck contents change"""
        self.table.clear_rows()
        for c in self.deck_builder.unique_cards_sorted:
            self.table.add_row([c.props.name, str(self.deck_builder.get_slug_cnt(c.props.slug)),
                                c.props.casting_cost, ', '.join(c.props.card_types),
                                f'{c.props.power}/{c.props.toughness}', ', '.join(c.props.keyword_abilities),
                                'Something re: Image'])

    # --- Draw everything ---
    def draw(self):
        screen = self.game.screen
        screen.fill(self.BG_COLOR)

        total_width = self.IMG_SIZE[0] * self.VISIBLE_COUNT + self.IMG_SPACING * (self.VISIBLE_COUNT - 1)
        start_x = (self.game.width - total_width) // 2 + self.slide_offset

        # Draw all images (only the first image for each slug)
        for i, (slug, card_images) in enumerate(self.images.items()):
            for _, surface in card_images.items():
                x = start_x + i * (self.IMG_SIZE[0] + self.IMG_SPACING)
                if -self.IMG_SIZE[0] <= x <= self.game.width:
                    screen.blit(surface, (x, self.CAROUSEL_Y))
                break

        # Carousel buttons
        self.left_btn = pg.Rect(80, self.CAROUSEL_Y + self.IMG_SIZE[1] // 2 - 25, 50, 50)
        self.right_btn = pg.Rect(self.game.width - 130, self.CAROUSEL_Y + self.IMG_SIZE[1] // 2 - 25, 50, 50)
        self.draw_button(screen, self.left_btn, "<")
        self.draw_button(screen, self.right_btn, ">")

        # Add to Deck button
        self.add_to_deck_btn = pg.Rect(self.game.width // 2 - 100, self.CAROUSEL_Y + self.IMG_SIZE[1] + 50, 200, 50)
        self.draw_button(screen, self.add_to_deck_btn, "Add to Deck")

        # Optionally: show current image keys (for debugging)
        for i, (slug, _) in enumerate(self.images.items()):
            if i == self.in_focus_card_idx:
                in_focus_text = self.font.render(f"In-focus slug: {slug}", True, (200, 200, 200))
                screen.blit(in_focus_text, (40, 70))
                break

        screen.fill((128, 128, 128), self.table.table_rect)
        for surf, pos in self.table.items_to_blit:
            screen.blit(surf, pos)


# TODO:
#  create remove buttons for each row & tie it to a card

