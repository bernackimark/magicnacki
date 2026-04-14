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

def update_deck(deck_id: str, name: str, main: list[list[str | int]], side: list[list[str | int]]) -> None:
    data = read_json_file(FILE_PATH)
    for k, v in data.items():
        if k != deck_id:
            continue
        v['name'] = name
        v['main'] = main
        v['side'] = side
    write_to_json_file_one_line_per_key(FILE_PATH, data)

def create_new_deck(user_id: str, name: str, main: list[list[str | int]], side: list[list[str | int]]):
    existing_decks = get_decks()
    deck_id = str(max([int(d.deck_id) for d in existing_decks]) + 1) if existing_decks else "0"
    record = {deck_id: {'user_id': user_id, 'name': name, 'main': main, 'side': side}}
    update_json_file_with_dict(FILE_PATH, record)

def delete_deck(deck_id: str, user_id: str) -> None:
    if not get_deck(deck_id, user_id):
        return
    data = read_json_file(FILE_PATH)
    del data[deck_id]
    write_to_json_file_one_line_per_key(FILE_PATH, data)


"""
{
  "0": {"user_id": "0", "name": "Aerial Domination", "main": [["amnesia", 4], ["mahamoti-djinn", 4], ["air-elemental", 4], ["island", 20], ["lord-of-atlantis", 4], ["phantom-monster", 4]], "side": []},
  "1": {"user_id": "1", "name": "White & Red Stuff", "main": [["mountain", 10], ["plains", 10], ["the-hive", 4], ["orcish-artillery", 4], ["keepers-of-the-faith", 4], ["tundra-wolves", 4], ["savannah-lions", 4]], "side": []}
}
"""