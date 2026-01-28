from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from models.effects.draw_discard import CursedRackEffect

if TYPE_CHECKING:
    from game_state import GameState

from card import Card
from cast_targets import CAST_TARGETS
from kw_ability import get_base_kwas
from models.counter_tokens import Counters
from models.effects.base import Effect
from models.effects.slug_effect_mapping import SLUG_EFFECTS, ActivatedAbility, get_activated_abilities
from models.modifiers import Modifiers


def build_effects_for_slug(slug: str) -> list[Effect]:
    """Instantiate and return effect instances for known slugs. This centralizes where slugs map to behaviors."""
    return SLUG_EFFECTS.get(slug, [])


class GameCard:
    def __init__(self, props: Card, id_: int, orig_owner_id: int, cast_target_func: Callable = None):
        self.props: Card = props
        self.id: int = id_
        self.orig_owner_id: int = orig_owner_id
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

        self.combat_damage_dealt: int = 0  # not sure that these belong here
        self.combat_damage_received: int = 0

        self.base_pt = (self.props.power, self.props.toughness)
        self.variable_x: int | None = None  # for variable casting costs

        # perform look-ups to add: base keyword abilities, activated abilities, and effects
        self._base_kwa: tuple[str, ...] | tuple[None] = get_base_kwas(self.props.slug)
        self.abilities: list[ActivatedAbility] = get_activated_abilities(self)
        self.effects: list[Effect] = build_effects_for_slug(self.props.slug)

        # gingerly testing out the new event emission system
        if self.props.slug == 'cursed-rack':
            self.effects = [CursedRackEffect()]

    def __repr__(self) -> str:
        text = self.props.name
        if self.props.is_creature:
            text += f' ({self.power}/{self.toughness})'
        if self.modifiers:
            text += f' w {self.modifiers}'
        if self.counters:
            text += f' w {self.counters}'
        return text.upper() if not self.is_tapped else text.lower()

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
        for card, global_effect, _ in self.game_state.global_effects:
            if not hasattr(global_effect, 'pt_offset'):
                continue
            if global_effect.applies_to(self, self.game_state):
                p_offset, t_offset = global_effect.pt_offset()
                power += p_offset
                toughness += t_offset
        return power, toughness

    @property
    def keyword_abilities(self) -> list[str]:
        """base_kwa = ['Flying', 'Reach'], mod adds = {'Trample'}, mod removes = {'Reach', 'First Strike'}
        returns ['Flying', 'Trample']"""
        kwa = set(self._base_kwa)
        adds, removes = self.modifiers.kwa_delta
        return list((kwa | adds) - removes)

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

    def get_cast_targets(self, gs: GameState) -> list["GameCard"]:
        # TODO: i don't think this belongs here and should be handled differentl in the new system
        """First search registry; if aura isn't found in registry, assume it targets in-play creatures"""
        if ctf := CAST_TARGETS.get(self.props.slug):
            return ctf(gs)
        if self.props.is_aura:
            return gs.card_filter.in_play().creatures().result()
