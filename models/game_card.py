from dataclasses import dataclass

from card import Card

@dataclass(frozen=True)
class BasePT:
    power: int
    toughness: int

@dataclass
class PTModifier:
    slug: str
    power_delta: int = 0
    toughness_delta: int = 0

    def __repr__(self):
        return f'{self.slug}({self.power_delta}/{self.toughness_delta})'

@dataclass
class PTTemp:
    power_delta: int
    toughness_delta: int
    expires_end_of_turn: bool = True

@dataclass
class KWAModifier:
    slug: str
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
    def __init__(self, props: Card, id_: int, orig_owner_id: int):
        self.props: Card = props
        self.id: int = id_
        self.orig_owner_id: int = orig_owner_id
        self.img_url: str = next(iter(self.props.images.values()))  # set to the earliest set's image
        self.casting_cost: str = self.props.casting_cost
        self.is_tapped: bool = False
        self.can_attack: bool = self.props.is_creature and 'Defender' not in self.props.card_sub_types
        self.can_block: bool = self.props.is_creature
        self.has_summoning_sickness: bool = 'Haste' not in self.props.keyword_abilities
        self.has_flying: bool = 'Flying' in self.props.keyword_abilities
        self.auras: list['GameCard'] = []

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

    def set_image(self, set_code: str):
        self.img_url = self.props.images.get(set_code) or self.img_url
