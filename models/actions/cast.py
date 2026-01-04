from dataclasses import dataclass

from constants import BASIC_LAND_MANA_PRODUCED
from models.actions.base import Action
from models.game_card import GameCard


@dataclass
class CastToBoard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Cast {self.card.props.name}"

    def play(self) -> None:
        board = self.gs.boards[self.player_idx]
        self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        board.play_to_board(self.card)
        if self.card.props.is_land:
            self.gs.turn.has_played_land = True
        if self.card.props.is_basic_land:
            color = BASIC_LAND_MANA_PRODUCED[self.card.props.slug]
            self.gs.mana_pools[self.player_idx].add(color)

        # TODO: for speed of testing, perms are being auto-cast, instead of being added to the stack
        self.gs.trigger('cast', self.card)
        print(f"Successfully cast {self.card.props.name}")


@dataclass
class CastToTargetAddToStack(Action):
    card: GameCard
    target: GameCard | list[GameCard] | None

    def __repr__(self) -> str:
        target_text = ''
        if isinstance(self.target, list) and self.target:
            target_text = f", targeting {', '.join([c.props.name for c in self.target])}"
        elif isinstance(self.target, GameCard):
            target_text = ', targeting ' + self.target.props.name
        return f"Cast {self.card.props.name}{target_text}"

    def play(self) -> None:
        self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        self.gs.action_stack.add(self, self.gs)


@dataclass
class CastCounter(Action):
    card: GameCard
    target: Action

    def __repr__(self):
        return f"Cast {self.card.props.name} to counter {self.target}"

    def play(self) -> None:
        self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        self.gs.action_stack.add(self, self.gs)
