from __future__ import annotations
from copy import deepcopy
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ..events_all import ModQueryEvent, TapCardEvent, UntapCardEvent

if TYPE_CHECKING:
    from game_state import GameState
    from .card import Card
    # from ..effects.base import EffSpec, ActivatedAbility

from .slug_effect_map import INVOCATIONS
from ..effects.base import EffSpec, ActivatedAbility
from models.counter_tokens import Counters
from models.modifiers import Modifiers, KWAMod
from models.zone import Zone


class GameCard:
    def __init__(self, props: Card, orig_owner_id: int, is_token: bool = False, colors: str = ''):
        self.id_ = str(uuid4())
        self.props: Card = props
        self._orig_owner_id: int = orig_owner_id
        self._owner_id: int = orig_owner_id
        self.game_state: GameState | None = None
        self.turn_entered_for_owner: int | None = None
        self.casting_cost: str = self.props.casting_cost[:] if self.props.casting_cost else None
        self._card_types: list[str] = self.props.card_types.copy()
        self._card_sub_types: list[str] = self.props.card_sub_types.copy()
        self._colors: str = colors or self.props.colors[:]
        self.is_token: bool = is_token
        self.is_tapped: bool = False
        self.is_face_up: bool = False
        self.host: GameCard | None = None
        self.auras: list[GameCard | None] = []
        self.modifiers = Modifiers()
        self.counters = Counters()

        self.zone = Zone.LIBRARY

        self.damage_dealt_this_turn: int = 0  # not sure that these belong here
        self.damage_received_this_turn: int = 0

        self.base_pt = (self.props.power, self.props.toughness)
        self._base_kwa = tuple(self.props.keyword_abilities)

        self.extras: dict[str, Any] = {}  # declarations of X, color upon entry, etc

        self.abilities: list[EffSpec | None] = deepcopy(INVOCATIONS.get(self.props.slug, []))
        self.activated_abilities: list[ActivatedAbility | None] = [ActivatedAbility(self, aa) for aa in self.aas]

    def __repr__(self) -> str:
        text = self.props.name
        if self.is_creature:
            text += f' ({self.power}/{self.toughness}) '
        if self.keyword_abilities:
            kwas = self.keyword_abilities.copy()
            text += ' '.join(kwas)
        if self.modifiers:
            text += f'w {self.modifiers}'
        if self.counters:
            text += f'w {self.counters}'
        return text.upper() if not self.is_tapped else text.lower()

    @property
    def has_summoning_sickness(self) -> bool:
        if not self.is_creature:
            return False
        if not self.turn_entered_for_owner:
            return True  # turn_entered_for_owner is getting set AFTER this check
        return self.turn_entered_for_owner >= self.game_state.turn_mgr.most_recent_turn_started[self.owner_id] and \
            'Haste' not in self.keyword_abilities

    @property
    def orig_owner_id(self) -> int:
        return self._orig_owner_id

    @property
    def owner_id(self) -> int:
        if not self.modifiers or self.modifiers.new_owner_id is None:
            return self._owner_id
        return self.modifiers.new_owner_id

    @property
    def aas(self) -> list[EffSpec | None]:
        return [e for e in self.abilities if e.is_aa]

    @property
    def spells(self) -> list[EffSpec | None]:
        return [e for e in self.abilities if e.is_spell]

    @property
    def is_enchanted(self) -> bool:
        return bool(self.auras)

    @property
    def power(self) -> int:
        """Anytime this property is requested, it calls: 1) its own base_power,
        2) GameState's query system for 'pt', 3) self.modifiers.power_delta, 4) self.counters.power_delta"""
        return self._pt[0]

    @property
    def toughness(self) -> int:
        """See doc string on .power"""
        return self._pt[1]

    @property
    def _pt(self) -> tuple[int, int]:
        base_power, base_t = self.base_pt[0] or 0, self.base_pt[1] or 0
        power = base_power + self.modifiers.power_delta + self.counters.power_delta
        toughness = base_t + self.modifiers.toughness_delta + self.counters.toughness_delta

        if self.game_state._query_depth > 0:  # temp solution while unifying event system
            return power, toughness

        event = ModQueryEvent(query='pt', card=self)
        self.game_state.event_mgr.emit(event)
        for mod in event.mods:
            power += mod.p_adj
            toughness += mod.t_adj
        return power, toughness

    @property
    def card_types(self) -> list[str]:
        """Anytime this property is requested, it calls: 1) its own base _card_types, 2) self.modifiers.type_delta,
        3) GameState's query system for 'type'"""
        if self.game_state._query_depth > 0:  # temp solution while unifying event system
            # SAFE PATH: no event emission
            return list(self._card_types)

        event = ModQueryEvent(query='type', card=self)
        self.game_state.event_mgr.emit(event)
        adds, removes = set(), set()
        for mod in event.mods:
            adds.add(mod.kwa) if mod.add_or_remove == 'add' else removes.add(mod.kwa)

        return list((set(self._card_types) | adds) - removes)

    @property
    def card_sub_types(self) -> list[str]:
        """Anytime this property is requested, it calls: 1) its own base _card_sub_types,
        2) self.modifiers.sub_type_delta, 3) GameState's query system for 'sub_type'"""
        if self.game_state._query_depth > 0:  # temp solution while unifying event system
            # SAFE PATH: no event emission
            return list(self._card_sub_types)

        event = ModQueryEvent(query='sub_type', card=self)
        self.game_state.event_mgr.emit(event)
        adds, removes = set(), set()
        for mod in event.mods:
            adds.add(mod.kwa) if mod.add_or_remove == 'add' else removes.add(mod.kwa)

        return list((set(self._card_sub_types) | adds) - removes)

    @property
    def keyword_abilities(self) -> list[str]:
        """base_kwa = ['Flying', 'Reach'], mod adds = {'Trample'}, global removes = {'Reach', 'First Strike'}
        returns ['Flying', 'Trample'] ...
        Anytime this prioerty is requested, it calls: 1) its own base _base_kwa,
        2) self.modifiers.kwa_delta, 3) GameState's query system for 'kwa'"""
        if self.game_state._query_depth > 0:  # temp solution while unifying event system
            # SAFE PATH: no event emission
            return list(self._base_kwa)

        event = ModQueryEvent(query='kwa', card=self)
        self.game_state.event_mgr.emit(event)
        adds, removes = set(), set()
        for mod in event.mods:
            adds.add(mod.kwa) if mod.add_or_remove == 'add' else removes.add(mod.kwa)
        for mod in self.modifiers.iter_type(KWAMod):
            adds.add(mod.kwa) if mod.add_or_remove == 'add' else removes.add(mod.kwa)

        return list((set(self._base_kwa) | adds) - removes)

    @property
    def colors(self) -> str:
        """Does not currently lookup global queries"""
        # TODO: the previous code was producing a RecursionError, so I'm no longer checking Modifiers
        return self._colors

    def clear_all_mods(self) -> None:
        """set attached_to = None for all auras and host; all modifiers are emptied"""
        if self.props.is_aura:
            host = self.host
            host.host = None
            host.modifiers.clear_all()
        # Remove all attachments
        self.host = None
        self.modifiers.clear_all()

    def tap(self) -> None:
        """If already tapped, skip; emit TapCardEvent & tap card"""
        if self.is_tapped:
            return
        self.game_state.event_mgr.emit(TapCardEvent(card=self))
        self.is_tapped = True

    def untap(self) -> None:
        """If already untapped, skip; emit UntapCardEvent & untap card"""
        if not self.is_tapped:
            return
        self.game_state.event_mgr.emit(UntapCardEvent(card=self))
        self.is_tapped = False

    def reveal(self) -> None:
        if not self.is_face_up:
            self.is_face_up = True

    @property
    def is_artifact(self) -> bool:
        return 'Artifact' in self.card_types

    @property
    def is_creature(self) -> bool:
        return 'Creature' in self.card_types

    @property
    def is_enchantment(self) -> bool:
        return 'Enchantment' in self.card_types

    @property
    def is_instant(self) -> bool:
        return 'Instant' in self.card_types

    @property
    def is_land(self) -> bool:
        return 'Land' in self.card_types

    @property
    def is_sorcery(self) -> bool:
        return 'Sorcery' in self.card_types

    @property
    def is_black(self) -> bool:
        return 'B' in self.colors

    @property
    def is_blue(self) -> bool:
        return 'U' in self.colors

    @property
    def is_green(self) -> bool:
        return 'G' in self.colors

    @property
    def is_red(self) -> bool:
        return 'R' in self.colors

    @property
    def is_white(self) -> bool:
        return 'W' in self.colors

    @property
    def rampage_amt(self) -> int | None:
        for kwa in self.keyword_abilities:
            if 'Rampage' in kwa:
                return int(kwa[-1])
        return None
