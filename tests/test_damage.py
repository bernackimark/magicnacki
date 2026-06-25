import unittest

from models.effects.resolvers_generic import PreventNextDamageToSourceOwner
from tests.setup_helpers import add_to_battlefield, create_engine_and_universe, get_card


class TestDamage(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_cop(self):
        red_source = get_card(self.gs, 'goblin-hero', 0)
        cop = get_card(self.gs, 'circle-of-protection-red', 1)
        plains = get_card(self.gs, 'plains', 1)
        p2 = get_card(self.gs, 'plains', 1)
        add_to_battlefield(plains, self.gs)
        add_to_battlefield(p2, self.gs)
        add_to_battlefield(cop, self.gs)
        PreventNextDamageToSourceOwner().resolve(self.gs, cop, red_source)
        self.gs.apply_damage(red_source, 5, 1, True)
        self.assertEqual(self.gs.score_mgr.life[1], 20)

    def test_unblocked_attacker_deals_damage_to_player(self):
        attacker = get_card(self.gs, 'grizzly-bears', 0)
        add_to_battlefield(attacker, self.gs)
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        starting_life = self.gs.score_mgr.life[1]
        combat.handle_damage()
        self.assertEqual(starting_life - attacker.power, self.gs.score_mgr.life[1])


if __name__ == '__main__':
    unittest.main()
