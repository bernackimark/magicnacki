import unittest

from tests.setup_helpers import TestGame


class TestAvailableActionsFromHand(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_can_cast_aura_with_valid_target(self):
        self.g.battlefield('plains', 'savannah-lions')
        card = self.g.hand('holy-strength')
        print(self.gs.perm_querier.can_cast(card, 0))
        print(self.gs.mana_pools[0].available_mana)
        print(self.gs.pile_mgr.boards[0])
        print(card in self.gs.pile_mgr.hands[0].cards)
        self.assertIn(card, [a.source for a in self.gs.available_actions_from_hand()])

    def test_can_cast_aura_to_multiple_valid_targets(self):
        self.g.battlefield('plains', 'savannah-lions', 'tundra-wolves')
        aura = self.g.hand('holy-strength')
        self.g.begin_cast(aura)
        self.assertEqual(2, len(self.gs.pending_choice.get_actions()))

    def test_cannot_cast_auras_without_valid_target(self):
        card = self.g.hand('holy-strength')
        self.g.mana('W')
        self.assertNotIn(card, [a.source for a in self.gs.available_actions_from_hand()])

    def test_cannot_cast_multiple_lands(self):
        land_1 = self.g.hand('plains')
        land_2 = self.g.hand('mountain')
        self.g.cast_and_accept(land_1)
        self.assertFalse(any(a for a in self.gs.available_actions_from_hand() if a.source is land_2))

    def test_cards_w_multiple_spells(self):
        card = self.g.hand('alabaster-potion')  # has two modes
        self.g.mana('WWW')
        cast_actions = [a for a in self.gs.available_actions_from_hand() if a.source is card]
        self.assertEqual(len(cast_actions), 2)


if __name__ == '__main__':
    unittest.main()
