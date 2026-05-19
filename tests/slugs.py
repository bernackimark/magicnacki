import json

from models.game_card.card_effect_specs import INVOCATIONS

def all_slug_mappings_are_legitimate():
    with open('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/testing/card_statuses.json', 'r') as f:
        all_cards: dict[str: str] = json.load(f)

    for slug in INVOCATIONS:
        assert slug in all_cards, f'{slug} not found'


all_slug_mappings_are_legitimate()