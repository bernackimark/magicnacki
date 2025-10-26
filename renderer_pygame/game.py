import os
import sys
from pathlib import Path

import pygame as pg

from renderer_pygame.scenes.scene_manager import SceneManager


class Game:
    """A generic game shell using pygame-ce."""

    def __init__(self, width=800, height=600, title="My Game", fps=60, images_path: str = 'assets/images'):
        pg.init()
        pg.mixer.init()  # 🔊 ensure mixer is ready
        self.width = width
        self.height = height
        self.fps = fps
        self.title = title

        # Core pygame setup
        self.screen = pg.display.set_mode((self.width, self.height))
        pg.display.set_caption(self.title)
        self.clock = pg.time.Clock()

        # Game state
        self.running = True
        self.paused = False
        self.scenes = SceneManager(self)

        # 🖼️ Store loaded images here
        self.images = {}

        # Auto-load all images in a given folder
        self.load_images(images_path)

    # -----------------------------------------------------------------
    # Image loader
    # -----------------------------------------------------------------
    def load_images(self, folder_path: str | Path, recursive: bool = True):
        """Loads images into a nested dictionary structure that mirrors the folder tree."""
        folder = Path(folder_path)
        valid_exts = {".png", ".jpg", ".jpeg", ".gif"}

        if not folder.exists():
            print(f"[Warning] Image folder not found: {folder}")
            return

        def insert_nested(struct: dict, parts: list[str], image_obj):
            """Recursively insert image_obj into struct following the parts list."""
            part = parts[0]
            if len(parts) == 1:
                name = Path(part).stem
                struct[name] = image_obj
            else:
                if part not in struct:
                    struct[part] = {}
                insert_nested(struct[part], parts[1:], image_obj)

        # Choose iteration strategy
        files = folder.rglob("*") if recursive else folder.glob("*")

        for file_path in files:
            if file_path.suffix.lower() in valid_exts and file_path.is_file():
                relative_parts = file_path.relative_to(folder).parts
                try:
                    image = pg.image.load(str(file_path)).convert_alpha()
                    insert_nested(self.images, list(relative_parts), image)
                except Exception as e:
                    print(f"[Error] Failed to load image {file_path.name}: {e}")

        print(f"[Info] Loaded images from {folder}")

        for k, v in self.images.items():
            print(k, v)

    # -------------------------------------------------------------------------
    # Lifecycle hooks — override these in subclasses
    # -------------------------------------------------------------------------
    def handle_events(self):
        """Handle input events (keyboard, mouse, etc)."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key == pg.K_p:
                    self.paused = not self.paused

    def update(self, dt):
        """Update the game logic."""
        pass  # Override in subclass

    def draw(self):
        """Draw everything to the screen."""
        self.screen.fill("black")  # Default background
        pg.display.flip()

    def on_start(self):
        """Called once when the game starts."""
        pass

    def on_quit(self):
        """Called once when the game is quitting."""
        pass

    # -------------------------------------------------------------------------
    # Main loop
    # -------------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            events = pg.event.get()

            # Global event handling
            for event in events:
                if event.type == pg.QUIT:
                    self.running = False
                elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                    self.running = False

            # Delegate to active scene
            if not self.paused and self.scenes.active_scene:
                self.scenes.handle_events(events)
                self.scenes.update(dt)
                self.scenes.draw()

            pg.display.flip()

        self.on_quit()
        pg.quit()
        sys.exit()

