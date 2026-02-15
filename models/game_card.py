from __future__ import annotations

import copy
from typing import Callable, TYPE_CHECKING, Optional

from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState

from card import Card
from models.card_attributes.kwa_abilities import get_creature_base_kwas
from models.counter_tokens import Counters
from models.effects.base import ActivatedAbility, EffSpec, Effect
from models.card_attributes.card_effect_specs import INVOCATIONS
from models.modifiers import Modifiers, KWAModifier, KWATemp, ModType


def attach_invocations(card: GameCard):
    """From INVOCATIONS, populate card.activated_abilities, card.static_abilities, and card.triggered_abilities"""
    eff_specs = INVOCATIONS.get(card.props.slug, [])

    for eff_spec in eff_specs:
        if eff_spec.activation_type == 'activated':
            card.activated_abilities.append(ActivatedAbility(card, eff_spec))
        elif eff_spec.activation_type == 'triggered':
            card.triggered_abilities.append(eff_spec)
        elif eff_spec.activation_type == 'static':
            card.static_abilities.append(eff_spec)
        else:
            raise ValueError(f'{eff_spec.activation_type} is not a known activation type')


class GameCard:
    def __init__(self, props: Card, orig_owner_id: int, is_token: bool = False, colors: str = ''):
        self.props: Card = props
        self._orig_owner_id: int = orig_owner_id
        self.owner_id: int = orig_owner_id
        self.game_state: "GameState" = None
        self.img_url: str = next(iter(self.props.images.values()))  # set to the earliest set's image
        self.casting_cost: str = self.props.casting_cost[:] if self.props.casting_cost else None
        self._card_types: list[str] = self.props.card_types.copy()
        self._card_sub_types: list[str] = self.props.card_sub_types.copy()
        self.colors: str = colors or self.props.colors[:]
        self.is_token: bool = is_token
        self.is_tapped: bool = False
        self.has_summoning_sickness: bool = self.props.is_creature and 'Haste' not in self.props.keyword_abilities
        self.attached_to: "GameCard" = None
        self.modifiers = Modifiers()
        self.counters = Counters()

        self.zone = Zone.LIBRARY

        self.damage_dealt_this_turn: int = 0  # not sure that these belong here
        self.damage_received_this_turn: int = 0

        self.base_pt = (self.props.power, self.props.toughness)
        self.variable_x: int | None = None  # for variable casting costs

        # perform look-up to add base keyword abilities, activated abilities, and effects
        if self.is_token:
            self._base_kwa = tuple(self.props.keyword_abilities)
        elif self.props.is_creature:
            self._base_kwa: tuple[str] = get_creature_base_kwas(self.props.slug)
        else:
            self._base_kwa = ()
        self.activated_abilities: list[ActivatedAbility] = []
        self.static_abilities: list[EffSpec] = []
        self.triggered_abilities: list[EffSpec] = []

        attach_invocations(self)

    def __repr__(self) -> str:
        text = self.props.name
        if self.is_creature:
            text += f' ({self.power}/{self.toughness}) '
        if self.keyword_abilities:
            kwas = self.keyword_abilities.copy()
            text += ' '.join(kwas)
        if self.modifiers:
            text += f' w {self.modifiers}'
        if self.counters:
            text += f' w {self.counters}'
        return text.upper() if not self.is_tapped else text.lower()

    @property
    def orig_owner_id(self) -> int:
        return self._orig_owner_id

    @property
    def power(self) -> int:
        return self._pt[0]

    @property
    def toughness(self) -> int:
        return self._pt[1]

    @property
    def _pt(self) -> tuple[int, int]:
        global_power_adj, global_toughness_adj = self._get_global_pt_adj()
        base_power, base_t = self.base_pt[0] or 0, self.base_pt[1] or 0
        power = base_power + global_power_adj + self.modifiers.power_delta + self.counters.power_delta
        toughness = base_t + global_toughness_adj + self.modifiers.toughness_delta + self.counters.toughness_delta
        return power, toughness

    def _get_global_pt_adj(self) -> tuple[int, int]:
        power, toughness = 0, 0
        for mod in self._get_global_query('pt_mod'):
            if mod:
                power += mod.power_delta
                toughness += mod.toughness_delta
        return power, toughness

    @property
    def card_types(self) -> list[str]:
        return self._get_types()

    def _get_types(self) -> list[str]:
        types = set(self._card_types)
        adds, removes = self.modifiers.type_delta
        global_adds, global_removes = set(), set()
        for mod in self._get_global_query('type_mod'):
            if mod:
                if mod.add_or_remove == 'add':
                    global_adds.add(mod.card_type)
                    if mod.card_type == 'Creature' and 'Creature' not in self._card_types:
                        if mod.expires_end_of_turn:
                            self.modifiers.temps.append(KWATemp(mod.source, 'add', 'Attack'))
                        else:
                            self.modifiers.auras.append(KWAModifier(mod.source, 'add', 'Attack'))
                else:
                    global_removes.add(mod.card_type)
        return list((types | adds | global_adds) - (removes | global_removes))

    @property
    def card_sub_types(self) -> list[str]:
        return self._get_sub_types()

    def _get_sub_types(self) -> list[str]:
        types = set(self._card_sub_types)
        adds, removes = self.modifiers.sub_type_delta
        global_adds, global_removes = set(), set()
        for mod in self._get_global_query('sub_type_mod'):
            if not mod:
                continue
            mods = [mod] if isinstance(mod, ModType) else mod
            for m in mods:
                global_adds.add(m.card_sub_type) if m.add_or_remove == 'add' else global_removes.add(m.card_sub_type)
        return list((types | adds | global_adds) - (removes | global_removes))

    @property
    def keyword_abilities(self) -> list[str]:
        """base_kwa = ['Flying', 'Reach'], mod adds = {'Trample'}, global removes = {'Reach', 'First Strike'}
        returns ['Flying', 'Trample']"""
        return self._get_keyword_abilities()

    def _get_keyword_abilities(self) -> list[str]:
        kwa = set(self._base_kwa)
        adds, removes = self.modifiers.kwa_delta
        global_adds, global_removes = set(), set()
        for mod in self._get_global_query('kwa_mod'):
            if mod:
                if mod.add_or_remove == 'add':
                    global_adds.add(mod.kwa)
                else:
                    global_removes.add(mod.kwa)
        return list((kwa | adds | global_adds) - (removes | global_removes))

    def _get_global_query(self, global_type: str) -> list[ModType]:
        effects_and_cards: list[tuple[Effect, GameCard]] = []
        # static effects on other permanents (ex: crusade lives in static abilities)
        for c in self.game_state.card_filter.in_play().result():
            for a in c.static_abilities:
                effects_and_cards.append((a.effect, c))
            for a in c.triggered_abilities:
                effects_and_cards.append((a.effect, c))
        for eff, card in self.game_state.until_eot_effects_and_cards:
            effects_and_cards.append((eff, card))

        modifiers = []
        for effect, source in effects_and_cards:
            if not hasattr(effect, 'on_query'):
                continue
            mod: ModType | list[ModType] = effect.on_query(self.game_state, global_type, card=self, source=source)
            if mod:
                modifiers.append(mod) if isinstance(mod, ModType) else modifiers.extend(mod)
        return modifiers

    def clear_all_mods(self) -> None:
        """attached_to = None for all auras and host; all modifiers are emptied"""
        if self.props.is_aura:
            host = self.attached_to
            host.attached_to = None
            host.modifiers.clear_all()
        # Remove all attachments
        self.attached_to = None
        self.modifiers.clear_all()

    def tap(self, gs: "GameState") -> None:
        gs.tap_card(self)

    def untap(self, gs: "GameState") -> None:
        gs.untap_card(self)

    def set_image(self, set_code: str):
        self.img_url = self.props.images.get(set_code) or self.img_url

    @property
    def is_creature(self) -> bool:
        return 'Creature' in self.card_types
