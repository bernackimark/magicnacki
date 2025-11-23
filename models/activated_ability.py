from dataclasses import dataclass
from typing import Callable, Optional, Union

from card_filter import CardFilter
from models.modifiers import PTModifier, PTTemp

Target = Union["GameCard", list["GameCard"], int, None]

@dataclass
class ActivatedAbility:
    card: "GameCard"
    cost_tap: bool
    cost_mana: str
    target_filter: Optional[Callable[["GameState", "GameCard"], Target]] = None
    effect: Callable[["GameState", "GameCard", Target], None] = None

    def can_activate(self, gs: "GameState") -> bool:
        if self.cost_tap and self.card.is_tapped:
            return False
        if self.cost_mana and not gs.boards[self.card.orig_owner_id].can_meet_casting_cost(self.cost_mana):
            return False
        return True


def psionic_entity_deals_damage(gs: "GameState", source: "GameCard", t: Target):
    source.deal_damage_to_player(gs, 2, t) if isinstance(t, int) else source.deal_damage_to_card(gs, 2, t)
    source.deal_damage_to_card(gs, 3, source)

def add_activated_abilities(cards: list["GameCard"]) -> None:
    for c in cards:
        if c.props.slug == 'blessing':
            c.abilities.append(ActivatedAbility(
                c, False, 'W', target_filter=None,
                effect=lambda gs, source, t: t.pt_temps.append(PTTemp(1, 1))))
        if c.props.slug == 'flood':
            c.abilities.append(ActivatedAbility(
                c, False, 'UU', target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().tapped(False).has('Flying', False).result(),
                                  effect=lambda gs, source, t: t.tap(gs)))
        if c.props.slug == 'holy-armor':
            c.abilities.append(ActivatedAbility(c, False, 'W', target_filter=None,
                               effect=lambda gs, source, t: t.pt_temps.append(PTTemp(0, 1))))
        if c.props.slug == 'northern-paladin':
            c.abilities.append(ActivatedAbility(
                c, True, 'WW', target_filter=lambda gs, source: CardFilter(gs).in_play().black().by_type(['Creature', 'Enchantment']).result(),
                                  effect=lambda gs, source, t: gs.send_to_graveyard_from_play(t)))
        if c.props.slug in ('pirate-ship', 'prodigal-sorcerer'):
            # damage to card
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: source.deal_damage_to_card(gs, 1, t)))
            # damage to player
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, _: [0, 1],
                               effect=lambda gs, source, t: source.deal_damage_to_player(gs, 1, t)))
        if c.props.slug in ('psionic-entity'):
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: psionic_entity_deals_damage(gs, source, t)))
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, _: [0, 1],
                               effect=lambda gs, source, p_id: psionic_entity_deals_damage(gs, source, p_id)))
        if c.props.slug == 'wall-of-water':
            c.abilities.append(ActivatedAbility(c, False, 'U', target_filter=None,
                               effect=lambda gs, source, t: t.pt_temps.append(PTTemp(1, 0))))


if __name__ == '__main__':
    ...
