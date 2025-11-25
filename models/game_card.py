from typing import Callable

from card import Card
from cast_targets import CAST_TARGETS
from models.effects.leave import *
from models.effects.slug_effect_mapping import SLUG_EFFECTS
from models.effects.untap import *
from models.activated_ability import ActivatedAbility
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
        self.abilities: list[ActivatedAbility] = []

        self.can_attack: bool = self.props.is_creature and 'Wall' not in self.props.card_sub_types
        self.can_block: bool = self.props.is_creature
        self.has_summoning_sickness: bool = 'Haste' not in self.props.keyword_abilities
        self.has_flying: bool = 'Flying' in self.props.keyword_abilities
        self.auras: list["GameCard"] = []
        self.attached_to: "GameCard" = None

        self.combat_damage_dealt: int = 0
        self.combat_damage_received: int = 0

        self.base_pt = (self.props.power, self.props.toughness)
        # self.base_kwa: tuple[str, ...] = tuple(self.props.keyword_abilities)
        self.base_kwa: tuple[str, ...] = self.construct_base_kwas()
        self.modifiers = Modifiers()

        # Build effect instances for this card based on slug
        self.effects: list[Effect] = []
        # global mapping for slug-based effects
        slug_effects = build_effects_for_slug(self.props.slug)
        if slug_effects:
            self.effects.extend(slug_effects)

    def __repr__(self) -> str:
        if not self.props.is_creature and not self.modifiers:
            text = self.props.name
        elif not self.props.is_creature and self.modifiers:
            text = f'{self.props.name} [{self.modifiers}]'
        else:
            text = f'{self.props.name} ({self.power}/{self.toughness}){self.modifiers}'
        return text.upper() if not self.is_tapped else text.lower()

    @property
    def owner_and_id(self) -> str:
        return f"{self.orig_owner_id}-{self.id}"

    @property
    def power(self) -> int:
        return self._pt[0]

    @property
    def toughness(self) -> int:
        return self._pt[1]

    @property
    def _pt(self) -> tuple[int, int]:
        global_power_adj, global_toughness_adj = self._get_global_pt_adj()
        power = self.base_pt[0] + global_power_adj + self.modifiers.power_delta
        toughness = self.base_pt[1] + global_toughness_adj + self.modifiers.toughness_delta
        return power, toughness

    def _get_global_pt_adj(self) -> tuple[int, int]:
        power, toughness = 0, 0
        for card, global_effect in self.game_state.global_effects:
            if global_effect.applies_to(self, self.game_state):
                if not hasattr(global_effect, 'pt_offset'):
                    continue
                p_offset, t_offset = global_effect.pt_offset()
                power += p_offset
                toughness += t_offset
        return power, toughness

    def construct_base_kwas(self) -> tuple[str, ...]:
        """Add 'Attack' to non-wall creatures"""
        base_kwas = self.props.keyword_abilities
        if 'Creature' not in self.props.card_types:
            return tuple(base_kwas)
        if 'Wall' not in self.props.card_sub_types and 'Attack' not in base_kwas:
            base_kwas.append('Attack')
        return tuple(base_kwas)

    @property
    def keyword_abilities(self) -> list[str]:
        """base_kwa = ['Flying', 'Reach'], mod adds = {'Trample'}, mod removes = {'Reach', 'First Strike'}
        returns ['Flying', 'Trample']"""
        kwa = set(self.base_kwa)
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
        if self.is_tapped:
            return
        self.is_tapped = True
        for a in self.auras:
            a.is_tapped = True
        gs.trigger('tap', self)

    def untap(self, gs: "GameState") -> None:
        if not self.is_tapped:
            return
        self.is_tapped = False
        for a in self.auras:
            a.is_tapped = False
        gs.trigger('untap', self)

    def deal_damage_to_card(self, gs: "GameState", amt: int, target: "GameCard"):
        target.receive_damage(gs, amt, self)

    def deal_damage_to_player(self, gs: "GameState", amt: int, target_player_idx: int):
        gs.decrement_life(target_player_idx, amt, self)

    def receive_damage(self, gs: "GameState", amt: int, source: "GameCard"):
        self.modifiers.temps.append(PTTemp(0, -amt))
        if self.toughness <= 0:
            gs.send_to_graveyard_from_play(self)

    def set_image(self, set_code: str):
        self.img_url = self.props.images.get(set_code) or self.img_url

    def get_cast_targets(self, gs: "GameState") -> list["GameCard"]:
        """First search registry; if aura isn't found in registry, assume it targets in-play creatures"""
        if ctf := CAST_TARGETS.get(self.props.slug):
            return ctf(gs)
        if self.props.is_aura:
            return CardFilter(gs).in_play().creatures().result()

    def on_upkeep(self, gs):
        gs.trigger('upkeep', self)
