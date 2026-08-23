import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.stack_accept_counter import PassPriority
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestAvailableActionsFromHand(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_active_player_gets_priority_at_beginning_of_turn(self):
        """At the beginning of the turn, the active player gets priority."""
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(0, self.gs.action_on_idx)

    def test_priority_passes_to_opponent(self):
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        PassPriority(0, self.gs).play()
        self.assertEqual(0, self.gs.action_on_idx)

    def test_priority_returns_to_active_player_after_opponent_passes(self):
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        PassPriority(0, self.gs).play()
        PassPriority(1, self.gs).play()
        self.assertEqual(0, self.gs.action_on_idx)

    def test_two_passes_advance_phase(self):
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        PassPriority(0, self.gs).play()
        PassPriority(1, self.gs).play()
        self.assertNotEqual(self.gs.phase_mgr.phase, Phase.MAIN)

    def test_casting_spell_passes_priority_to_opponent(self):
        bolt = self.g.hand('lightning-bolt')
        spell_pipeline = AbilityPipeline(0, self.gs, bolt, bolt.abilities[0], targets=[1])
        spell_pipeline.advance()
        self.assertEqual(1, self.gs.action_on_idx)

    def test_spell_only_resolves_after_both_players_pass(self):
        bolt = self.g.hand('lightning-bolt')
        self.g.mana('R')
        spell_pipeline = AbilityPipeline(0, self.gs, bolt, bolt.abilities[0], targets=[1])
        spell_pipeline.advance()
        PassPriority(1, self.gs).play()
        self.assertEqual(0, self.gs.action_on_idx)
        self.assertEqual(1, len(self.gs.action_stack.actions))
        PassPriority(0, self.gs).play()
        self.assertEqual(0, len(self.gs.action_stack.actions))


if __name__ == '__main__':
    unittest.main()
