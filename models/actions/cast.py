from dataclasses import dataclass

from constants import BASIC_LAND_MANA_PRODUCED
from models.actions.base import Action
from models.game_card import GameCard


@dataclass
class CastToBoard(Action):
    card: GameCard
    x_values_for_variable_cast: int | None = None

    def __repr__(self) -> str:
        variable_cast_text = '' if not self.x_values_for_variable_cast else f', X={self.x_values_for_variable_cast}'
        return f"Cast {self.card.props.name}{variable_cast_text}"

    def play(self) -> None:
        if self.x_values_for_variable_cast is not None:
            cast_cost = self.card.props.casting_cost[:].replace('X', str(self.x_values_for_variable_cast))
            self.gs.mana_pools[self.player_idx].pay(cast_cost)
            self.card.variable_x = self.x_values_for_variable_cast
        else:
            self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        board = self.gs.boards[self.player_idx]
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        board.play_to_board(self.card)
        if self.card.props.is_land:
            self.gs.turn.has_played_land = True
        # if self.card.props.is_basic_land:
        #     color = BASIC_LAND_MANA_PRODUCED[self.card.props.slug]
        #     self.gs.mana_pools[self.player_idx].add(color)

        # TODO: for speed of testing, perms are being auto-cast, instead of being added to the stack
        self.gs.trigger('cast', self.card)
        print(f"Successfully cast {self.card.props.name}")


@dataclass
class CastToTargetAddToStack(Action):
    card: GameCard
    target: GameCard | list[GameCard] | None
    x_values_for_variable_cast: int | None = None

    def __post_init__(self):
        self.card.variable_x = self.x_values_for_variable_cast

    def __repr__(self) -> str:
        target_text, variable_cast_text = '', ''
        if isinstance(self.target, list) and self.target:
            target_text = f", targeting {', '.join([c.props.name for c in self.target])}"
        elif isinstance(self.target, GameCard):
            target_text = ', targeting ' + self.target.props.name
        if self.x_values_for_variable_cast is not None:
            variable_cast_text = f", X={self.x_values_for_variable_cast}"
        return f"Cast {self.card.props.name}{target_text}{variable_cast_text}"

    def play(self) -> None:
        if self.x_values_for_variable_cast is not None:
            cast_cost = self.card.props.casting_cost[:].replace('X', str(self.x_values_for_variable_cast))
            self.gs.mana_pools[self.player_idx].pay(cast_cost)
            self.card.variable_x = self.x_values_for_variable_cast
        else:
            self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        self.gs.action_stack.push(self, self.gs)


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
        self.gs.action_stack.push(self, self.gs)
