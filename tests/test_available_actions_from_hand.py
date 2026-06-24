import unittest

from tests.setup_helpers import create_engine_and_universe, get_card, add_to_battlefield


class TestAvailableActionsFromHand(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/testing/game_testing_settings.json',
                                                                'engine_testing_setup_a', True)
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_can_cast_aura_with_valid_target(self):
        mana = get_card(self.gs, 'plains', 0)
        creature = get_card(self.gs, 'savannah-lions', 0)
        add_to_battlefield(mana, self.gs)
        add_to_battlefield(creature, self.gs)
        aura = get_card(self.gs, 'holy-strength', 0)
        self.gs.pile_mgr.hands[0].cards.append(aura)
        self.assertIn('Cast Holy Strength', [a.__repr__() for a in self.gs.available_actions_from_hand()])

    def test_cannot_cast_auras_without_valid_target(self):
        mana = get_card(self.gs, 'plains', 0)
        add_to_battlefield(mana, self.gs)
        aura = get_card(self.gs, 'holy-strength', 0)
        self.gs.pile_mgr.hands[0].cards.append(aura)
        self.assertNotIn('Cast Holy Strength', [a.__repr__() for a in self.gs.available_actions_from_hand()])


if __name__ == '__main__':
    unittest.main()
