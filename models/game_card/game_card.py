from __future__ import annotations
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Iterable
from uuid import uuid4

from ..constants import KW, Zone

if TYPE_CHECKING:
    from game_state import GameState
    from .card import Card

from .slug_effect_map import INVOCATIONS
from ..effects.base import EffSpec, ActivatedAbility
from ..events_all import ModQueryEvent, TapCardEvent, UntapCardEvent
from models.game_card.counter_tokens import Counters
from models.game_card.modifiers import Modifiers, KWAMod, SubTypeMod, TypeMod, ManaProdMod, ColorMod, CollectionMod, PTMod, \
    BasePTMod


class GameCard:
    def __init__(self, props: Card, orig_owner_id: int, is_token: bool = False):
        self.id_ = str(uuid4())
        self.props: Card = props
        self._card_types: list[str] = self.props.card_types.copy()
        self._card_sub_types: list[str] = self.props.card_sub_types.copy()
        self._colors: list[str] = self.props.colors
        self._mana_produced: list[str] = self.props.mana_produced or []
        self.base_pt = (self.props.power, self.props.toughness)
        self._base_kwa = tuple(self.props.keyword_abilities)
        self.casting_cost: str = self.props.casting_cost[:] if self.props.casting_cost else None
        self._orig_owner_id: int = orig_owner_id

        self.game_state: GameState | None = None
        self.turn_entered_for_owner: int | None = None
        self.is_token: bool = is_token
        self.is_tapped: bool = False
        self.is_face_up: bool = False
        self.host: GameCard | None = None
        self.auras: list[GameCard | None] = []
        self.modifiers = Modifiers()
        self.counters = Counters()

        self.zone = Zone.LIBRARY

        self.damage_dealt_this_turn: int = 0
        self.damage_received_this_turn: int = 0

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
            KW.HASTE not in self.keyword_abilities

    @property
    def orig_owner_id(self) -> int:
        return self._orig_owner_id

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
        if not self.is_creature:
            return 0, 0

        base_p, base_t = self.base_pt

        for mod in self.modifiers.get(BasePTMod):
            base_p = mod.base_p
            base_t = mod.base_t

        base_p, base_t = base_p or 0, base_t or 0
        power = base_p + sum(m.p_adj for m in self.modifiers.get(PTMod)) + self.counters.power_delta
        toughness = base_t + sum(m.t_adj for m in self.modifiers.get(PTMod)) + self.counters.toughness_delta

        event = ModQueryEvent(query='pt', card=self)
        self.game_state.event_mgr.emit(event)
        for mod in event.mods:
            power += mod.p_adj
            toughness += mod.t_adj
        return power, toughness

    @property
    def owner_id(self) -> int:
        """Query for registered ModQueryEvents query='ownership';
        if none found, return owner id assigned during instantiation; else, return the most recent new owner"""
        event = ModQueryEvent(query='ownership', card=self)
        self.game_state.event_mgr.emit(event)
        if not event.mods:
            return self.orig_owner_id
        return event.mods[-1].new_owner_id

    @property
    def card_types(self) -> list[str]:
        return self._modified_collection("type", self._card_types, TypeMod)

    @property
    def card_sub_types(self) -> list[str]:
        return self._modified_collection("sub_type", self._card_sub_types, SubTypeMod)

    @property
    def colors(self) -> list[str]:
        return self._modified_collection("color", self._colors, ColorMod)

    @property
    def keyword_abilities(self) -> list[str]:
        return self._modified_collection("kwa", self._base_kwa, KWAMod)

    @property
    def mana_produced(self) -> list[str]:
        return self._modified_collection("mana_produced", self._mana_produced, ManaProdMod)

    def _modified_collection(self, query: str, base: Iterable[str | None],
                             mod_cls: type[CollectionMod]) -> list[str]:
        """Ex: base = [KW.FLYING] -> aura in self.modifiers grants KW.FIRST_STRIKE ->
        global ModQueryEvent removes KW.FLYING from all creatures -> [KW.FIRST_STRIKE]"""

        event = ModQueryEvent(query=query, card=self)
        self.game_state.event_mgr.emit(event)

        adds = set()
        removes = set()

        for mod in self.modifiers.get(mod_cls):
            adds.add(mod.item) if mod.add_or_remove == "add" else removes.add(mod.item)

        for mod in event.mods:
            adds.add(mod.item) if mod.add_or_remove == "add" else removes.add(mod.item)

        return list((set(base) | adds) - removes)

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
    def rampage_amt(self) -> int | None:
        for kwa in self.keyword_abilities:
            if 'Rampage' in kwa:
                return int(kwa[-1])
        return None

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
    def is_permanent(self) -> bool:
        permanent_types = {'Artifact', 'Enchantment', 'Creature', 'Land'}
        return bool(permanent_types & set(self.card_types))

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
    def is_island(self) -> bool:
        return 'Island' in self.card_sub_types
