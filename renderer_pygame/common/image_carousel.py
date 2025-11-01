import pygame as pg
from renderer_pygame.common.components import Button

class ImageCarousel:
    def __init__(self, x, y, w, h, img_size: tuple[int, int], visible_cnt: int, carousel_images: list,
                 img_spacing: int = 15, slide_speed: float = 8.0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.img_size = img_size
        self.img_spacing = img_spacing
        self.visible_count = visible_cnt
        self.slide_speed = slide_speed

        # Carousel logic
        self.index_offset = 0
        self.target_offset = 0.0
        self.slide_offset = 0.0

        # Carousel accessories (initialized later, depend on layout)
        self.left_btn = Button(80, self.y + self.img_size[1] // 2 - 25, 50, 50, "<")
        self.right_btn = Button(self.w - 50, self.y + self.img_size[1] // 2 - 25, 50, 50, ">")

        self.images = carousel_images

    @property
    def in_focus_idx(self) -> int:
        return self.index_offset + (self.visible_count // 2)

    def draw(self, surface):
        total_width = self.img_size[0] * self.visible_count + self.img_spacing * (self.visible_count - 1)
        start_x = self.x

        # Draw placeholder spaces at the front of carousel, else can never grab index 0
        placeholder_card_surf = pg.Surface((self.img_size[0], self.img_size[1]))
        for i in range(self.visible_count // 2):
            surface.blit(placeholder_card_surf, (start_x - (self.img_spacing - self.img_size[0]) * i, self.y))
        # Draw all images
        displayed_card_cnt = 0
        for card_image in self.images:
            x = start_x + displayed_card_cnt * (self.img_size[0] + self.img_spacing) + self.slide_offset
            displayed_card_cnt += 1
            if -self.img_size[0] <= x <= self.w:
                surface.blit(card_image.image, (x, self.y))

        # Carousel buttons
        self.left_btn.draw(surface)
        self.right_btn.draw(surface)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_btn and self.left_btn.rect.collidepoint(event.pos):
                if self.index_offset > -(self.visible_count // 2):
                    self.index_offset -= 1
                    self.target_offset += self.img_size[0] + self.img_spacing

            elif self.right_btn and self.right_btn.rect.collidepoint(event.pos):
                if self.index_offset < len(self.images) - self.visible_count // 2 - 1:
                    self.index_offset += 1
                    self.target_offset -= self.img_size[0] + self.img_spacing
