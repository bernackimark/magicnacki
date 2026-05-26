from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import PayManaOrTakeDamage
from models.effects.base import Effect
from models.events_all import AttackEvent, BlockEvent
from models.modifiers import PTMod

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class CavePeopleAttackPump(Effect):
    """Whenever this creature attacks, it gets +1/-2 until end of turn ..."""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker is not s:
            return
        event.attacker.modifiers.items.append(PTMod(s=s, p_adj=1, t_adj=-2, expires='EOT'))


class HasranOgress(Effect):
    """Whenever this creature attacks, it deals 3 damage to you unless you pay {2}"""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: AttackEvent):
        if event.attacker is not s:
            return
        gs.action_stack.push(PayManaOrTakeDamage(s.owner_id, gs, s, '2', 3), gs, False)


class MijaeDjinn(Effect):
    """Whenever this creature attacks, flip a coin. If you lose the flip, remove this creature from combat and tap it"""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: AttackEvent):
        if event.attacker is not s:
            return
        result = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        print(f'The result of the random event was: {result}')
        if result == 'tails':
            gs.remove_from_combat(s)
            gs.tap_card(s)
