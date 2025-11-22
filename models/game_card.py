from dataclasses import dataclass
from typing import Callable, Self

from card import Card
from card_filter import CardFilter
from models.activated_ability import ActivatedAbility
from utils import flip


CAST_TARGETS = {
    'animate-wall': lambda gs: CardFilter(gs).in_play().walls().result(),
    'disenchant': lambda gs: CardFilter(gs).by_type(['Artifact', 'Enchantment']).result(),
    'feedback': lambda gs: CardFilter(gs).in_play().by_type('Enchantment').result(),
    'jump': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'psychic-venom': lambda gs: CardFilter(gs).in_play().lands().result(),
    'twiddle': lambda gs: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).result(),
    'unsummon': lambda gs: CardFilter(gs).in_play().creatures().result()
}

def swords_to_plowshares_success_cast(gs, t):
    gs.send_to_exile(t)
    gs.increment_life(t.orig_owner_id, t.power)

def unsummon_success_cast(gs, t):
    print(f"UNSUMMONING: {t}")
    board = gs.boards[t.orig_owner_id]
    board.remove_from_board(t)
    gs.return_to_hand(t)


SUCCESSFUL_CAST = {
    'armageddon': lambda gs, c, t: [gs.send_to_graveyard(c) for c in CardFilter(gs).in_play().by_type('Land').result()],
    'castle': lambda gs, c, t: [c.pt_modifiers.append(PTModifier(c, 0, 2)) for c in CardFilter(gs).creatures().on_player_board(gs.player_idx).is_tapped(False).result()],
    'crusade': lambda gs, c, t: [c.pt_modifiers.append(PTModifier(c, 1, 1)) for c in CardFilter(gs).in_play().creatures().white().result()],
    'disenchant': lambda gs, c, t: gs.send_to_graveyard(t),
    'divine-transformation': lambda gs, c, t: t.pt_modifiers.append(PTModifier(c, 3, 3)),
    'flight': lambda gs, c, t: t.kwa_modifiers.append(KWAModifier(c, 'add', 'Flying')),
    'giant-tortoise': lambda gs, c, t: c.pt_modifiers.append(PTModifier(c, 0, 3)),
    'holy-strength': lambda gs, c, t: t.pt_modifiers.append(PTModifier(c, 1, 2)),
    'jump': lambda gs, c, t: t.kwa_temps.append(KWATemp('add', 'Flying')),
    'lance': lambda gs, c, t: t.kwa_modifiers.append(KWAModifier(c, 'add', 'First Strike')),
    'swords-to-plowshares': lambda gs, c, t: swords_to_plowshares_success_cast(gs, t),
    'twiddle': lambda gs, c, t: t.tap(gs) if t.is_tapped else t.tap(gs),
    'unsummon': lambda gs, c, t: unsummon_success_cast(gs, t),
    'wrath-of-god': lambda gs, c, t: [gs.send_to_exile(c) for c in CardFilter(gs).in_play().creatures().result()]
}

UPKEEP_FUNCS = {
    'feedback': lambda gs, c: gs.decrement_life(gs.player_turn_idx, 1, c),
    'karma': lambda gs, c: [gs.decrement_life(gs.player_turn_idx, 1, c) for _ in CardFilter(gs).on_player_board(flip(gs.player_turn_idx)).by_slug('swamp').result()],
    'serendib-efreet': lambda gs, c: gs.decrement_life(gs.player_turn_idx, 1, c),
}

TAP_REGISTRY = [
    # If Castle exists and card becomes tapped, remove Castle from its Power/Toughness Modifiers
    (lambda gs, c: any(m for m in c.pt_modifiers if m.slug == 'castle'), lambda gs, c: c.remove_perm_mod_by_slug('castle')),
    # If Giant Tortoise taps, shed its +0/+3 mod
    (lambda gs, c: c.props.slug == "giant-tortoise", lambda gs, c: c.remove_perm_mod_by_slug("giant-tortoise")),
    # If a card w Psychic Venom taps, deal 2 damage to its controller
    (lambda gs, c: any(a.props.slug == "psychic-venom" for a in c.auras), lambda gs, c: gs.decrement_life(c.orig_owner_id, 2, c)),
]

UNTAP_REGISTRY = [
    # If the player has a Castle in-play and the card is White, add one Castle to its PT Modifiers for each Castle owned
    (lambda gs, c: CardFilter(gs).on_player_board(c.orig_owner_id).by_slug('castle').result() and 'W' in c.props.colors,
     lambda gs, c: [c.pt_modifiers.append(PTModifier(c, 0, 2)) for _ in CardFilter(gs).on_player_board(c.orig_owner_id).by_slug('castle').result()]),
    # If Giant Tortoise untaps, give it its +0/+3 mod
    (lambda gs, c: c.props.slug == "giant-tortoise", lambda gs, c: c.pt_modifiers.append(PTModifier(c, 0, 3))),
]


@dataclass(frozen=True)
class BasePT:
    power: int
    toughness: int

@dataclass
class PTModifier:
    card: "GameCard"
    power_delta: int = 0
    toughness_delta: int = 0

    def __repr__(self):
        return f'{self.card.props.name}({self.power_delta}/{self.toughness_delta})'

@dataclass
class PTTemp:
    power_delta: int
    toughness_delta: int
    expires_end_of_turn: bool = True

@dataclass
class KWAModifier:
    card: "GameCard"
    add_or_remove: str
    kwa: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa}"

@dataclass
class KWATemp:
    add_or_remove: str
    kwa: str
    expires_end_of_turn: bool = True

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa} until end of turn"


class GameCard:
    def __init__(self, props: Card, id_: int, orig_owner_id: int, cast_target_func: Callable = None):
        self.props: Card = props
        self.id: int = id_
        self.orig_owner_id: int = orig_owner_id
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
        return (self.base.power + sum(m.power_delta for m in self.pt_modifiers) +
                sum(t.power_delta for t in self.pt_temps))

    @property
    def toughness(self) -> int:
        return (self.base.toughness + sum(m.toughness_delta for m in self.pt_modifiers)
                + sum(t.toughness_delta for t in self.pt_temps))

    @property
    def keyword_abilities(self) -> list[str]:
        kwa = set(self.base_kwa)

        # TODO: a modifying method inside of a property?!
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
        for a in self.auras:
            a.attached_to = None
        self.auras.clear()
        self.kwa_modifiers.clear()
        self.kwa_temps.clear()
        self.pt_modifiers.clear()
        self.pt_temps.clear()

    def remove_perm_mod_by_slug(self, slug: str):
        for mod in self.auras:
            if mod.props.slug == slug:
                self.auras.remove(mod)
                break
        for mod in self.pt_modifiers:
            if mod.slug == slug:
                self.pt_modifiers.remove(mod)
                break
        for mod in self.kwa_modifiers:
            if mod.slug == slug:
                self.kwa_modifiers.remove(mod)
                break

    def tap(self, gs: "GameState") -> None:
        # Core tap behavior: affects the card itself
        self.is_tapped = True
        for a in self.auras:
            a.is_tapped = True

        # Delegate special-case triggers to the GameState registry
        gs.apply_tap_effects(self)

    def untap(self, gs: "GameState") -> None:
        # Core tap behavior: affects the card itself
        self.is_tapped = False
        for a in self.auras:
            a.is_tapped = False

        # Delegate special-case triggers to the GameState registry
        gs.apply_untap_effects(self)

    def set_image(self, set_code: str):
        self.img_url = self.props.images.get(set_code) or self.img_url

    def get_cast_targets(self, gs: "GameState") -> list["GameCard"]:
        """First search registry; if aura isn't found in registry, assume it targets in-play creatures"""
        if ctf := CAST_TARGETS.get(self.props.slug):
            return ctf(gs)
        if self.props.is_aura:
            return CardFilter(gs).in_play().creatures().result()

    def on_upkeep(self, gs):
        """If self.props.slug is found in UPKEEP_FUNCS registry, execute function"""
        if func := UPKEEP_FUNCS.get(self.props.slug):
            func(gs, self)

    def cast(self):
        ...
