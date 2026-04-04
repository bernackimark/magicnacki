from game_state import GameState
from models.events_all import LifeLossEvent, LifeGainEvent
from models.game_card import GameCard


class ScoreManager:
    def __init__(self, life: tuple[int, int] = (20, 20), poison_death_amt: int = 10):
        self.life = list(life)
        self._poison = [0, 0]
        self.poison_death_amt = poison_death_amt

    @property
    def poison_counters(self) -> list[int]:
        return self._poison

    def add_poison_counter(self, p_idx: int, cnt: int = 1):
        self._poison[p_idx] += cnt

    def increment_life(self, p_id: int, amt: int, source: GameCard | None, gs: GameState):
        """Increments player life; no event is raised/emitted, as there's seemingly no cards w increased life effects;
        some implementers of increment_life don't capture the source, so it may be None"""
        event = LifeGainEvent(p_id, amt, source)
        if event.amt <= 0:
            return
        gs.event_mgr.emit(event, gs)
        self._life[p_id] += amt
        print(f"Increasing player #{p_id}'s life by {amt}. Life is now at {self.life}")

    def decrement_life(self, p_id: int, amt: int, source: GameCard, gs: GameState):
        """Should ONLY be called from GameState.apply_damage();
        creates LifeLossEvent; if amt <=0, skip; emit, decrement player life"""
        event = LifeLossEvent(p_id, amt, source)
        if event.amt <= 0:
            return
        gs.event_mgr.emit(event, gs)
        self.life[p_id] -= amt
        print(f"{source.props.name} deals {amt} damage to player #{p_id}. Life is now at {self.life}")