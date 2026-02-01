from __future__ import annotations
from typing import TYPE_CHECKING

from models.damage import DamageReplacement, DamageEvent
from models.effects.base import Effect

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.damage_replacements import MartyrsOfKorlisReplacement

# --- GENERICS ---
class RedirectDamageFromOwnerToCreature(DamageReplacement):
    def __init__(self, damage_source: GameCard, to_creature: GameCard):
        self.damage_source = damage_source
        self.to_creature = to_creature
        self.used = False

    def applies(self, gs: GameState, event: DamageEvent) -> bool:
        if self.used:
            return False
        return (event.source is self.damage_source and event.target is self.to_creature.orig_owner_id
                and event.remaining > 0)

    def replace(self, gs: GameState, event: DamageEvent) -> None:
        # redirect the damage
        event.target = self.to_creature
        self.used = True

class RedirectDamageToOwner(DamageReplacement):
    def __init__(self, damage_source: GameCard, to_creature: GameCard):
        self.damage_source = damage_source
        self.to_creature = to_creature
        self.used = False

    def applies(self, gs: GameState, event: DamageEvent) -> bool:
        if self.used:
            return False
        return event.source is self.damage_source and event.target is self.to_creature and event.remaining > 0

    def replace(self, gs: GameState, event: DamageEvent) -> None:
        # redirect the damage
        event.target = self.to_creature.orig_owner_id
        self.used = True

class JadeMonolith(Effect):
    """{1}: Redirect next damage from a chosen source to a chosen creature onto you."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        replacement = RedirectDamageToOwner(source, target)
        gs.damage_replacements.append(replacement)


class MartyrsOfKorlisDamageReplacement:
    def apply(self, gs: GameState, source: GameCard):
        gs.damage_replacements.append(MartyrsOfKorlisReplacement(source))

    def remove(self, gs: GameState, source: GameCard):
        gs.damage_replacements = [r for r in gs.damage_replacements
                                  if not (isinstance(r, MartyrsOfKorlisReplacement) and r.card is source)]
