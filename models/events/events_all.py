from models.events.base import Event

class EndStepEvent(Event):
    def __init__(self, active_player: int):
        self.active_player = active_player
