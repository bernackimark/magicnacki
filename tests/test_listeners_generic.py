import unittest

from models.counter_tokens import DOOM
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestListenersGeneric(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_multiple_listeners_firing_on_same_event(self):
        upkeep_card1 = self.g.battlefield('armageddon-clock')  # at controller upkeep, add a counter
        self.g.battlefield('serendib-efreet')  # at controller upkeep, deal one damage to owner
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, upkeep_card1.counters.get_count(DOOM))
        self.assertEqual(19, self.gs.life[0])


if __name__ == '__main__':
    unittest.main()
