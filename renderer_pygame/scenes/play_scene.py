import pygame as pg

from renderer_pygame.scenes.scene_abc import Scene


class PlayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.font = pg.font.SysFont("arial", 48)

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_m:
                    self.game.scenes.set_scene("menu", use_fade=True)
                elif event.key == pg.K_q:
                    self.game.running = False

    def update(self, dt):
        pass

    def draw(self):
        self.game.screen.fill("darkslategray")
        text = self.font.render("You are playing Magicnacki; press M for menu", True, "white")
        self.game.screen.blit(text, (100, 250))
        small = self.font.render("Press Q to Quit", True, "lightgray")
        self.game.screen.blit(small, (180, 320))
