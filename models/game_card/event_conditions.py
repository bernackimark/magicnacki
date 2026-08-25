from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from models.events_all import Event, AttackEvent, DiesEvent, BlockEvent, UnblockedAttackerEvent, \
    DamageResolvedEvent, DrawCardEvent, CastResolvedEvent
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

class EventCondition(ABC):
    @abstractmethod
    def matches(self, gs: GameState, source: GameCard, event: Event) -> bool: ...


class CardIsHost(EventCondition):
    """This can be used by any Event with the 'card' attr"""
    def matches(self, gs: GameState, source: GameCard, event: Event) -> bool:
        return event.card is source.host  # type: ignore

class CardIsSource(EventCondition):
    """This can be used by any Event with the 'card' attr"""
    def matches(self, gs: GameState, source: GameCard, event: Event) -> bool:
        return event.card is source  # type: ignore

class CastCardIsArtifact(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> bool:
        return event.card.is_artifact

class CastCardIsBlack(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> bool:
        return event.card.is_black

class CastCardIsBlue(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> bool:
        return event.card.is_blue

class CastCardIsGreen(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> bool:
        return event.card.is_green

class CastCardIsRed(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> bool:
        return event.card.is_red

class CastCardIsWhite(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> bool:
        return event.card.is_white

class CasterIsOpp(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> bool:
        return event.owner_id != source.owner_id

class DierIsCreature(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DiesEvent) -> bool:
        return event.card.is_creature

class DierIsYourArtifact(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DiesEvent) -> bool:
        return event.card.is_artifact and source.owner_id == event.card.owner_id

class HostIsDamager(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DamageResolvedEvent) -> bool:
        return event.source is source.host

class IsYourTurn(EventCondition):
    def matches(self, gs: GameState, source: GameCard, _: Event) -> bool:
        return gs.turn_mgr.player_turn_idx == source.owner_id

class NoCreaturesInPlay(EventCondition):
    def matches(self, gs: GameState, source: GameCard, _: Event) -> bool:
        return not gs.card_filter.creatures().in_play().result()

class OpponentIsDrawer(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: DrawCardEvent) -> bool:
        return event.player_id == flip(source.owner_id)

class SelfDamagedOpponent(EventCondition):
    """Returns true if source dealt damage to opp this turn"""
    def matches(self, gs: GameState, source: GameCard, _: Event) -> bool:
        for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent):
            if e.source is source and e.target == flip(source.owner_id):
                return True
        return False

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
