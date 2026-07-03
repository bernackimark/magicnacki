import unittest

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


if __name__ == '__main__':
    unittest.main()
