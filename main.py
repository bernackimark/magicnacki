from pathlib import Path

from models.card import CardUniverse
import pygame as pg

from renderer_pygame.game import Game
from renderer_pygame.scenes.build_deck_scene import BuildDeckScene
from renderer_pygame.scenes.menu_scene import MenuScene
from renderer_pygame.scenes.play_scene import PlayScene


class MyGame(Game):
    def __init__(self, card_univ: CardUniverse):
        super().__init__(width=1500, height=900, title="Magicnacki")

        cursor_img = pg.image.load(Path("assets/cursor.png")).convert_alpha()
        cursor_img = pg.transform.scale(cursor_img, (32, 32))
        cursor = pg.cursors.Cursor((0, 0), cursor_img)  # (0,0) = the top-left is the click point
        pg.mouse.set_cursor(cursor)

        self.card_univ = card_univ

        # Register scenes
        self.scenes.add_scene("menu", MenuScene(self))
        self.scenes.add_scene("build_deck", BuildDeckScene(self))
        self.scenes.add_scene("play", PlayScene(self))
        self.scenes.set_scene("menu", use_fade=False)  # Start in menu

        self.scenes.load_transition_sound("assets/a_Major_7_Sharp_11.mp3")


if __name__ == "__main__":
    cu = CardUniverse(['4E'])
    MyGame(cu).run()
