from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class ActivatedAbility:
    card: "GameCard"
    cost_tap: bool = False
    cost_mana: str = ""
    target_filter: Optional[Callable[["GameState", "GameCard"], list["GameCard"]]] = None
    effect: Callable[["GameState", "GameCard", Optional["GameCard"]], None] = None

    def can_activate(self, gs: "GameState") -> bool:
        if self.cost_tap and self.card.is_tapped:
            return False
        if self.cost_mana and not gs.boards[self.card.orig_owner_id].can_meet_casting_cost(self.cost_mana):
            return False
        return True


def add_activated_abilities(cards: list["GameCard"]) -> None:
    # TODO: this would be called from Deck.__post_init__()
    for c in cards:
        if c.props.slug == 'flood':
            aa = ActivatedAbility(c, False, 'UU', target_filter=lambda gs, source: gs.card_filter.in_play().creatures().is_tapped(False).has('Flying').result(),
                                  effect=lambda gs, source, target: gs.tap_card(target))
            c.abilities.append(aa)

