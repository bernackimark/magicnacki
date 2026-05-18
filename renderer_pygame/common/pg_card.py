from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

import pygame as pg
from models.game_card import GameCard

CARD_W = 100
CARD_H = 142
CARD_BACK_IMG = pg.image.load(Path("renderer_pygame/assets/card_back.jpg"))
RENDER_SCALE = 2


@dataclass
class PGCard:
    card: GameCard
    full_surf: pg.Surface
    art_surf: pg.Surface
    index: int
    rect: pg.Rect = None
    hovered: bool = False
    selected: bool = False
    back_surf: pg.Surface = CARD_BACK_IMG

    def __post_init__(self):
        hi_w = int(CARD_W * RENDER_SCALE)
        hi_h = int(CARD_H * RENDER_SCALE)
        self.hi_res_full_surf = pg.transform.smoothscale(self.full_surf, (hi_w, hi_h))
        self.hi_res_art_surf = pg.transform.smoothscale(self.art_surf, (hi_w, hi_h))

        self.back_surf = self.back_surf.convert_alpha()
        self.back_surf = pg.transform.smoothscale(self.back_surf, (CARD_W, CARD_H))

    def draw(self, screen: pg.Surface, x: int, y: int, width=CARD_W, height=CARD_H,
             face_down=False, rotation_angle=0, crop_ratio=1.0, scale=1.0, full_or_art: str = 'full'):
        """Crop, rotate, scale, draw card, update interaction rectangle"""
        surf = self.back_surf if face_down else self.art_surf if full_or_art == 'art' else self.full_surf

        if self.card.is_tapped:
            rotation_angle = 90

        # crop BEFORE rotation (visual only)
        if crop_ratio < 1.0:
            w, h = surf.get_size()
            crop_rect = pg.Rect(0, 0, w, int(h * crop_ratio))
            surf = surf.subsurface(crop_rect)

        # rotate
        rotated = pg.transform.rotate(surf, -rotation_angle)

        # scale (constant, based on original surface)
        base_w, base_h = surf.get_size()
        scale_ratio = (width / base_w) * scale
        new_w = int(rotated.get_width() * scale_ratio)
        new_h = int(rotated.get_height() * scale_ratio)
        final = pg.transform.smoothscale(rotated, (new_w, new_h))

        # position using FULL card geometry (not cropped!)
        full_rect = pg.Rect(0, 0, width, height)
        full_rect.topleft = (int(x), int(y))

        # center the rotated surface inside the full rect
        draw_rect = final.get_rect(center=full_rect.center)

        # Optional: slight downward shift so cropped cards sit nicely
        if crop_ratio < 1.0:
            draw_rect.centery += int((1 - crop_ratio) * height * 0.5)

        screen.blit(final, draw_rect.topleft)
        self.rect = draw_rect
