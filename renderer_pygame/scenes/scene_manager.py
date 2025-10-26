import pygame as pg

from renderer_pygame.scenes.scene_abc import Scene


class SceneManager:
    """Handles switching between scenes with optional fade transitions."""

    def __init__(self, game):
        self.game = game
        self.scenes = {}
        self.active_scene = None
        self.next_scene = None
        self.fade_alpha = 0
        self.fading = False
        self.fade_speed = 400  # pixels per second (alpha units/sec)
        self.fade_surface = pg.Surface((game.width, game.height))
        self.fade_surface.fill("black")

        # 🔊 Add a transition sound
        self.transition_sound = None  # optional pg.mixer.Sound object

    def load_transition_sound(self, path: str):
        """Load a sound to play during transitions."""
        sound = pg.mixer.Sound(path)
        sound.set_volume(0.2)  # 0.0–1.0
        self.transition_sound = sound

    def add_scene(self, name: str, scene: Scene):
        self.scenes[name] = scene

    def set_scene(self, name: str, use_fade=True):
        """Begin transition to a new scene."""
        if name not in self.scenes:
            raise ValueError(f"Scene '{name}' not found.")
        if self.fading:
            return  # prevent overlapping transitions

        if use_fade and self.active_scene:
            self.fading = True
            self.next_scene = self.scenes[name]
            self.fade_alpha = 0

            # 🔊 Play transition sound once when fade starts
            if self.transition_sound:
                self.transition_sound.play()
        else:
            self.active_scene = self.scenes[name]

    def handle_events(self, events):
        if not self.fading and self.active_scene:
            self.active_scene.handle_events(events)

    def update(self, dt):
        """Handles scene updates and fade logic."""
        if self.fading:
            self.fade_alpha += self.fade_speed * dt
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                # Swap scenes at midpoint of fade
                if self.next_scene:
                    self.active_scene = self.next_scene
                    self.next_scene = None
                # Start fade-out (reverse)
                self.fade_speed *= -1
            elif self.fade_alpha <= 0 and self.fade_speed < 0:
                # Fade finished
                self.fade_alpha = 0
                self.fade_speed *= -1
                self.fading = False
        else:
            if self.active_scene:
                self.active_scene.update(dt)

    def draw(self):
        """Draws the active scene and the fade overlay if active."""
        if self.active_scene:
            self.active_scene.draw()

        if self.fading:
            self.fade_surface.set_alpha(int(self.fade_alpha))
            self.game.screen.blit(self.fade_surface, (0, 0))
