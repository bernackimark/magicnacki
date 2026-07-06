import unittest

from models.actions.cast import BeginSpellCastAction
from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.special import PayManaForLife, Attach
from models.actions.target import AddTargetAction
from models.effects.resolvers_generic import Destroy
from models.effects.resolvers_p_to_z import Sindbad
from models.events_all import StateBasedEvent
from models.phase_manager import Phase
from tests.setup_helpers import TestGame


class TestCardsWtoZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_seeker(self):
        """Host can't be blocked except by artifact creatures and/or white creatures"""
        host = self.g.battlefield('giant-spider')
        card = self.g.battlefield('seeker')
        Attach(0, self.gs, card, host).play()
        ineligible_blocker = self.g.battlefield('grizzly-bears', owner=1)
        eligible_blocker = self.g.battlefield('savannah-lions', owner=1)
        self.assertFalse(self.gs.perm_querier.can_block(ineligible_blocker, host))
        self.assertTrue(self.gs.perm_querier.can_block(eligible_blocker, host))

    def test_serendib_djinn(self):
        """At your upkeep, sac a land. If you sac an Island, SD deals 3 damage to you.
        When you control no lands, sac SD."""
        self.g.mana('U')
        sd = self.g.battlefield('serendib-djinn')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.assertIn('Sacrifice Island', [a.__repr__() for a in self.gs.pending_choice.get_actions()])
        self.gs.pending_choice.options[0].play()
        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)
        self.assertEqual(17, self.gs.score_mgr.life[0])
        self.assertIn(sd, self.gs.pile_mgr.graveyards[0])

    def test_serpent_generator(self):
        """{4}, {T}: Create a 1/1 colorless Snake artifact creature token w
        'Whenever this creature deals damage to a player, that player gets a poison counter.'"""
        self.g.mana('UUUUUUU')
        sg = self.g.battlefield('serpent-generator')
        self.g.activate_ability(sg.activated_abilities[0])
        snake = next(c for c in self.gs.pile_mgr.boards[0] if c.props.slug == 'snake')
        self.assertIn(snake, self.gs.pile_mgr.boards[0])
        PassTheTurn(0, self.gs).play()
        PassTheTurn(1, self.gs).play()
        self.gs.combat_mgr.create_combat(self.gs, snake)
        combat = self.gs.combat_mgr.get_combat(snake)
        combat.handle_damage()
        self.assertEqual(1, self.gs.score_mgr.poison_counters[1])
        # TODO: The above fails ... Am I ever looking up 'snake' in slug-effect map??

    def test_sindbad(self):
        """{T}: Draw a card and reveal it. If it isn't a land card, discard it."""
        card = self.g.battlefield('sindbad')
        land_atop_lib = self.g.library('island')
        Sindbad().resolve(self.gs, card, None)
        self.assertIn(land_atop_lib, self.gs.pile_mgr.hands[0].cards)
        non_land_atop_lib = self.g.library('serendib-efreet')
        Sindbad().resolve(self.gs, card, None)
        self.assertIn(non_land_atop_lib, self.gs.pile_mgr.graveyards[0])

    def test_soul_net(self):
        self.assertFalse(any(isinstance(a, PayManaForLife) for a in self.gs.pending_choice.get_actions()))
        self.g.battlefield('soul-net')
        creature = self.g.battlefield('grizzly-bears')
        bolt = self.g.card('lightning-bolt')
        Destroy().resolve(self.gs, bolt, creature)
        self.assertTrue(any(isinstance(a, PayManaForLife) for a in self.gs.pending_choice.get_actions()))

    def test_spectral_cloak(self):
        """Enchanted creature has shroud as long as it's untapped. (It can't be the target of spells or abilities.)"""
        creature = self.g.battlefield('giant-spider')  # 4/4
        self.g.mana('RRR')
        bolt = self.g.hand('lightning-bolt')
        BeginSpellCastAction(0, self.gs, bolt, bolt.abilities[0]).play()
        self.assertIn(creature, [a.target for a in self.gs.pending_choice.get_actions()
                                 if isinstance(a, AddTargetAction)])

        self.gs.pending_choice = None
        spectral_cloak = self.g.battlefield('spectral-cloak')
        Attach(0, self.gs, spectral_cloak, creature).play()
        BeginSpellCastAction(0, self.gs, bolt, bolt.abilities[0]).play()
        self.assertNotIn(creature, [a.target for a in self.gs.pending_choice.get_actions()  # type: ignore
                                    if isinstance(a, AddTargetAction)])

    def test_spirit_link(self):
        """Whenever enchanted creature deals damage, you gain that much life"""
        host = self.g.battlefield('giant-spider')  # 4/4
        spirit_link = self.g.battlefield('spirit-link')
        Attach(0, self.gs, spirit_link, host).play()
        self.gs.apply_damage(host, 4, 1, is_combat=True)
        self.assertEqual(24, self.gs.score_mgr.life[0])

    def test_sprit_shackle(self):
        """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it"""
        host = self.g.battlefield('giant-spider')  # 4/4
        spirit_shackle = self.g.battlefield('spirit-shackle')
        Attach(0, self.gs, spirit_shackle, host).play()
        host.tap()
        self.assertEqual(2, host.toughness)


if __name__ == '__main__':
    unittest.main()
