"""Obtain data from Scryfall cards search API; write to a json file"""

import requests

from common.file_utils import write_json_to_file
from constants import OS_SET_CODES

OUTPUT_PATH = '/gatherer-scryfall/scryfall_card_data_OS.json'
OUTPATH_PATH_TOKENS = '/gatherer-scryfall/scryfall_token_data.json'

def get_scryfall_set_data(sets: list[str]) -> list[dict]:
    """This only obtains one instance of a card -- even if the card appears in multiple sets"""
    query = " or ".join(f"set:{s}" for s in sets)
    url = "https://api.scryfall.com/cards/search"
    params = {"q": query}
    cards = []
    while url:
        response = requests.get(url, params=params)
        data = response.json()
        cards.extend(data["data"])
        # pagination
        url = data.get("next_page") if data.get("has_more") else None
    print(f"Retrieved {len(cards)} cards")
    return cards

def get_get_scryfall_tokens() -> list[dict]:
    query = "is:token"
    url = "https://api.scryfall.com/cards/search"
    params = {"q": query}
    cards = []
    while url:
        response = requests.get(url, params=params)
        data = response.json()
        cards.extend(data["data"])
        # pagination
        url = data.get("next_page") if data.get("has_more") else None
    print(f"Retrieved {len(cards)} tokens")
    return cards


if __name__ == '__main__':
    if input('Are you sure you want to overwrite the existing scryfall data file? (Y/n) ') in ('Y', 'y'):
        the_data = get_scryfall_set_data(OS_SET_CODES)
        write_json_to_file(OUTPUT_PATH, the_data)
    if input('Are you sure you want to overwrite the existing scryfall TOKEN file (Y/n) ') in ('Y', 'y'):
        token_data = get_get_scryfall_tokens()
        write_json_to_file(OUTPATH_PATH_TOKENS, token_data)
