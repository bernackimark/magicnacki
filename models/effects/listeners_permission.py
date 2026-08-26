from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Any

from models.constants import KW, Zone
from models.game_card.counter_tokens import PUPA
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Listener
from models.events_all import CanBlockQueryEvent, CanAttackQueryEvent, CanTargetQueryEvent, CanCastQueryEvent, \
    CanUntapQueryEvent, UntapCardEvent, AttackEvent, CanEnterUntapPhaseQueryEvent, CanUntapAtUntapPhaseQueryEvent, \
    CanRegenerateQueryEvent, CastResolvedEvent, ZoneChangeEvent

"""
These are Effects that listens for Events that are XXQueryEvent
These query-style effects must have a class-level attribute 'listens_to', implement on_event(gs, card, XXQueryEvent).
It may set the event.permission = False
"""


# --- GENERICS ---
class AttackerCountMax(Listener):
    """Only allows X attackers per turn"""
    listens_to = CanAttackQueryEvent

    def __init__(self, max_cnt: int):
        self.max_cnt = max_cnt

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if len(gs.card_filter.attackers().result()) >= self.max_cnt:
            event.permission = False

class BlockerCountMax(Listener):
    """Only allows X blockers per turn"""
    listens_to = CanBlockQueryEvent

    def __init__(self, max_cnt: int):
        self.max_cnt = max_cnt

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if len(gs.card_filter.blockers().result()) >= self.max_cnt:
            event.permission = False

class CanAttackEOT(Listener):
    """Card, which may otherwise not be permitted to attack, can attack this turn"""
    listens_to = CanAttackQueryEvent
    expires = 'EOT'

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if event.attacker is not self.target:
            return
        event.permission = True

class CantAttack(Listener):
    listens_to = CanAttackQueryEvent

    def __init__(self, applies_to_func: Callable[[GameState, GameCard], GameCard] = None,
                 target: GameCard | None = None):
        self.applies_to_func = applies_to_func
        self.target = target

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        if not self.applies_to_func and self.target is None:
            self.target = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        card = self.applies_to_func(gs, source) if self.applies_to_func else self.target
        if event.attacker is not card:
            return
        event.permission = False

class CantBeTargetedByAuras(Listener):
    """Card can't host an aura"""
    listens_to = CanTargetQueryEvent

    def __init__(self, protected_card_func: Callable[[GameState, GameCard], GameCard] = None,
                 protected_card: GameCard | None = None, condition_func: Callable[[GameState, GameCard], bool] = None):
        self.protected_card_func = protected_card_func
        self.protected_card = protected_card
        self.condition_func = condition_func

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        if not self.protected_card_func and self.protected_card is None:
            self.protected_card = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if 'Aura' not in event.source.card_sub_types:
            return
        protected_cards = [self.protected_card] if self.protected_card else self.protected_card_func(gs, source)
        if event.target not in protected_cards:
            return
        if self.condition_func and not self.condition_func(gs, source):
            return
        event.permission = False

class CantCastAppliesTo(Listener):
    """A card matching the applies to func cannot be cast"""
    listens_to = CanCastQueryEvent

    def __init__(self, applies_to_func: Callable[[GameState, GameCard], list[GameCard | None]]):
        self.applies_to_func = applies_to_func

    def on_event(self, gs: GameState, source: GameCard, event: CanCastQueryEvent) -> None:
        applies_to_cards = self.applies_to_func(gs, source)
        if event.card in applies_to_cards:
            event.permission = False

class CantCastEOT(Listener):
    listens_to = CanCastQueryEvent
    expires = 'EOT'

    def __init__(self, card: GameCard):
        self.card = card

    def on_event(self, gs: GameState, source: GameCard, event: CanCastQueryEvent) -> None:
        if event.card is not self.card:
            return
        event.permission = False

class DoesntUntapAtUntap(Listener):
    """Card does not untap during its owner's untap phase"""
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]] = None,
                 target: GameCard | None = None):
        self.card_filter_func = card_filter_func
        self.target = target

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        if not self.card_filter_func and self.target is None:
            self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        affected_cards = self.card_filter_func(gs, source) if self.target is None else self.target
        if not isinstance(affected_cards, list):
            affected_cards = [affected_cards]
        if gs.player_turn_idx == event.card.owner_id and event.card in affected_cards:
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

    def __init__(self, target: GameCard | None = None):
        self.target = target

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        if self.target is None:
            self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if self.target is event.attacker:
            event.permission = True

class HostCantAttack(Listener):
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if source.host is event.attacker:
            event.permission = False

class HostCantBeTargetedBySpells(Listener):
    """WARNING: because CanTargetQueryEvent doesn't carry .effect, I'm backing into 'is the source a spell'?"""
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if event.target is not source.host or event.source.zone == Zone.BATTLEFIELD:
            return
        event.permission = False

class NoAttacksAllowedEOT(Listener):
    """No attacks are allowed this turn"""
    listens_to = CanAttackQueryEvent
    expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        event.permission = False

class PreventRegenerationEOT(Listener):
    """Target creature can't regenerate this turn."""
    listens_to = CanRegenerateQueryEvent
    expires = 'EOT'

    def __init__(self, target: GameCard | None = None):
        self.target = target

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        if not self.target:
            self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: CanRegenerateQueryEvent):
        if event.card is self.target:
            event.permission = False

class RegenerateSelf(Listener):
    """This creature explicitly regenerates upon destroy() entry. This is rare."""
    listens_to = CanRegenerateQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanRegenerateQueryEvent):
        if event.card is source:
            event.permission = True

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

    def __init__(self, target: GameCard | None = None):
        self.target: GameCard | None = target

    def initialize(self, gs: GameState, source: GameCard, targets: list[GameCard | int | None]):
        self.target = targets[0]

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

class Arboria(Listener):
    """Creatures can only attack a player who, in their last turn,
    cast a spell or put a nontoken permanent onto the battlefield"""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        opp = flip(event.attacker.owner_id)
        p_most_recent_turn = gs.turn_mgr.most_recent_turn_started[opp]
        events_on_players_last_turn = gs.event_mgr.get_events(p_most_recent_turn)
        for e in events_on_players_last_turn:
            if isinstance(e, CastResolvedEvent) and e.owner_id == opp and not e.card.is_land:
                return
            if (isinstance(e, ZoneChangeEvent) and e.card.owner_id == opp and not e.card.is_land
                    and not e.card.is_token and e.to_zone == Zone.BATTLEFIELD):
                return
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

class CocoonUntap(Listener):
    """Host doesn't untap during its controller's untap step if it has a pupa counter on it."""
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if event.card != source.host or event.card.owner_id != gs.player_turn_idx:
            return
        if source.counters.get_count(PUPA):
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

class EvilEyeOfOrmsByGoreMyNonEyeNoAttack(Listener):
    """Non-Eye creatures you control can't attack."""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        a = event.attacker
        if source.owner_id != a.owner_id:
            return
        if a not in gs.card_filter.on_player_board(a.owner_id).creatures().by_sub_type('Eye').result():
            event.permission = False

class GoblinRockSledCanAttack(Listener):
    """This creature can't attack unless defending player controls a Mountain"""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if not gs.card_filter.in_play().mountains().on_player_board(flip(source.owner_id)).result():
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

class IronclawOrcs(Listener):
    """This creature can't block creatures with power 2 or greater"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.blocker is not source or event.attacker.power < 2:
            return
        event.permission = False

class IslandSanctuaryRestriction(Listener):
    """You can only be attacked fliers or Islandwalkers"""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if event.attacker == source.owner_id:
            return
        if KW.FLYING in event.attacker.keyword_abilities:
            return
        if KW.ISLANDWALK in event.attacker.keyword_abilities:
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

class Lure(Listener):
    """All creatures able to block host do so"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source.host:
            return
        if gs.perm_querier.can_block(event.blocker, event.attacker):
            event.permission = True

class MarblePriestForcesBlock(Listener):
    """All Walls able to block this creature do so ..."""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source or 'Wall' not in event.blocker.card_sub_types:
            return
        if gs.perm_querier.can_block(event.blocker, event.attacker):
            event.permission = True

class Meekstone(Listener):
    """Creatures with power 3 or greater don't untap during their controllers' untap steps."""
    listens_to = CanUntapAtUntapPhaseQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if event.card.owner_id == event.active_player and event.card.is_creature and event.card.power >= 3:
            event.permission = False

class Moat(Listener):
    """Creatures without flying can't attack"""
    listens_to = CanAttackQueryEvent
    query = 'can_attack'

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if event.attacker in gs.card_filter.in_play().has(KW.FLYING).creatures().result():
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

class WallOfDustAttackerCantAttackNextTurn(Listener):
    """... can't attack during its controller's next turn"""
    listens_to = CanAttackQueryEvent

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if event.attacker is not self.target:
            return
        event.permission = False
        gs.event_mgr.unregister_specific_effect(self)
        # TODO: this needs expires = 'After Owner Next Turn'

class WinterOrb(Listener):
    """As long as this artifact is untapped, players can't untap more than one land during their untap steps"""
    listens_to = CanUntapAtUntapPhaseQueryEvent
    query = 'can_untap'

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapAtUntapPhaseQueryEvent) -> None:
        if source.is_tapped or 'Land' not in event.card.card_types:
            return
        # TODO: this should probably enter a flow where user can declare which one card they want to untap
        events = gs.event_mgr.get_events(gs.turn_mgr.turn_number, UntapCardEvent)
        if [e for e in events if e.card.is_land]:
            event.permission = False
