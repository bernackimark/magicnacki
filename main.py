from pathlib import Path

from deck_builder.build_deck import Deck, DeckBuilder, OLD_SCHOOL_DB_RULE_SET
from engine import Engine
from game_state import GameState
from models.card import CardUniverse
import pygame as pg

from players import ConsolePlayer
from renderer_pygame.game import Game
from renderer_pygame.scenes.build_deck_scene import BuildDeckScene
from renderer_pygame.scenes.menu_scene import MenuScene
from renderer_pygame.scenes.play_scene import PlayScene
from renderers import ConsoleRenderer


class MyGame(Game):
    def __init__(self, card_univ: CardUniverse, engine: Engine):
        super().__init__(width=1500, height=900, title="Magicnacki")

        cursor_img = pg.image.load(Path("renderer_pygame/assets/cursor.png")).convert_alpha()
        cursor_img = pg.transform.scale(cursor_img, (32, 32))
        cursor = pg.cursors.Cursor((0, 0), cursor_img)  # (0,0) = the top-left is the click point
        pg.mouse.set_cursor(cursor)

        self.card_univ = card_univ
        self.engine = engine

        # Register scenes
        self.scenes.add_scene("menu", MenuScene(self))
        self.scenes.add_scene("build_deck", BuildDeckScene(self))
        self.scenes.add_scene("play", PlayScene(self, self.engine))
        self.scenes.set_scene("menu", use_fade=False)  # Start in menu

        self.scenes.load_transition_sound(Path("renderer_pygame/assets/a_Major_7_Sharp_11.mp3"))


def create_engine():
    import json
    with open('testing/cards_for_game_testing.json', 'r') as f:
        data = json.load(f)

    universe = CardUniverse(data['universe'])
    deck_0 = data['deck_0']
    deck_1 = data['deck_1']
    if data['starting_deck'] == 1:
        deck_0, deck_1 = deck_1, deck_0

    decks = []
    for i, cards in enumerate((deck_0, deck_1)):
        deck_builder = DeckBuilder(OLD_SCHOOL_DB_RULE_SET, i)
        for card_slug, qty in cards:
            for _ in range(qty):
                deck_builder.add_card_by_slug(card_slug)
        deck: Deck = deck_builder.complete_deck()
        decks.append(deck)

    # for speed of testing, reduce all cards' casting costs
    for d in decks:
        for c in d.cards:
            if not c.casting_cost:
                continue
            if c.casting_cost[-1] not in ('B', 'U', 'G', 'R', 'W'):
                c.casting_cost = '1'
            else:
                c.casting_cost = c.casting_cost[-1] if 'X' not in c.casting_cost else f'X{c.casting_cost[-1]}'

    # create players
    players = [ConsolePlayer(0, 'Mark', False), ConsolePlayer(1, 'Bull', False)]

    e = Engine(players=players,
               renderer=ConsoleRenderer(),
               gs=GameState(len(players), 0, decks=decks))
    return e


if __name__ == "__main__":
    cu = CardUniverse(['4E'])
    engine = create_engine()
    MyGame(cu, engine).run()
