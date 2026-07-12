import unittest

from models.actions.mana import PayMana
from models.phase_manager import Phase
from tests.setup_helpers import TestGame


class TestCardsDEF(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_fellwar_stone_1(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('plains', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)  # type: ignore
        self.assertEqual(1, len(self.gs.pending_choice.get_actions()))

    def test_fellwar_stone_2(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('birds-of-paradise', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)  # type: ignore
        self.assertEqual(5, len(self.gs.pending_choice.get_actions()))

    def test_field_of_dreams(self):
        """Players play with the top card of their libraries revealed"""
        self.g.battlefield('field-of-dreams')
        top_card = self.gs.pile_mgr.libraries[0][0]
        self.assertTrue(top_card.is_face_up)
        self.gs.pile_mgr.draw(0)
        top_card = self.gs.pile_mgr.libraries[0][0]
        self.assertTrue(top_card.is_face_up)

    def test_force_of_nature(self):
        """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
        self.g.battlefield('force-of-nature')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.assertEqual(12, self.gs.score_mgr.life[0])

        self.g.mana('GGGGG')  # five forests
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        for a in self.gs.pending_choice.get_actions():
            if isinstance(a, PayMana):
                a.play()
        self.assertEqual(1, len([c for c in self.gs.pile_mgr.boards[0]
                                 if c.props.slug == 'forest' and not c.is_tapped]))

    def test_forcefield(self):
        """{1}: The next time an unblocked creature of your choice would deal combat damage to you this turn,
        prevent all but 1 of that damage"""
        ff = self.g.battlefield('forcefield', owner=1)
        self.g.mana('U', owner=1)
        attacker = self.g.battlefield('grizzly-bears')  # 2/2
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        self.g.activate_ability(ff.activated_abilities[0], attacker, 1)
        combat.handle_damage()
        self.assertEqual(19, self.gs.score_mgr.life[1])


if __name__ == '__main__':
    unittest.main()

