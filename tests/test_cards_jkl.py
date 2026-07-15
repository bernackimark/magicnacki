import unittest

from models.counter_tokens import MINUS_ZERO_ONE
from models.systems.phase import Phase
from models.zone import Zone
from tests.setup_helpers import TestGame

class TestCardsJKL(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_jovial_evil(self):
        """JE deals X damage to target opponent, where X is twice the number of white creatures that player controls"""
        self.g.battlefield('savannah-lions', owner=1)
        card = self.g.hand('jovial-evil')
        card.abilities[0].effect.resolve(self.gs, card, 1)  # type: ignore
        self.assertEqual(18, self.gs.score_mgr.life[1])

    # def test_kudzu(self):
    #     """When host becomes tapped, destroy it. Host may attach this Aura to a land of their choice."""
    #     # TODO: aura is already sent to graveyard upon its host being destroyed, just like creature-bond
    #     card = self.g.hand('kudzu')
    #     target = self.g.battlefield('island', owner=1)
    #     other_target_1 = self.g.battlefield('swamp', owner=1)
    #     other_target_2 = self.g.battlefield('plains', owner=1)
    #     self.g.cast_and_accept(card, target, card.abilities[1])
    #     target.tap()
    #     self.assertIn(target, self.g.gy[1])
    #     print(self.gs.pending_choice)

    def test_land_equilibrium(self):
        """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
        that player instead puts that land onto the battlefield then sacrifices a land of their choice;
        the effect listens to ZoneChangeEvent where zone.to_zone == Zone.BATTLEFIELD"""
        self.g.battlefield('land-equilibrium')
        self.g.mana('RR')
        self.g.mana('BG', owner=1)
        opp_land = self.g.hand('island', owner=1)
        self.gs.pile_mgr.move_card(opp_land, Zone.BATTLEFIELD, cause='cast', emit_zone_event=True)
        self.assertEqual(3, len(self.gs.pending_choice.get_actions()), 'Should have options to sac one of 3 lands')

        self.gs.pending_choice = None
        self.g.mana('RRRRR')
        opp_land = self.g.hand('swamp', owner=1)
        self.gs.pile_mgr.move_card(opp_land, Zone.BATTLEFIELD, cause='cast', emit_zone_event=True)
        self.assertEqual(None, self.gs.pending_choice, 'Should not trigger if you own more lands')

    def test_lesser_werewolf(self):
        """{B}: If LW's power is >= 1, it gets -1/-0 EOT &
        put a -0/-1 counter on target creature blocking or blocked by LW.
        Activate only during the declare blockers step."""
        card = self.g.battlefield('lesser-werewolf')  # 2/4
        aa = card.activated_abilities[0]
        blocker = self.g.battlefield('giant-spider', owner=1)  # 2/4
        self.g.mana('B')

        self.g.next_turn()
        self.assertFalse(aa.can_activate(self.gs))
        self.gs.combat_mgr.create_combat(self.gs, card)
        com = self.gs.combat_mgr.get_combat(card)
        com.blockers.append(blocker)
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS, self.gs)
        self.g.activate_ability(aa, blocker)
        self.assertEqual(1, card.power)
        self.assertEqual(1, blocker.counters.get_count(MINUS_ZERO_ONE))

        self.g.next_turn()
        self.assertEqual(2, card.power)

    def test_library_of_alexandria(self):
        """{T}: Add {C}.
        {T}: Draw a card. Activate only if you have exactly seven cards in hand."""
        card = self.g.battlefield('library-of-alexandria')
        aa_add_mana = card.activated_abilities[0]
        aa_draw_card = card.activated_abilities[1]

        # TODO: this is failing; look at AbilityPipeline.finish()
        #  only a Land that's cast from the hand is subject to bypassing the stack
        #  the current code executes .play()
        #  it's a hot mess, needs re-configure
        self.g.activate_ability(aa_add_mana, 0)
        self.assertEqual(1, self.gs.mana_pools[0].available_mana.get('C'))

        self.g.next_turn()
        self.assertEqual(7, len(self.gs.pile_mgr.hands[0].cards))
        self.assertTrue(aa_draw_card.eff_spec.effect.can_activate(self.gs, card))  # type: ignore
        self.g.activate_ability(aa_draw_card, 0)

        self.g.next_turn()
        self.assertTrue(8, len(self.gs.pile_mgr.hands[0].cards))
        self.assertFalse(aa_draw_card.eff_spec.effect.can_activate(self.gs, card))  # type: ignore


if __name__ == '__main__':
    unittest.main()
