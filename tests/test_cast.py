import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastWithNoSpellEffect
from models.actions.stack_accept_counter import AcceptAction
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestCast(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_allowed_turn_and_phase(self):
        """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
        reset = self.g.hand('reset')
        self.g.mana('UU')
        self.assertFalse(any(a.source is reset for a in self.gs.available_actions_from_hand()))
        self.g.next_turn(True)
        self.assertFalse(any(a.source is reset for a in self.gs.available_actions_from_hand()))
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        self.gs.action_on_idx = 0
        print()
        print(self.gs.hands[0])
        print(self.gs.available_actions_from_hand())
        print()
        self.assertTrue(any(a.source is reset for a in self.gs.available_actions_from_hand()))

    def test_cast_land_doesnt_reach_stack(self):
        self.gs.hands[0].clear()
        card = self.g.hand('library-of-alexandria')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        self.assertFalse(any(isinstance(a, AbilityPipeline) for a in self.gs.available_actions_from_hand()))
        available_actions[0].play()
        self.assertFalse(self.gs.action_stack.actions)
        self.assertIn(card, self.gs.boards[0])

    def test_cast_land_w_listeners_still_register(self):
        self.gs.hands[0].clear()
        card = self.g.hand('safe-haven')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        available_actions[0].play()
        self.assertTrue(self.g.card_has_a_registered_listener(card))

    def test_cast_permanent_w_no_effects(self):
        card = self.g.hand('merfolk-of-the-pearl-trident')
        self.g.mana('U')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        cast_action = next(a for a in available_actions if isinstance(a, CastWithNoSpellEffect) and a.source is card)
        cast_action.play()
        self.assertTrue(self.gs.action_stack.last_action.source is card)
        AcceptAction(1, self.gs).play()
        self.assertIn(card, self.gs.boards[0])

    def test_cast_card_with_effects_but_no_spell(self):
        card = self.g.hand('ankh-of-mishra')
        self.g.mana('RRRRRR')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        cast_action = next(a for a in available_actions if isinstance(a, CastWithNoSpellEffect) and a.source is card)
        cast_action.play()
        AcceptAction(1, self.gs).play()
        self.assertTrue(any(e.source is card for effs in self.gs.event_mgr.event_listeners.values() for e in effs))

    def test_cast_card_with_spell_with_no_effect(self):
        card = self.g.hand('animate-wall')
        host = self.g.battlefield('wall-of-brambles')
        self.g.mana('W')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        ability_action = next(a for a in available_actions if isinstance(a, AbilityPipeline) and a.source is card)
        ability_action.targets.append(host)
        ability_action.resolve_ability()
        self.assertTrue(card.host is host)


if __name__ == '__main__':
    unittest.main()
