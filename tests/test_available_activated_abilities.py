import unittest

from models.actions.activate_ability import ActivateAbility
from models.effects.base import ActivatedAbility
from tests.setup_helpers import create_engine_and_universe, get_card, add_to_battlefield


class TestAvailableActionsFromHand(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_can_activate_ability_simple(self):
        card = get_card(self.gs, 'aladdins-ring', 0)
        mana = [get_card(self.gs, 'island', 0) for _ in range(8)]
        add_to_battlefield(card, self.gs)
        [add_to_battlefield(m, self.gs) for m in mana]
        aa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aa_cnt, 2)  # aladdins-ring should have 2 distinct targets (player #0 & player #1)

    def test_cannot_activate_with_insufficient_mana(self):
        card = get_card(self.gs, 'aladdins-ring', 0)  # {1}: Deal 4 damage to any player
        add_to_battlefield(card, self.gs)
        aa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aa_cnt, 0)

    def test_cannot_surpass_max_activations_per_turn(self):
        card = get_card(self.gs, 'fire-drake', 0)  # {R}: Pump only once per turn
        mana = [get_card(self.gs, 'mountain', 0) for _ in range(4)]
        add_to_battlefield(card, self.gs)
        [add_to_battlefield(m, self.gs) for m in mana]
        aa = card.activated_abilities[0]
        aaa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aaa_cnt, 1)
        ActivateAbility(0, self.gs, aa, card).play()
        aaa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aaa_cnt, 0)


if __name__ == '__main__':
    unittest.main()
