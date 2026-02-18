from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from models.events_all import ZoneChangeEvent, EndStepEvent, TapCardEvent
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard


from models.counter_tokens import STORAGE, PLUS_ONE_ZERO, PLUS_ZERO_ONE, PLUS_ONE, \
    PUPA, CounterType, CHARGE, MINUS_ZERO_TWO
from models.effects.base import Effect

# --- GENERICS ---
class AddCounter(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        source.counters.add_counter(self.counter_type, self.cnt)

class AddCounterAtEndStep(Effect):
    """Add counter to target if it is still on the battlefield"""
    listens_to = EndStepEvent

    def __init__(self, source: GameCard, target: GameCard, counter_type: CounterType, cnt: int = 1):
        self.source = source
        self.target = target
        self.counter_type = counter_type
        self.cnt = cnt

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if self.target.zone != Zone.BATTLEFIELD:
            return
        self.target.counters.add_counter(self.counter_type, self.cnt)
        gs.unregister_specific_effect(self)

class AddCounterToHost(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        source.attached_to.counters.add_counter(self.counter_type, self.cnt)

class AddCountersOnHostTurn(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.player_turn_idx != source.attached_to.owner_id:
            return
        source.attached_to.counters.add_counter(self.counter_type, self.cnt)

class ManaBatteriesAddMana(Effect):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, target=None, x_value=None):
        print('XXX', x_value)
        source.counters.remove_counter(CHARGE, x_value)
        gs.mana_pools[source.owner_id].add_floating(self.color, 1 + x_value)

class RemoveCountersOnHostTurn(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.player_turn_idx != source.attached_to.owner_id:
            return
        source.attached_to.counters.remove_counter(self.counter_type, self.cnt)

class RemovePlusOneZeroFromCombatant(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if source in gs.card_filter.combatants().result():
            source.counters.remove_counter(PLUS_ONE_ZERO)

class AddCountersYourTurnOnly(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None, x_value: int = None):
        if gs.player_turn_idx != s.owner_id:
            return
        cnt = self.cnt if x_value is None else x_value
        s.counters.add_counter(self.counter_type, cnt)

class AddCountersIfAnyCreatureDied(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if gs.cards_that_died_this_turn:
            s.counters.add_counter(self.counter_type, self.cnt)

class AddCounterPerCreatureDeath(Effect):
    def __init__(self, counter_type: CounterType):
        self.counter_type = counter_type

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if death_cnt := len(gs.cards_that_died_this_turn) > 0:
            s.counters.add_counter(self.counter_type, death_cnt)

class XZeroOneCountersByManaValue(Effect):
    """Put X +0/+1 counters on target creature, where X is that creature's mana value"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.counters.add_counter(PLUS_ZERO_ONE, target.props.casting_weight)

# --- CARD-SPECIFIC ---
class CitanulDruid(Effect):
    """Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or 'Artifact' not in event.card.props.card_types:
            return
        source.counters.add_counter(PLUS_ONE)

class CityOfShadowsAA1(Effect):
    """{T}, Exile a creature you control: Put a storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        source.counters.add_counter(STORAGE)

class CityOfShadowsAA2(Effect):
    """{T}: Add {C} for each storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        cnt = len(source.counters.get_count(STORAGE))
        gs.mana_pools[source.orig_owner_id].add_floating('C', cnt)

class CocoonCast(Effect):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        target.tap(gs)
        source.counters.add_counter(PUPA, 3)

class RockHydraCast(Effect):
    """This creature enters with X +1/+1 counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
            source.counters.add_counter(PLUS_ONE, x)

class SpiritShackle(Effect):
    """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.attached_to:
            return
        s.attached_to.counters.add_counter(MINUS_ZERO_TWO)
