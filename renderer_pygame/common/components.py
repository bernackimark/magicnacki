import pygame as pg

class ColoredBoxButton:
    def __init__(self, x, y, color, size=30, checked=True):
        self.rect = pg.Rect(x, y, size, size)
        self.color = color
        self.checked = checked

    def draw(self, surface):
        # draw box
        if self.checked:
            pg.draw.rect(surface, self.color, self.rect, border_radius=4)
        pg.draw.rect(surface, self.color, self.rect, width=2, border_radius=4)

    def handle_event(self, event) -> bool:
        """Returns True if an event was handled"""
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.checked = not self.checked
                return True  # an event was handled

class Button:
    def __init__(self, x, y, w, h, label):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.label = label
        self.rect = pg.Rect(self.x, self.y, self.w, self.h)

    def draw(self, surface):
        pg.draw.rect(surface, (70, 70, 70), self.rect, border_radius=6)
        label = pg.font.SysFont("arial", 32).render(self.label, True, (220, 220, 220))
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def handle_event(self, event) -> bool:
        ...

class Toggle:
    def __init__(self, x, y, label, label_w=125, slider_w=50, slider_h=30, checked=False):
        self.label_x = x
        self.label_y = y
        self.toggle_x = self.label_x + label_w
        self.slider_w = slider_w
        self.slider_h = slider_h

        self.left_rect = pg.Rect(self.toggle_x, self.label_y, self.slider_w // 2, self.slider_h)
        self.right_rect = pg.Rect(self.toggle_x + self.slider_w // 2, self.label_y, self.slider_w // 2, self.slider_h)
        self.sliding_rect = pg.Rect(self.toggle_x, self.label_y, round(self.slider_w / 3 * 2, 0), self.slider_h)
        self.label = label
        self.checked = checked

    @property
    def pg_label(self):
        return pg.font.SysFont('arial', 14, bold=True).render(self.label, True, (220, 220, 220))

    def draw(self, surface):
        surface.blit(self.pg_label, (self.label_x, self.label_y + 10))
        pg.draw.rect(surface, 'green', self.left_rect, border_top_left_radius=4, border_bottom_left_radius=4)
        pg.draw.rect(surface, 'darkgrey', self.right_rect, border_top_right_radius=4, border_bottom_right_radius=4)
        if self.checked:
            self.sliding_rect.x = self.toggle_x + (self.slider_w // 3)
        else:
            self.sliding_rect.x = self.toggle_x
        pg.draw.rect(surface, 'lightgrey', self.sliding_rect, border_radius=4)

    def handle_event(self, event) -> bool:
        """Returns True if an event is handled"""
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_rect.collidepoint(event.pos) or self.right_rect.collidepoint(event.pos):
                self.checked = not self.checked
                return True
