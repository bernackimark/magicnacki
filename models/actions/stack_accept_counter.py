from dataclasses import dataclass

from models.actions.base import Action
from models.actions.cast import CastToTargetAddToStack
from utils import flip


@dataclass
class AcceptAction(Action):
    def __repr__(self) -> str:
        return f"Accept {self.gs.action_stack.last_action}"

    def play(self) -> None:
        last_action: CastToTargetAddToStack = self.gs.action_stack.last_action
        card = last_action.card
        target = last_action.target
        if card.props.is_aura:
            card.attached_to = target
            target.modifiers.auras.append(card)
            self.gs.boards[target.orig_owner_id].play_to_board(card)

        self.gs.trigger('cast', card, target)
        print(f"Successfully cast {card.props.name}")

        self.gs.action_on_idx = self.gs.action_stack.first_actor_idx  # action returns to the first actor
        self.gs.action_stack.clear()


@dataclass
class CounterAction(Action):
    action: Action

    def __repr__(self) -> str:
        return f"In response to {self.gs.action_stack.last_action}: {self.action}"

    def play(self) -> None:
        self.gs.action_stack.add(self.action, self.gs)
        self.gs.action_on_idx = flip(self.gs.action_on_idx)
