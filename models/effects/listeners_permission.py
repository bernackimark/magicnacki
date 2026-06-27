from __future__ import annotations
from typing import TYPE_CHECKING

from models.counter_tokens import PUPA

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.actions.tap_untap import LeaveTapped
from models.effects.base import Listener
from models.events_all import CanBlockQueryEvent, CanAttackQueryEvent, CanTargetQueryEvent, CanCastQueryEvent, \
    CanUntapQueryEvent, UntapCardEvent, AttackEvent
from models.phase_manager import Phase
from models.utils import flip

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

class DoesntUntapAtUntap(Listener):
    """Card does not untap during its owner's untap phase"""
    listens_to = CanUntapQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if event.card is not source or gs.phase_mgr.phase != Phase.UNTAP:
            return
        event.permission = False

class HostDoesntUntapAtUntap(Listener):
    """Host does not untap during its owner's untap phase"""
    listens_to = CanUntapQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if event.card is not source.host or gs.phase_mgr.phase != Phase.UNTAP:
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


class AmrouKithkin(Listener):
    """This creature can't be blocked by creatures with power 3 or greater"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source:
            return
        if event.blocker.power >= 3:
            event.permission = False


class ArtifactWardCanBeBlocked(Listener):
    """Enchanted creature can't be blocked by artifact creatures"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source.host:
            return
        event.permission = False


class ArtifactWardCanBeTargeted(Listener):
    """Enchanted creature can't be the target of abilities from artifact sources"""
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if event.target is not source.host or 'Artifact' not in source.card_types:
            return
        event.permission = False


class ArgothianPixiesCanBeBlocked(Listener):
    """This creature can't be blocked by artifact creatures"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source or 'Artifact' not in event.blocker.card_types:
            return
        event.permission = False


class BogRats(Listener):
    """This creature can't be blocked by Walls"""
    listens_to = CanBlockQueryEvent
    query = 'can_block'

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source or 'Wall' not in event.blocker.card_types:
            return
        event.permission = False


class CityInABottleCantCast(Listener):
    """Players can't cast spells or play lands with a name originally printed in the Arabian Nights expansion"""
    listens_to = CanCastQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanCastQueryEvent) -> None:
        if event.card in gs.card_filter.by_set_code('AN').result():
            event.permission = False


class ElderSpawnCanBeBlocked(Listener):
    """This creature can't be blocked by red creatures"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source or 'R' not in event.blocker.colors:
            return
        event.permission = False


class ElvenRidersCanBeBlocked(Listener):
    """This creature can't be blocked except by Walls and/or creatures with flying"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source:
            return
        if 'Wall' not in event.blocker.card_sub_types or 'Flying' not in event.blocker.keyword_abilities:
            event.permission = False


class EvilEyeOfOrmsByGoreCanBeBlocked(Listener):
    """Can only be blocked by walls"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source or 'Wall' not in event.blocker.card_sub_types:
            return
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


class Fear(Listener):
    """Enchanted creature has fear. (It can't be blocked except by artifact creatures and/or black creatures.)"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        a = event.attacker
        if a.host is not source:
            return
        artifact_creatures = gs.card_filter.on_player_board(flip(a.owner_id)).artifacts().creatures().result()
        black_creatures = gs.card_filter.on_player_board(flip(a.owner_id)).black().creatures().result()
        if event.blocker not in artifact_creatures + black_creatures:
            event.permission = False


class Invisibility(Listener):
    """Enchanted creature can't be blocked except by Walls"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker.host is not source or 'Wall' in event.blocker.card_sub_types:
            return
        event.permission = False


class IronclawOrcs(Listener):
    """This creature can't block creatures with power 2 or greater"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.blocker is not source or event.attacker.power < 2:
            return
        event.permission = False


class JuggernautUnblockableByWalls(Listener):
    """... This creature can't be blocked by Walls"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source or 'Wall' not in event.blocker.card_sub_types:
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


class Meekstone(Listener):
    """Creatures with power 3 or greater don't untap during their controllers' untap steps."""
    listens_to = CanUntapQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if event.card.is_creature and event.card.power >= 3:
            event.permission = False


class Moat(Listener):
    """Creatures without flying can't attack"""
    listens_to = CanAttackQueryEvent
    query = 'can_attack'

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if event.attacker in gs.card_filter.in_play().has('Flying').creatures().result():
            event.permission = False


class Seeker(Listener):
    """Enchanted creature can't be blocked except by artifact creatures and/or white creatures"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        a = event.attacker
        if a.host is not source:
            return
        artifact_creatures = gs.card_filter.on_player_board(flip(a.owner_id)).artifacts().creatures().result()
        white_creatures = gs.card_filter.on_player_board(flip(a.owner_id)).white().creatures().result()
        if event.blocker not in artifact_creatures + white_creatures:
            event.permission = False


class SirensCallCanCast(Listener):
    """Cast this spell only during an opponent's turn, before attackers are declared ..."""
    listens_to = CanCastQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanCastQueryEvent) -> None:
        if gs.turn_mgr.player_turn_idx == event.card.owner_id:
            return
        if gs.phase_mgr.phase >= Phase.DECLARE_ATTACKERS:
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
class CocoonUntap(Listener):
    """Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it"""
    listens_to = CanUntapQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if event.card is not source.host:
            return
        if source.host.counters.get_count(PUPA):
            event.permission = False

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
