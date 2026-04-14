from dataclasses import dataclass
from pathlib import Path

from common.file_utils import read_json_file, update_json_file_with_dict, write_to_json_file_one_line_per_key

FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "decks.json"

@dataclass
class DeckData:
    deck_id: str
    user_id: str
    name: str
    main: list[list[str, int]]
    side: list[list[str, int]]

def get_decks() -> list[DeckData]:
    data = read_json_file(FILE_PATH)
    return [DeckData(k, v['user_id'], v['name'], v['main'], v['side']) for k, v in data.items()]

def get_deck(deck_id: str, user_id: str) -> DeckData:
    data = read_json_file(FILE_PATH)
    for k, v in data.items():
        if k == deck_id and v['user_id'] == user_id:
            return DeckData(k, v['user_id'], v['name'], v['main'], v['side'])

def get_user_decks(user_id: str) -> list[DeckData]:
    data = read_json_file(FILE_PATH)
    return [DeckData(k, v['user_id'], v['name'], v['main'], v['side'])
            for k, v in data.items() if v['user_id'] == user_id]

def update_deck(deck_id: str, name: str, main: list[list[str, int]], side: list[list[str, int]]) -> None:
    data = read_json_file(FILE_PATH)
    for k, v in data.items():
        if k != deck_id:
            continue
        v['name'] = name
        v['main'] = main
        v['side'] = side
    write_to_json_file_one_line_per_key(FILE_PATH, data)
