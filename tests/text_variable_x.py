import unittest

from models.actions.activate_ability import ActivateAbility
from models.actions.cast import BeginSpellCastAction, CastToTargetAddToStack
from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.special import SelectXAction
from models.actions.stack_accept_counter import AcceptAction
from models.choice_actions_all import XValueChoice
from tests.setup_helpers import create_engine_and_universe, get_card, add_to_battlefield

class TestVariableX(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_x_cast_simple(self):
        card = get_card(self.gs, 'stream-of-life', 0)
        mana = [get_card(self.gs, 'forest', 0) for _ in range(4)]
        [add_to_battlefield(m, self.gs) for m in mana]
        eff_spec = card.abilities[0]
        choice = XValueChoice(0, self.gs, card, [1, 2, 3], eff_spec)  # create choices for user
        SelectXAction(0, self.gs, choice, 3).play()  # select a value of 3, assign 3 to card.extras['x']
        CastToTargetAddToStack(0, self.gs, card, 0, eff_spec).play()  # add spell to stack
        AcceptAction(1, self.gs).play()  # opponent accepts spell; spell materializes, adding 3 life
        self.assertEqual(self.gs.score_mgr.life[0], 23)

    def test_x_activation_simple(self):
        """{XT}: Banshee deals half X damage, rounded down, to any target, and half X damage, rounded up to you"""
        card = get_card(self.gs, 'banshee', 0)
        mana = [get_card(self.gs, 'plains', 0) for _ in range(3)]
        add_to_battlefield(card, self.gs)
        [add_to_battlefield(m, self.gs) for m in mana]
        PassTheTurn(0, self.gs).play()  # clears summoning sickness
        PassTheTurn(1, self.gs).play()
        eff_spec = card.abilities[0]
        aa = card.activated_abilities[0]
        choice = XValueChoice(0, self.gs, card, [1, 2, 3], eff_spec, aa)  # create choices for user
        SelectXAction(0, self.gs, choice, 3).play()  # select a value of 3, assign 3 to card.extras['x']
        ActivateAbility(0, self.gs, aa, 1).play()  # add activated ability spell to stack
        AcceptAction(1, self.gs).play()  # opponent accepts spell; spell materializes, adding 3 life
        self.assertEqual((self.gs.score_mgr.life[0], self.gs.score_mgr.life[1]), (18, 19))

    def test_xx(self):
        card = get_card(self.gs, 'part-water', 0)  # casting_cost: XXU
        self.gs.pile_mgr.hands[0].cards.append(card)
        self.gs.mana_pools[0].add_floating('U', 4)
        eff_spec = card.abilities[0]
        BeginSpellCastAction(0, self.gs, card, eff_spec).play()
        self.assertEqual(len(self.gs.pending_choice.get_actions()), 1)


if __name__ == '__main__':
    unittest.main()
