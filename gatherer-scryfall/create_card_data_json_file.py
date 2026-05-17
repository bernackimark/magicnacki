import json
import re
import unicodedata

from common.file_utils import read_json_file, write_json_to_file
from constants import OS_SET_CODES, CARD_TYPES, SUPERTYPES

# This file contains one entry per card for all old school sets; cards in multiple sets one have one total entry
OS_CARD_DATA = read_json_file('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/gatherer-scryfall/scryfall_card_data_OS.json')

OUTPUT_PATH = '/Users/Bernacki_Laptop/PycharmProjects/magicnacki/gatherer-scryfall/card_data.json'


def name_to_slug(name: str) -> str:
    """Data cleansing; (ex: 'Air Elemental' -> 'air-elemental')"""
    # normalize unicode accents
    slug = unicodedata.normalize('NFKD', name)
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    slug = slug.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r'[^a-z0-9]+', ' ', slug)
    slug = slug.strip()
    slug = slug.replace(' ', '-')
    return slug

def parse_type_line(type_line: str) -> tuple[list, list, list]:
    """Data cleansing; (ex: "Creature — Horror" -> ([], ['Creature'], ['Horror']))"""
    left, *right = type_line.split(" — ")
    left_parts = left.split()

    supertypes = [x for x in left_parts if x in SUPERTYPES]
    card_types = [x for x in left_parts if x in CARD_TYPES]
    subtypes = right[0].split() if right else []

    return supertypes, card_types, subtypes

def get_all_card_data(set_codes: list[str] | None = None) -> list[dict]:
    """This file has every card through the date in the file name -- one entry per card (maybe each illus) per language;
    "id" is unique to each record; "oracle_id" appears to be the same for each slug"""
    with open('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/gatherer-scryfall/default-cards-20260517090928.json') as f:
        data = json.load(f)
        english_only = [r for r in data if r['lang'] == 'en']
        if not set_codes:
            return english_only
        return [r for r in english_only if r['set'] in set_codes]

def create_sets_data(all_cards_data: list[dict], oracle_id: str) -> dict:
    """Lookup oracle_id in full master scryfall data dump file; create & return a nested dictionary of sets"""
    sets_data = {}
    for card_data in all_cards_data:
        if oracle_id != card_data.get('oracle_id'):
            continue
        sets_data[card_data['set']] = {
            'flavor_text': card_data.get('flavor_text'),
            'image_uris': card_data['image_uris']
        }
    return sets_data


def create_card_data(card_data_all_sets: list[dict]):
    """From the Scryfall master file (here: just the OS sets), create a dictionary -- one entry per slug --
    with the data elements I'm interested (cleaning the data along the way)"""
    d = {}
    for c in OS_CARD_DATA:
        slug = name_to_slug(c['name'])
        d[slug] = {
                    'name': c['name'],
                    'casting_cost': c['mana_cost'].replace('{', '').replace('}', '') if c['mana_cost'] else None,
                    'casting_cost_brackets': c['mana_cost'] if c['mana_cost'] else None,
                    'mana_value': int(c['cmc']) if c['cmc'] else None,
                    'card_type':  c['type_line'],
                    'card_types': parse_type_line(c['type_line'])[1],
                    'card_sub_types': parse_type_line(c['type_line'])[2],
                    'card_super_types': parse_type_line(c['type_line'])[0],
                    'rarity': c['rarity'].capitalize(),
                    'oracle_text': c['oracle_text'],
                    'power': c.get('power'),
                    'toughness': c.get('toughness'),
                    'keywords': c['keywords'],
                    'mana_produced': c.get('produced_mana'),
                    'ids': {
                        'oracle_id': c['oracle_id'],
                        'scryfall_id': c['id'],
                    },
                    'uris': {
                        'scryfall_uri': c['uri'],
                        'rulings_uri': c['rulings_uri']
                    },
                    'sets': create_sets_data(card_data_all_sets, c['oracle_id'])
                }
    return d


if __name__ == '__main__':
    if input('Are you sure you want to write this data to file (Y/n) ') in ('Y', 'y'):
        all_card_data: list[dict] = get_all_card_data(OS_SET_CODES)
        the_card_data: dict = create_card_data(all_card_data)
        write_json_to_file(OUTPUT_PATH, the_card_data)
