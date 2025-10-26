from card import CardUniverse

from renderer_pygame.game import Game
from renderer_pygame.scenes.build_deck_scene import BuildDeckScene
from renderer_pygame.scenes.menu_scene import MenuScene
from renderer_pygame.scenes.play_scene import PlayScene


class MyGame(Game):
    def __init__(self, card_univ: CardUniverse):
        super().__init__(width=1500, height=900, title="Magicnacki")

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
