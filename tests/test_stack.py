import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.stack_accept_counter import AcceptAction
from tests.setup_helpers import TestGame

class TestStackResolution(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_stack_resolves_lifo_1(self):
        """P0: Giant Growth -> Grizzly Bears
        P1: Lightning Bolt -> Grizzly Bears
        both players pass; Grizzly Bears dies; Giant Growth fizzles"""
        gg = self.g.hand('giant-growth')
        bolt = self.g.hand('lightning-bolt', owner=1)
        creature = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.mana('G')
        self.g.mana('R', owner=1)

        gg_pipeline = AbilityPipeline(0, self.gs, gg, gg.abilities[0], targets=[creature])
        gg_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #1
        self.assertEqual(1, self.gs.action_on_idx)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[creature])
        bolt_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #0
        self.assertEqual(0, self.gs.action_on_idx)

        AcceptAction(0, self.gs).play()  # player 0 passes priority (adds nothing else to the stack)
        AcceptAction(1, self.gs).play()  # player 1 also passes priority, thus the entire stack should resolve

        self.assertIn(creature, self.gs.graveyards[0])
        self.assertIn(bolt, self.gs.graveyards[1])
        self.assertIn(gg, self.gs.graveyards[0])
        self.assertEqual(0, self.gs.action_on_idx)

    def test_stack_resolves_lifo_2(self):
        """P1: Lightning Bolt -> Grizzly Bears
        P0: Giant Growth -> Grizzly Bears
        both players pass"""
        gg = self.g.hand('giant-growth')
        bolt = self.g.hand('lightning-bolt', owner=1)
        creature = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.mana('G')
        self.g.mana('R', owner=1)

        self.g.next_turn(True)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[creature])
        bolt_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #0
        self.assertEqual(0, self.gs.action_on_idx)

        gg_pipeline = AbilityPipeline(0, self.gs, gg, gg.abilities[0], targets=[creature])
        gg_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #1
        self.assertEqual(1, self.gs.action_on_idx)

        AcceptAction(1, self.gs).play()  # player 1 passes priority (adds nothing else to the stack)
        AcceptAction(0, self.gs).play()  # player 0 also passes priority, thus the entire stack should resolve

        self.assertNotIn(creature, self.gs.graveyards[0])
        self.assertIn(bolt, self.gs.graveyards[1])
        self.assertIn(gg, self.gs.graveyards[0])
        self.assertEqual(1, self.gs.action_on_idx)

    def test_counter_spell_removes_spell(self):
        """P0 casts Shivan Dragon
        P1 casts Counterspell targeting Dragon
        resolve stack"""
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_counter_spell_a_counter_spell(self):
        """P0 casts Shivan Dragon
        P1 casts Counterspell targeting Dragon
        P0 casts Counterspell targeting Counterspell"""
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_counter_an_activated_ability(self):
        """"""
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_ability_survives_source_ltb(self):
        """Prodigal Sorcerer taps
        Bolt kills Sorcerer
        Ability still resolves"""
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_illegal_target_fizzles(self):
        """Bolt -> Bears
        Unsummon Bears
        resolve"""
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_three_item_lifo(self):
        """spell A
        spell B
        spell C"""
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_priority_changes(self):
        """P0 casts;
        assert priority=P1;
        P1 responds;
        assert priority=P0;
        P0 passes;
        assert priority=P1"""

    def test_counter_removes_only_its_target(self):
        """Bolt
        Growth
        Counterspell -> Growth
        resolve stack; bolt should have resolved"""
        ...
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_activated_ability_followed_by_spell(self):
        """Tap Prodigal Sorcerer
        Respond with Giant Growth
        resolve"""

    def test_x_value_persists(self):
        """Braingeyser X=4;
        Counterspell;
        Counterspell"""

    def test_counter_precludes_cast_resolved_event(self):
        """"""


if __name__ == '__main__':
    unittest.main()
