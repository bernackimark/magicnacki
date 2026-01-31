from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard

from models.effects.base import Effect


def creature_bond_on_leave():
    class E(Effect):
        event = 'leave'
        # need this instance that uses the leave event, because it DOES something on leave, not just the removal of a
        # continuous effect

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: i think this is wrong; i think it's only if creature goes to graveyard
            # creature leaving: for every attached aura that is creature-bond, do life loss to creature's owner
            for aura in target.modifiers.auras:
                if aura.props.slug == 'creature-bond':
                    gs.decrement_life(target.orig_owner_id, target.props.toughness, aura)
                    # TODO: use apply_damage instead of directly calling decrement_life; make decrement_life private?
    return E()

