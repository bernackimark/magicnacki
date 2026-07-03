import json
import unittest

from models.game_card.slug_effect_map import INVOCATIONS

class TestSlugs(unittest.TestCase):
    def setUp(self):
        pass

    def test_all_slug_mappings_are_legitimate(self):
        with open('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/testing/card_statuses.json', 'r') as f:
            all_cards: dict[str: str] = json.load(f)

        with open('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/models/game_card/tokens.json', 'r') as f:
            tokens: dict[str: str] = json.load(f)

        for slug in INVOCATIONS:
            if slug in tokens:
                continue
            self.assertIn(slug, all_cards, f'{slug} not found')


if __name__ == '__main__':
    unittest.main()
