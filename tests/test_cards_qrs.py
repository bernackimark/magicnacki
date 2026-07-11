import unittest

from models.actions.cast import BeginSpellCastAction, CastToTargetAddToStack
from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.special import PayManaForLife, Attach
from models.actions.stack_accept_counter import AcceptAction
from models.actions.tap_untap import Untap
from models.actions.target import AddTargetAction
from models.effects.listeners_damage import ReverseDamageEOT
from models.effects.resolvers_generic import Destroy, RevealHands
from models.effects.resolvers_p_to_z import Sindbad
from models.events_all import StateBasedEvent, DamageProposedEvent
from models.phase_manager import Phase
from tests.setup_helpers import TestGame


class TestCardsWtoZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_rag_man(self):
        """{BBB}, {T}: Opp reveals their hand and discards a creature card at random. Activate only during your turn"""
        card = self.g.battlefield('rag-man')
        aa = card.activated_abilities[0]
        self.g.mana('BBBBBBBBB')
        opp_hand = self.gs.pile_mgr.hands[1].cards
        opp_hand.clear()
        self.g.hand('merfolk-of-the-pearl-trident', owner=1)
        self.g.hand('phantom-monster', owner=1)
        non_creature = self.g.hand('jump', owner=1)
        self.g.next_turn()

        self.g.activate_ability(aa, 1)
        self.assertIn(non_creature, opp_hand)
        self.assertEqual(2, len(opp_hand))
        self.g.next_turn()

        opp_hand.clear()
        self.g.hand('jump', owner=1)
        self.g.activate_ability(aa, 1)
        self.assertEqual(1, len(opp_hand))
        self.g.next_turn()

        opp_hand.clear()
        self.g.activate_ability(aa, 1)  # just make sure nothing blows up if the hand is empty

    def test_rakalite(self):
        """{2}: Prevent the next 1 damage that would be dealt to any target this turn. Bounce Rakalite at end step."""
        card = self.g.battlefield('rakalite')
        aa = card.activated_abilities[0]
        self.g.mana('BBBB')
        self.g.activate_ability(aa, 0)
        self.g.activate_ability(aa, 0)
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('R', owner=1)
        CastToTargetAddToStack(1, self.gs, bolt, 0, bolt.abilities[0]).play()
        AcceptAction(0, self.gs).play()
        self.assertEqual(19, self.gs.score_mgr.life[0])
        self.gs.phase_mgr.set_phase(Phase.END_STEP, self.gs)
        self.assertIn(card, self.gs.pile_mgr.hands[0].cards)

    def test_revelation(self):
        """Players play with their hands revealed"""
        card = self.g.card('revelation')
        RevealHands().resolve(self.gs, card)
        self.gs.event_mgr.register(card.abilities[0].effect, card)
        hand = self.gs.pile_mgr.hands[0].cards
        self.assertTrue(all(c.is_face_up for c in hand))
        self.gs.pile_mgr.draw(0, 1)
        self.assertTrue(all(c.is_face_up for c in hand))

    def test_reverse_damage(self):
        """The next time a source of your choice would deal damage to you this turn, prevent that damage.
        You gain life equal to the damage prevented this way."""
        damage_dealer = self.g.battlefield('grizzly-bears', owner=1)
        PassTheTurn(0, self.gs).play()
        card = self.g.card('reverse-damage')
        self.gs.event_mgr.register(ReverseDamageEOT(damage_dealer=damage_dealer), card)
        self.g.combat(damage_dealer, None)
        self.assertEqual(22, self.gs.score_mgr.life[0])

    def test_rubinia_soulsinger(self):
        """You may choose not to untap Rubinia Soulsinger during your untap step.
        {T}: Gain control of target creature for as long as you control RS and RS remains tapped."""
        card = self.g.battlefield('rubinia-soulsinger')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('air-elemental', owner=1)
        self.g.next_turn()
        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)

        self.g.next_turn()
        self.assertTrue(any(isinstance(a, Untap) for a in self.gs.pending_choice.get_actions()))

        card.untap()
        self.assertEqual(1, target.owner_id)

        self.g.next_turn()
        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)
        self.gs.pile_mgr.destroy(card)
        self.assertEqual(1, target.owner_id)

    def test_safe_haven(self):
        """{2}, {T}: Exile target creature you control.
        At your upkeep, you may sacrifice SH to return each card exiled by SH to the battlefield."""
        card = self.g.battlefield('safe-haven')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('phantom-monster')
        self.g.mana('BBBBBB')
        self.g.activate_ability(aa, target)
        self.assertIn(target, self.gs.pile_mgr.exiles[0])

        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.gs.pending_choice.get_actions()[0].play()
        self.assertIn(target, self.gs.pile_mgr.boards[0])

    def test_sandals_of_abdallah(self):
        """{2}, {T}: Target creature gains islandwalk until EOT. When that creature dies this turn, destroy SOA."""
        card = self.g.battlefield('sandals-of-abdallah')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.mana('UUUUUU')
        self.g.activate_ability(aa, target)
        self.assertIn('Islandwalk', target.keyword_abilities)

        self.gs.pile_mgr.destroy(target)
        self.assertIn(card, self.gs.pile_mgr.graveyards[0])

    def test_scarecrow(self):
        """{6}, {T}: Prevent all damage that would be dealt to you this turn by creatures with flying"""
        card = self.g.battlefield('scarecrow')
        aa = card.activated_abilities[0]
        self.g.mana('UUUUUUUU')
        flier = self.g.battlefield('air-elemental', owner=1)  # 4/4
        non_flier = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        PassTheTurn(0, self.gs).play()
        self.g.activate_ability(aa)
        self.g.combat(flier, None)
        self.g.combat(non_flier, None)
        self.assertEqual(19, self.gs.score_mgr.life[0])

    def test_scarwood_hag(self):
        """{GGGG}, {T}: Target creature gains forestwalk EOT. {T}: Target creature loses forestwalk until EOT."""
        card = self.g.battlefield('scarwood-hag')
        give_aa = card.activated_abilities[0]
        lose_aa = card.activated_abilities[1]
        forest_walker = self.g.battlefield('cat-warriors')
        non_forest_walker = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.mana('GGGGGGG')

        self.g.next_turn()
        self.g.activate_ability(give_aa, non_forest_walker)
        self.assertIn('Forestwalk', non_forest_walker.keyword_abilities)

        self.g.next_turn()
        self.g.activate_ability(lose_aa, forest_walker)
        self.assertNotIn('Forestwalk', forest_walker.keyword_abilities)

    def test_season_of_the_witch(self):
        """At your upkeep, sac SOTW unless you pay 2 life. At end step,
        destroy all untapped creatures that didn't attack this turn, except for creatures that couldn't attack."""
        card = self.g.battlefield('season-of-the-witch')
        wall = self.g.battlefield('wall-of-wood')
        has_haste = self.g.battlefield('nether-shadow')
        regular = self.g.battlefield('savannah-lions')
        gy = self.gs.pile_mgr.graveyards[0]
        self.gs.phase_mgr.set_phase(Phase.END_STEP, self.gs)
        self.assertIn(has_haste, gy)
        self.assertNotIn(wall, gy)
        self.assertNotIn(regular, gy)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.gs.pending_choice.get_actions()[0].play()
        self.assertEqual(18, self.gs.score_mgr.life[0])

        self.gs.phase_mgr.set_phase(Phase.END_STEP, self.gs)
        self.assertIn(regular, gy)
        self.assertNotIn(wall, gy)

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

    def test_storm_seeker(self):
        """SS deals damage to target player equal to the number of cards in that player's hand"""
        card = self.g.hand('storm-seeker')
        self.g.mana('GGGG')
        CastToTargetAddToStack(0, self.gs, card, 1, card.abilities[0]).play()
        AcceptAction(1, self.gs).play()
        self.assertEqual(13, self.gs.score_mgr.life[1])

    def test_syphon_soul(self):
        """SS deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
        card = self.g.hand('syphon-soul')
        self.g.mana('BBB')
        CastToTargetAddToStack(0, self.gs, card, 1, card.abilities[0]).play()
        AcceptAction(1, self.gs).play()
        self.assertEqual([22, 18], self.gs.score_mgr.life)

    def test_tablet_of_epityr(self):
        """Whenever an artifact you control is put into a graveyard from battlefield, you may pay {1} to gain 1 life."""
        card = self.g.battlefield('tablet-of-epityr')
        your_artifact = self.g.battlefield('barls-cage')
        self.g.mana('U')
        self.gs.pile_mgr.destroy(your_artifact)
        self.gs.pending_choice.options[0].play()
        self.assertEqual(21, self.gs.score_mgr.life[0])


if __name__ == '__main__':
    unittest.main()
