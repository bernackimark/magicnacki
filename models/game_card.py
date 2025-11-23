from typing import Callable

from card import Card
from models.effects.cast import *
from models.effects.common import *
from models.effects.leave import *
from models.effects.tap import *
from models.effects.upkeep import *
from models.effects.untap import *
from models.activated_ability import ActivatedAbility
from models.modifiers import BasePT, PTModifier, PTTemp, KWAModifier, KWATemp

def build_effects_for_slug(slug: str) -> list[Effect]:
    """
    Instantiate and return effect instances for known slugs.
    This centralizes where slugs map to behaviors.
    """
    mapping = {
        'armageddon': [send_to_graveyard_all_lands()],
        'castle': [castle_on_cast(), castle_on_leave()],
        'creature-bond': [creature_bond_on_leave()],
        'crusade': [crusade_on_cast(), crusade_on_leave()],
        'disenchant': [disenchant_on_cast()],
        'divine-transformation': [divine_transformation_on_cast()],
        'feedback': [feedback_on_upkeep()],
        'flight': [add_flying_on_cast()],
        'giant-tortoise': [giant_tortoise_on_cast(), giant_tortoise_on_tap(), giant_tortoise_on_untap()],
        'holy-armor': [holy_armor_on_cast()],
        'holy-strength': [holy_strength_on_cast()],
        'jump': [jump_on_cast()],
        'karma': [karma_on_upkeep()],
        'lance': [lance_on_cast()],
        'serendib-efreet': [serendib_efreet_on_upkeep()],
        'swords-to-plowshares': [swords_to_plowshares_on_cast()],
        'twiddle': [twiddle_on_cast()],
        'unsummon': [unsummon_on_cast()],
        'wrath-of-god': [wrath_of_god_on_cast()],

        '_default_leave': [default_clear_on_leave()],
    }
    return mapping.get(slug, [])


CAST_TARGETS = {
    'animate-wall': lambda gs: CardFilter(gs).in_play().walls().result(),
    'disenchant': lambda gs: CardFilter(gs).in_play().by_type(['Artifact', 'Enchantment']).result(),
    'feedback': lambda gs: CardFilter(gs).in_play().by_type('Enchantment').result(),
    'jump': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'psychic-venom': lambda gs: CardFilter(gs).in_play().lands().result(),
    'twiddle': lambda gs: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).result(),
    'unsummon': lambda gs: CardFilter(gs).in_play().creatures().result()
}

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

        self.base: BasePT = BasePT(self.props.power, self.props.toughness)
        self.pt_modifiers: list[PTModifier] = []
        self.pt_temps: list[PTTemp] = []

        self.base_kwa: tuple[str, ...] = tuple(self.props.keyword_abilities)
        self.kwa_modifiers: list[KWAModifier] = []
        self.kwa_temps: list[KWATemp] = []

        # Build effect instances for this card based on slug
        self.effects: list[Effect] = []
        # global mapping for slug-based effects
        slug_effects = build_effects_for_slug(self.props.slug)
        if slug_effects:
            self.effects.extend(slug_effects)

    def __repr__(self) -> str:
        if not self.props.is_creature:
            text = self.props.name
        else:
            mods = self.auras + self.pt_modifiers + self.pt_temps + self.kwa_modifiers + self.kwa_temps
            text = f'{self.props.name} ({self.power}/{self.toughness}) {mods}'
        return text.upper() if not self.is_tapped else text.lower()

    @property
    def owner_and_id(self) -> str:
        return f"{self.orig_owner_id}-{self.id}"

    @property
    def power(self) -> int:
        # could probably be re-written to reduce calls
        global_power_adj, _ = self.get_global_pt_adj()
        return (self.base.power + global_power_adj + sum(m.power_delta for m in self.pt_modifiers) +
                sum(t.power_delta for t in self.pt_temps))

    @property
    def toughness(self) -> int:
        # could probably be re-written to reduce calls
        _, global_toughness_adj = self.get_global_pt_adj()
        return (self.base.toughness + global_toughness_adj + sum(m.toughness_delta for m in self.pt_modifiers)
                + sum(t.toughness_delta for t in self.pt_temps))

    def get_global_pt_adj(self) -> tuple[int, int]:
        for card, global_effect in self.game_state.global_effects:
            if global_effect.applies_to(self, self.game_state):
                return global_effect.pt_offset()
        return 0, 0

    @property
    def keyword_abilities(self) -> list[str]:
        kwa = set(self.base_kwa)

        # TODO: a modifying method inside a property?!
        def add_remove_kwa(m: KWAModifier | KWATemp):
            if m.add_or_remove == 'add':
                kwa.add(m.kwa)
            else:
                if m.kwa in kwa:
                    kwa.remove(m.kwa)

        for mod in self.kwa_modifiers:
            add_remove_kwa(mod)
        for mod in self.kwa_temps:
            add_remove_kwa(mod)

        return list(kwa)

    def clear_all_mods(self) -> None:
        """attached_to = None for auras and host; all lists of auras, perm_mods, and temp_mods are emptied"""
        if self.props.is_aura:
            # I'm an aura. remove relationship from host & remove from host.auras(), .pt_modifiers(), .kwa_modifiers()
            host = self.attached_to
            host.attached_to = None
            host.auras.remove(self)
            for kwa_mod in host.kwa_modifiers:
                if kwa_mod.card == self:
                    host.kwa_modifiers.remove(kwa_mod)
                    break
            for pt_mod in host.pt_modifiers:
                if pt_mod.card == self:
                    host.pt_modifiers.remove(pt_mod)
                    break
        # Remove all attachments
        self.attached_to = None
        self.auras.clear()
        self.kwa_modifiers.clear()
        self.pt_modifiers.clear()
        self.kwa_temps.clear()
        self.pt_temps.clear()

    def remove_perm_mod(self, mod: "GameCard"):
        for a in self.auras:
            if a == mod:
                self.auras.remove(mod)
                break
        for pt_mod in self.pt_modifiers:
            if pt_mod.card == mod:
                self.pt_modifiers.remove(pt_mod)
                break
        for kwa_mod in self.kwa_modifiers:
            if kwa_mod.card == mod:
                self.kwa_modifiers.remove(kwa_mod)
                break

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
        self.pt_temps.append(PTTemp(0, -amt))
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
