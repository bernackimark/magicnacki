from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass

from common.file_utils import read_json_file
from game_state import GameState, Action
from models.actions.base import Action
from models.game_over import Concede


@dataclass
class Player(ABC):
    idx: int
    name: str
    is_bot: bool = False

    @abstractmethod
    def make_move(self, gs: GameState, available_actions: list[Action]):
        ...


@dataclass
class ConsolePlayer(Player):
    def make_move(self, gs: GameState, available_actions: list[Action]) -> Action | None:
        if not available_actions:
            return None
        for i, avail_action in enumerate(available_actions):
            print(f"{i}: {avail_action}")
        with suppress(KeyboardInterrupt):
            while True:
                sel_action = input("Please select an action (type a card slug for info; C to concede) ")
                if sel_action.isnumeric():
                    sel_action = int(sel_action)
                    break
                elif sel_action.lower() == 'c':
                    return Concede(self.idx, gs)
                else:
                    print_quick_card_info(sel_action)
            return available_actions[sel_action]


def print_quick_card_info(requested_slug: str):
    data = read_json_file('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/gatherer/card_data.json')
    for set_, set_data in data.items():
        for slug, card_data in set_data.items():
            if slug == requested_slug:
                for k, v in card_data.items():
                    print(f'{k}: {v}')
                return
    print(f'slug {requested_slug} not found in database')
