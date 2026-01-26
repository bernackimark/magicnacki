from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.draw_discard import DiscardCard
from models.effects.base import Effect
from utils import flip


def cursed_rack_at_discard_phase():
    """Opponent's maximum hand size is four [at their discard phase]"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            opp_id = flip(source.orig_owner_id)
            if gs.player_turn_idx != opp_id:
                return
            hand = gs.hands[opp_id]
            if len(hand.cards) > 4:
                for c in hand.cards:
                    gs.action_stack.push(DiscardCard(opp_id, gs, c), gs, False)
    return E()


def ancestral_recall_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
            """target = player_id whose lands should be tapped"""
            if target is None:
                return
            gs.draw(gs.hands[target], gs.decks[target].cards, 3)
            print(f"Ancestral Recall has player #{target} draw three cards.")
    return E()


def braingeyser_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: int = None):
            if target is not None:
                x = getattr(source, 'variable_x', 0)  # read X chosen when casting
                gs.draw(gs.hands[target], gs.decks[target].cards, x)
    return E()


def wheel_of_fortune_on_cast():
    """Each player discards their hand, then draws seven cards"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for i in (0, 1):
                [DiscardCard(i, gs, card).play() for card in gs.hands[i].cards]
                gs.draw(gs.hands[i], gs.decks[i].cards, 7)
    return E()
