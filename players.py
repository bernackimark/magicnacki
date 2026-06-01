from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from common.file_utils import read_json_file
from game_state import GameState
from models.actions.base import Action
from models.game_card.card_filter import ARG_LOOKUP, CardFilter
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
                sel_action = input("Please select an action (type a card slug for info; CF for card filter; C to concede) ")
                if sel_action.isnumeric():
                    sel_action = int(sel_action)
                    break
                elif sel_action.lower() == 'c':
                    return Concede(self.idx, gs)
                elif sel_action.lower() == 'cf':
                    args = input(f"Enter args: ({', '.join(ARG_LOOKUP)}) (ex: color=R,G p>=3 kwa=Trample set=lea) ")
                    print_slugs_from_args(args)
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

def print_slugs_from_args(arg_str: str):
    cf = CardFilter()
    matching_cards = cf.from_arg_parse(arg_str)
    for c in sorted(matching_cards, key=lambda x: x.slug):
        print(c.slug)
