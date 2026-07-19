from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from models.counter_tokens import PUPA, SLEEP

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Listener
from models.events_all import CanBlockQueryEvent, CanAttackQueryEvent, CanTargetQueryEvent, CanCastQueryEvent, \
    CanUntapQueryEvent, UntapCardEvent, AttackEvent, CanEnterUntapPhaseQueryEvent, CanUntapAtUntapPhaseQueryEvent

"""
These are Effects that listens for Events that are XXQueryEvent
These query-style effects must have a class-level attribute 'listens_to', implement on_event(gs, card, XXQueryEvent).
It may set the event.permission = False
"""


# --- GENERICS ---
class CantBeTargetedByAuras(Listener):
    """Card can't host an aura"""
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if event.target is not source or 'Aura' not in event.source.card_sub_types:
            return
        event.permission = False

class DoesntUntapAtUntap(Listener):
    """Card does not untap during its owner's untap phase"""
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if gs.player_turn_idx == event.card.owner_id and event.card in [self.card_filter_func(gs, source)]:
            event.permission = False

class DoesntUntapAtUntapIfItAttackedLastTurn(Listener):
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if self.target.owner_id != gs.player_turn_idx or self.target is not event.card:
            return
        p_last_turn_num = gs.turn_mgr.get_players_last_turn_num(self.target.owner_id)
        for e, turn_num in gs.event_mgr.events[::-1]:
            if turn_num == p_last_turn_num:
                if isinstance(e, AttackEvent) and e.attacker is self.target:
                    event.permission = False

class HostCanAttack(Listener):
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if source.host is event.attacker:
            event.permission = True

class HostCantAttack(Listener):
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if source.host is event.attacker:
            event.permission = False


class HostCantBeTargetedByAuras(Listener):
    """Host can't host an aura"""
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if event.target is not source.host or 'Aura' not in event.source.card_sub_types:
            return
        event.permission = False

class NoAttacksAllowedEOT(Listener):
    """No attacks are allowed this turn"""
    listens_to = CanAttackQueryEvent
    expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        event.permission = False

class SkipUntapPhase(Listener):
    """Player skips their untap phase"""
    listens_to = CanEnterUntapPhaseQueryEvent

    def __init__(self, skipped_player_id: int | None = None):
        self.skipped_player_ids = (skipped_player_id, ) if skipped_player_id is not None else (0, 1)

    def on_event(self, gs: GameState, source: GameCard, event: CanEnterUntapPhaseQueryEvent) -> None:
        if event.active_player not in self.skipped_player_ids:
            return
        event.permission = False

class UnblockableEOT(Listener):
    """Target creature can't be blocked this turn"""
    listens_to = CanBlockQueryEvent
    expires = 'EOT'

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is self.target:
            event.permission = False

class UnblockableCondition(Listener):
    """If attacker is in the attacker func & blocker is in the blocker func, block is illegal;
    attacker func must return a single GameCard"""
    listens_to = CanBlockQueryEvent

    def __init__(self, attacker_func: Callable, blockable_func: Callable):
        self.attacker_func = attacker_func
        self.blocker_func = blockable_func

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker == self.attacker_func(gs, source) and event.blocker in self.blocker_func(gs, source):
            event.permission = False

class WalkRuleRemoved(Listener):
    """Creatures with a landwalk can be blocked as though they didn't have that landwalk."""
    listens_to = CanBlockQueryEvent

    def __init__(self, walk_type: str):
        self.walk_type = walk_type

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if self.walk_type not in event.attacker.keyword_abilities:
            return None
        event.permission = True  # a hard-confirm that the block is allowed


# --- CARD-SPECIFIC ---
class AkronLegionnaire(Listener):
    """Except for creatures named Akron Legionnaire and artifact creatures, creatures you control can't attack"""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        a = event.attacker
        if a not in gs.card_filter.creatures().on_player_board(source.owner_id).result():
            return
        artifact_creatures = gs.card_filter.on_player_board(a.owner_id).creatures().artifacts().result()
        akron_legionnaires = gs.card_filter.on_player_board(a.owner_id).by_slug('akron-legionnaire').result()
        if a not in artifact_creatures + akron_legionnaires:
            event.permission = False

class ArtifactWardCanBeTargeted(Listener):
    """Enchanted creature can't be the target of abilities from artifact sources"""
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if event.target is not source.host or 'Artifact' not in source.card_types:
            return
        event.permission = False

class CityInABottleCantCast(Listener):
    """Players can't cast spells or play lands with a name originally printed in the Arabian Nights expansion"""
    listens_to = CanCastQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanCastQueryEvent) -> None:
        if event.card in gs.card_filter.by_set_code('AN').result():
            event.permission = False

class EvilEyeOfOrmsByGoreMyNonEyeNoAttack(Listener):
    """Non-Eye creatures you control can't attack."""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        a = event.attacker
        if source.owner_id != a.owner_id:
            return
        if a not in gs.card_filter.on_player_board(a.owner_id).creatures().by_sub_type('Eye').result():
            event.permission = False

class IronclawOrcs(Listener):
    """This creature can't block creatures with power 2 or greater"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.blocker is not source or event.attacker.power < 2:
            return
        event.permission = False

class LivonyaSilone(Listener):
    """Legendary landwalk (This creature can't be blocked as long as defending player controls a legendary land.)"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source:
            return
        if gs.card_filter.on_player_board(event.blocker.owner_id).legendary().lands().result():
            event.permission = False

class Moat(Listener):
    """Creatures without flying can't attack"""
    listens_to = CanAttackQueryEvent
    query = 'can_attack'

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if event.attacker in gs.card_filter.in_play().has('Flying').creatures().result():
            event.permission = False

class SpectralCloak(Listener):
    """Enchanted creature has shroud as long as it's untapped. (It can't be the target of spells or abilities.)"""
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if event.target is not source.host:
            return
        event.permission = False

class TowerOfCoireallEOT(Listener):
    """Target creature can't be blocked by Walls this turn"""
    listens_to = CanBlockQueryEvent
    query = 'can_block'
    expires = 'EOT'

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not self.target or event.blocker not in gs.card_filter.walls().result():
            return
        event.permission = False


# --- CAN UNTAP QUERY EVENT ---
class DampingField(Listener):
    """Players can't untap more than one artifact during their untap steps"""
    listens_to = CanUntapQueryEvent
    query = 'can_untap'

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if not event.card.is_artifact:
            return
        # TODO: this should probably enter a flow where user can declare which one card they want to untap
        events = gs.event_mgr.get_events(gs.turn_mgr.turn_number, UntapCardEvent)
        if [e for e in events if e.card.is_artifact]:
            event.permission = False

class GoblinRockSledUntap(Listener):
    """This creature doesn't untap during your untap step if it attacked during your last turn"""
    listens_to = CanUntapQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if source is not event.card:
            return
        p_last_turn_num = gs.turn_mgr.get_players_last_turn_num(source.owner_id)
        for e, turn_num in gs.event_mgr.events[::-1]:
            if turn_num == p_last_turn_num:
                if isinstance(e, AttackEvent) and e.attacker is source:
                    event.permission = False

class Smoke(Listener):
    """Players can't untap more than one creature during their untap steps"""
    listens_to = CanUntapQueryEvent
    query = 'can_untap'

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if not event.card.is_creature:
            return
        # TODO: this should probably enter a flow where user can declare which one card they want to untap
        events = gs.event_mgr.get_events(gs.turn_mgr.turn_number, UntapCardEvent)
        if [e for e in events if e.card.is_creature]:
            event.permission = False

class WinterOrb(Listener):
    """As long as this artifact is untapped, players can't untap more than one land during their untap steps"""
    listens_to = CanUntapQueryEvent
    query = 'can_untap'

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if source.is_tapped or 'Land' not in event.card.card_types:
            return
        # TODO: this should probably enter a flow where user can declare which one card they want to untap
        events = gs.event_mgr.get_events(gs.turn_mgr.turn_number, UntapCardEvent)
        if [e for e in events if e.card.is_land]:
            event.permission = False


# --- CAN UNTAP AT UNTAP QUERY EVENT ---
class CocoonUntap(Listener):
    """Host doesn't untap during its controller's untap step if it has a pupa counter on it."""
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if event.card != source.host or event.card != gs.player_turn_idx:
            return
        if source.host.counters.get_count(PUPA):
            event.permission = False

class Meekstone(Listener):
    """Creatures with power 3 or greater don't untap during their controllers' untap steps."""
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if event.card.owner_id == event.active_player and event.card.is_creature and event.card.power >= 3:
            event.permission = False

class VenarianGoldAtUntap(Listener):
    """Host doesn't untap during its controller's untap step if it has a sleep counter on it."""
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if event.card != source.host or event.card.owner_id != event.active_player:
            return
        if source.host.counters.get_count(SLEEP):
            event.permission = False
