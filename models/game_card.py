from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState

from card import Card
from models.card_attributes.kwa_abilities import get_creature_base_kwas
from models.counter_tokens import Counters
from models.effects.base import ActivatedAbility, EffSpec, Effect
from models.card_attributes.card_effect_specs import INVOCATIONS
from models.modifiers import Modifiers, PTModifier, PTTemp, KWAModifier, KWATemp


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
    def __init__(self, props: Card, id_: int, orig_owner_id: int, cast_target_func: Callable = None):
        self.props: Card = props
        self.id: int = id_
        self._orig_owner_id: int = orig_owner_id
        self.owner_id: int = orig_owner_id
        self.game_state: "GameState" = None
        self.img_url: str = next(iter(self.props.images.values()))  # set to the earliest set's image
        self.casting_cost: str = self.props.casting_cost
        self.is_tapped: bool = False
        self.can_block: bool = self.props.is_creature  # can get rid of this attribute; only one (incorrect) usage
        self.has_summoning_sickness: bool = self.props.is_creature and 'Haste' not in self.props.keyword_abilities
        self.has_flying: bool = 'Flying' in self.props.keyword_abilities
        self.attached_to: "GameCard" = None
        self.modifiers = Modifiers()
        self.counters = Counters()

        self.zone = Zone.LIBRARY

        self.combat_damage_dealt: int = 0  # not sure that these belong here
        self.combat_damage_received: int = 0

        self.base_pt = (self.props.power, self.props.toughness)
        self.variable_x: int | None = None  # for variable casting costs

        # perform look-up to add base keyword abilities, activated abilities, and effects
        self._base_kwa: tuple[str] = get_creature_base_kwas(self.props.slug) if self.props.is_creature else ()
        self.activated_abilities: list[ActivatedAbility] = []
        self.static_abilities: list[EffSpec] = []
        self.triggered_abilities: list[EffSpec] = []

        attach_invocations(self)

    def __repr__(self) -> str:
        text = self.props.name
        if self.props.is_creature:
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
        power = self.base_pt[0] + global_power_adj + self.modifiers.power_delta + self.counters.power_delta
        toughness = self.base_pt[1] + global_toughness_adj + self.modifiers.toughness_delta + self.counters.toughness_delta
        return power, toughness

    def _get_global_pt_adj(self) -> tuple[int, int]:
        power, toughness = 0, 0
        for mod in self._get_global_query('pt_mod'):
            if mod:
                power += mod.power_delta
                toughness += mod.toughness_delta
        return power, toughness

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

    def _get_global_query(self, global_type: str) -> list[PTModifier | PTTemp | KWAModifier | KWATemp]:
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
            mod: PTModifier | PTTemp | KWAModifier | KWATemp = effect.on_query(self.game_state, global_type,
                                                                               card=self, source=source)
            modifiers.append(mod)
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
