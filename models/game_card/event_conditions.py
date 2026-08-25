from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.events_all import Event, AttackEvent, DiesEvent, BlockEvent, UnblockedAttackerEvent, DamageResolvedEvent, \
    DrawCardEvent
    from models.game_card.game_card import GameCard

class EventCondition(ABC):
    @abstractmethod
    def matches(self, gs: GameState, source: GameCard, event: Event) -> bool: ...

class DierIsCreature(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DiesEvent) -> bool:
        return event.card.is_creature

class HostIsDamager(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DamageResolvedEvent) -> bool:
        return event.source is source.host

class OpponentIsDrawer(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DrawCardEvent) -> bool:
        return event.player_id == flip(source.owner_id)

class SelfIsAttacking(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: AttackEvent) -> bool:
        return event.attacker is source

class SelfIsBlocker(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: BlockEvent) -> bool:
        return event.blocker is source

class SelfIsCombatant(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: Event) -> bool:
        return source in gs.card_filter.combatants().result()

class SelfIsDamager(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DamageResolvedEvent) -> bool:
        return event.source is source

class SelfIsDamageReceiver(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DamageResolvedEvent) -> bool:
        return event.target is source

class SelfIsDier(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DiesEvent) -> bool:
        return event.card is source

class SelfIsTapped(EventCondition):
    def matches(self, gs: GameState, source: GameCard, _: Event) -> bool:
        return source.is_tapped

class SelfIsUnblockedAttacker(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: UnblockedAttackerEvent) -> bool:
        return event.attacker is source

class YouAreDrawer(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DrawCardEvent) -> bool:
        return event.player_id is source.owner_id
