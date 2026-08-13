import unittest

from models.counter_tokens import DOOM
from models.events_all import UpkeepEvent
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestAvailableActionsFromHand(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_can_activate_ability_simple(self):
        card = self.g.card('aladdins-ring')
        self.g.battlefield('island', cnt=8)
        aa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(1, aa_cnt)

    def test_cannot_activate_with_insufficient_mana(self):
        card = self.g.battlefield('aladdins-ring')  # {1}: Deal 4 damage to any player
        aa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(aa_cnt, 0)

    def test_cannot_surpass_max_activations_per_turn(self):
        card = self.g.battlefield('fire-drake')  # {R}: Pump only once per turn
        self.g.battlefield('mountain', cnt=4)
        aa = card.activated_abilities[0]
        aaa_cnt = len(self.gs.get_available_activated_abilities(card))
        self.assertEqual(1, aaa_cnt)
        self.g.activate_ability(aa, card)
        self.assertEqual(0, len(self.gs.get_available_activated_abilities(card)))

    def test_either_player_can_activate_via_allowed_activators(self):
        """... {4}: Remove a doom ctr from AC. Any player may activate this ability but only during any upkeep step."""
        card = self.g.battlefield('armageddon-clock')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertEqual(1, card.counters.get_count(DOOM))

        self.g.next_turn()
        self.gs.event_mgr.emit(UpkeepEvent(0))

        self.g.next_turn()
        self.g.mana('RRRR')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(0, self.gs.action_on_idx)
        self.assertTrue(any(a.source is card for a in self.gs.add_activated_abilities_from_board()))

        self.g.next_turn(True)
        self.g.mana('WWWW', owner=1)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, self.gs.action_on_idx)
        self.assertTrue(any(a.source is card for a in self.gs.add_activated_abilities_from_board()))


if __name__ == '__main__':
    unittest.main()
