import json
import unittest

from models.constants import OS_SCRYFALL_SETS
from models.game_card.card import CardUniverse
from models.game_card.game_card import GameCard
from models.game_card.slug_effect_map import INVOCATIONS
from tests.setup_helpers import TestGame


class TestSlugs(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_all_slug_mappings_are_legitimate(self):
        with open('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/testing/card_statuses.json', 'r') as f:
            all_cards: dict[str: str] = json.load(f)

        with open('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/models/game_card/tokens.json', 'r') as f:
            tokens: dict[str: str] = json.load(f)

        for slug in INVOCATIONS:
            if slug in tokens:
                continue
            self.assertIn(slug, all_cards, f'{slug} not found')

    def test_lands_have_no_spells(self):
        """This assumption is made in casting pipeline logic"""
        cu = CardUniverse(OS_SCRYFALL_SETS)
        with open('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/models/game_card/tokens.json', 'r') as f:
            tokens: dict[str: str] = json.load(f)
        for slug, eff_specs in INVOCATIONS.items():
            if slug in tokens:
                continue
            card = cu[slug]
            if not card.is_land:
                continue
            for eff_spec in eff_specs:
                self.assertFalse(eff_spec.is_spell)


if __name__ == '__main__':
    unittest.main()
