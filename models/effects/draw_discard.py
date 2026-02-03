from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.draw_discard import DiscardCard
from models.effects.base import Effect
from utils import flip

# This follows the new emission system, as opposed to when Effects also knew about their own events
from models.events.events_all import EndStepEvent

# --- GENERIC ---
class DrawCards(Effect):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        if target is None:
            return
        gs.draw(target, self.card_cnt)
        print(f"{source.props.name} has player #{target} draw {self.card_cnt} card(s).")


# --- CARD-SPECIFIC ---
class Braingeyser(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is not None:
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            gs.draw(target, x)

class CursedRackEffect(Effect):
    """Opponent's maximum hand size is four [at their discard phase]"""
    listens_to = EndStepEvent

    def resolve(self, gs: GameState, source: GameCard, target=None):
        opp_id = flip(source.orig_owner_id)
        if gs.player_turn_idx != opp_id:
            return

        hand = gs.hands[opp_id]
        for i in range(len(hand.cards) - 4):
            gs.action_stack.push(DiscardCard(opp_id, gs, hand.cards[0]), gs, False)

class WheelOfFortune(Effect):
    """Each player discards their hand, then draws seven cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for i in (0, 1):
            [DiscardCard(i, gs, card).play() for card in gs.hands[i].cards]
            gs.draw(i, 7)
