from pathlib import Path

from deck_builder.build_deck import Deck, DeckBuilder, OLD_SCHOOL_DB_RULE_SET
from engine import Engine, create_engine_from_json
from game_state import GameState
from models.card import CardUniverse
import pygame as pg

from models.constants import Mulligan
from models.match_manager import MatchManager
from players import ConsolePlayer
from renderer_pygame.game import Game
from renderer_pygame.scenes.build_deck_scene import BuildDeckScene
from renderer_pygame.scenes.menu_scene import MenuScene
from renderer_pygame.scenes.play_scene import PlayScene
from renderers import ConsoleRenderer


class MyGame(Game):
    def __init__(self, card_univ: CardUniverse, eng: Engine, p_idx: int = 0):
        super().__init__(width=1520, height=920, title="Magicnacki")

        cursor_img = pg.image.load(Path("renderer_pygame/assets/cursor.png")).convert_alpha()
        cursor_img = pg.transform.scale(cursor_img, (32, 32))
        cursor = pg.cursors.Cursor((0, 0), cursor_img)  # (0,0) = the top-left is the click point
        pg.mouse.set_cursor(cursor)

        self.card_univ = card_univ
        self.engine = eng
        self.p_idx = p_idx

        # Register scenes
        self.scenes.add_scene("menu", MenuScene(self))
        self.scenes.add_scene("build_deck", BuildDeckScene(self))
        self.scenes.add_scene("play", PlayScene(self, self.engine, self.p_idx))
        self.scenes.set_scene("menu", use_fade=False)  # Start in menu

        self.scenes.load_transition_sound(Path("renderer_pygame/assets/a_Major_7_Sharp_11.mp3"))


if __name__ == "__main__":
    cu = CardUniverse(['1E'])
    engine = create_engine_from_json('testing/game_testing_settings.json', 'py_game_testing_setup_a', True)
    MyGame(cu, engine).run()
