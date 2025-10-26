from abc import ABC, abstractmethod


class Scene(ABC):
    """Abstract base class for all game scenes."""

    def __init__(self, game):
        self.game = game

    @abstractmethod
    def handle_events(self, events): ...
    @abstractmethod
    def update(self, dt): ...
    @abstractmethod
    def draw(self): ...
