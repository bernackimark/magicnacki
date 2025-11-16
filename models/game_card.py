from card import Card


class GameCard:
    def __init__(self, props: Card, id_: int, orig_owner_id: int):
        self.props: Card = props
        self.id: int = id_
        self.orig_owner_id: int = orig_owner_id
        self.img_url: str = next(iter(self.props.images.values()))  # set to the earliest set's image
        self.casting_cost: str = self.props.casting_cost
        self.is_tapped: bool = False
        self.can_attack: bool = self.props.is_creature
        self.can_block: bool = self.props.is_creature
        self.power: int | None = self.props.power
        self.toughness: int | None = self.props.toughness
        self.has_summoning_sickness: bool = not ('Haste' in self.props.keyword_abilities)
        self.has_flying: bool = 'Flying' in self.props.keyword_abilities
        self.combat_damage_dealt: int = 0
        self.combat_damage_received: int = 0
        self.auras: list['GameCard'] = []

    def __repr__(self) -> str:
        if not self.props.is_creature:
            text = self.props.name
        else:
            ec_text = 'w ' + '& '.join([ec.props.name for ec in self.auras]) if self.auras else ''
            text = f'{self.props.name} {ec_text}({self.props.power}/{self.props.toughness})'
        return text.upper() if not self.is_tapped else text.lower()

    @property
    def owner_and_id(self) -> str:
        return f"{self.orig_owner_id}-{self.id}"

    def tap(self) -> None:
        self.is_tapped = True
        for ec in self.auras:
            ec.is_tapped = True

    def untap(self) -> None:
        self.is_tapped = False
        for ec in self.auras:
            ec.is_tapped = False

    def set_image(self, set_code: str):
        self.img_url = self.props.images.get(set_code) or self.img_url
