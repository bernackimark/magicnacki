from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass

from game_state import Action, GameState


@dataclass
class Player(ABC):
    idx: int
    name: str
    is_bot: bool = False

    @abstractmethod
    def make_move(self, gs: GameState):
        ...


@dataclass
class ConsolePlayer(Player):
    def make_move(self, gs: GameState) -> Action | None:
        avail_actions = gs.get_available_actions(self.idx)
        if not avail_actions:
            return None
        for i, avail_action in enumerate(avail_actions):
            print(f"{i}: {avail_action}")
        with suppress(KeyboardInterrupt):
            while True:
                sel_action: str = input("Please select an action (or type a card slug to get info about it) ")
                if sel_action.isnumeric():
                    sel_action = int(sel_action)
                    break
                else:
                    card_info = next((c for d in gs.decks_all_cards for c in d.cards if c.props.slug == sel_action), None)
                    if not card_info:
                        print('Card not found')
                        continue
                    props = card_info.props
                    print(props.name, props.casting_cost, props.card_types, props.card_sub_types,
                          props.keyword_abilities, props.oracle_rules_text)
            return avail_actions[sel_action]
