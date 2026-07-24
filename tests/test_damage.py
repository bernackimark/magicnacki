import unittest

from models.effects.listeners_generic import PreventNextDamageTo
from tests.setup_helpers import TestGame


class TestDamage(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_prevent_all_damage_1(self):
        """Prevent all damage that would be dealt to AP by artifact creatures"""
        protected = self.g.battlefield('argothian-pixies')
        dealer = self.g.battlefield('juggernaut', owner=1)
        self.g.next_turn(True)
        self.g.combat(dealer, protected)
        self.assertIn(protected, self.gs.boards[0])

    def test_cop(self):
        red_source = self.g.card('goblin-hero')
        cop = self.g.battlefield('circle-of-protection-red', owner=1)
        self.g.mana('WW', owner=1)
        eff = PreventNextDamageTo(protected=1)
        self.gs.event_mgr.register(eff, cop)
        self.gs.apply_damage(red_source, 5, 1, True)
        self.assertEqual(self.gs.life[1], 20)

    def test_unblocked_attacker_deals_damage_to_player(self):
        attacker = self.g.battlefield('grizzly-bears')
        self.g.combat(attacker, None)
        self.assertEqual(20 - attacker.power, self.gs.life[1])

    def test_multiple_damage_reducers(self):
        card = self.g.card('rakalite')
        eff = PreventNextDamageTo(protected=0, preventable_amt=1)
        self.gs.event_mgr.register(eff, card)
        eff = PreventNextDamageTo(protected=0, preventable_amt=1)
        self.gs.event_mgr.register(eff, card)
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.gs.apply_damage(bolt, 3, 0)
        self.assertEqual(19, self.gs.life[0])


if __name__ == '__main__':
    unittest.main()
