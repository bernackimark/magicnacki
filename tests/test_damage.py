import unittest

from models.effects.listeners_generic import PreventNextDamageToEOT
from models.effects.resolvers_generic import PreventNextDamageToSourceOwner
from tests.setup_helpers import TestGame


class TestDamage(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_cop(self):
        red_source = self.g.card('goblin-hero')
        cop = self.g.battlefield('circle-of-protection-red', owner=1)
        self.g.mana('WW', owner=1)
        PreventNextDamageToSourceOwner().resolve(self.gs, cop, red_source)
        self.gs.apply_damage(red_source, 5, 1, True)
        self.assertEqual(self.gs.score_mgr.life[1], 20)

    def test_unblocked_attacker_deals_damage_to_player(self):
        attacker = self.g.battlefield('grizzly-bears')
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        starting_life = self.gs.score_mgr.life[1]
        combat.handle_damage()
        self.assertEqual(starting_life - attacker.power, self.gs.score_mgr.life[1])

    def test_multiple_damage_reducers(self):
        card = self.g.card('rakalite')
        self.gs.event_mgr.register(PreventNextDamageToEOT(protected_target=0, preventable_amt=1), card)
        self.gs.event_mgr.register(PreventNextDamageToEOT(protected_target=0, preventable_amt=1), card)
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.gs.apply_damage(bolt, 3, 0)
        self.assertEqual(19, self.gs.score_mgr.life[0])


if __name__ == '__main__':
    unittest.main()
