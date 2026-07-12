import unittest

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
    #     self.assertIn(target, self.gs.pile_mgr.graveyards[1])
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


if __name__ == '__main__':
    unittest.main()
