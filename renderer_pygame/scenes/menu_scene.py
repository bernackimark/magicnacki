import pygame as pg

from renderer_pygame.scenes.scene_abc import Scene


class MenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.font = pg.font.SysFont("arial", 48)

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_p:
                    self.game.scenes.set_scene("play", use_fade=True)
                elif event.key == pg.K_b:
                    self.game.scenes.set_scene("build_deck", use_fade=True)

                elif event.key == pg.K_q:
                    self.game.running = False

    def update(self, dt):
        pass

    def draw(self):
        self.game.screen.fill("darkslategray")
        text = self.font.render("Press P to Play or B to Build Deck", True, "white")
        self.game.screen.blit(text, (100, 250))
        small = self.font.render("Press Q to Quit", True, "lightgray")
        self.game.screen.blit(small, (180, 320))
