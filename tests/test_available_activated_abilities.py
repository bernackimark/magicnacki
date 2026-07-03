import unittest

from models.actions.activate_ability import ActivateAbility
from tests.setup_helpers import TestGame


class TestAvailableActionsFromHand(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_can_activate_ability_simple(self):
        card = self.g.card('aladdins-ring')
        self.g.battlefield('island', cnt=8)
        aa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aa_cnt, 2)  # aladdins-ring should have 2 distinct targets (player #0 & player #1)

    def test_cannot_activate_with_insufficient_mana(self):
        card = self.g.battlefield('aladdins-ring')  # {1}: Deal 4 damage to any player
        aa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aa_cnt, 0)

    def test_cannot_surpass_max_activations_per_turn(self):
        card = self.g.battlefield('fire-drake')  # {R}: Pump only once per turn
        self.g.battlefield('mountain', cnt=4)
        aa = card.activated_abilities[0]
        aaa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aaa_cnt, 1)
        ActivateAbility(0, self.gs, aa, card).play()
        aaa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aaa_cnt, 0)


if __name__ == '__main__':
    unittest.main()
