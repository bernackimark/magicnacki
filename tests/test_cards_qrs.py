import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastPermanentAction
from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.special import PayManaForLife, Attach
from models.actions.tap_untap import Untap
from models.cost import SacCardCost
from models.counter_tokens import PLUS_ONE
from models.effects.resolvers_generic import RevealHands
from models.effects.resolvers_p_to_z import Sindbad
from models.events_all import StateBasedEvent, EndStepEvent, UpkeepEvent
from models.systems.phase import Phase
from models.zone import Zone
from tests.setup_helpers import TestGame


class TestCardsQRS(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_rag_man(self):
        """{BBB}, {T}: Opp reveals their hand and discards a creature card at random. Activate only during your turn"""
        card = self.g.battlefield('rag-man')
        aa = card.activated_abilities[0]
        self.g.mana('BBBBBBBBB')
        opp_hand = self.gs.pile_mgr.hands[1]
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
        bolt.abilities[0].effect.resolve(self.gs, bolt, 0)
        self.assertEqual(19, self.gs.life[0])
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.assertIn(card, self.gs.pile_mgr.hands[0])

    def test_reset(self):
        """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control."""
        card = self.g.hand('reset')
        island_1 = self.g.battlefield('island')
        self.g.battlefield('island')
        self.assertNotIn(card, [a.source for a in self.gs.available_actions_from_hand()
                                if isinstance(a, AbilityPipeline)])

        PassTheTurn(0, self.gs).play()
        island_1.tap()
        self.assertTrue(island_1.is_tapped)
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        card.abilities[0].effect.resolve(self.gs, card)
        self.assertFalse(island_1.is_tapped)

    def test_revelation(self):
        """Players play with their hands revealed"""
        card = self.g.card('revelation')
        RevealHands().resolve(self.gs, card)
        self.gs.event_mgr.register(card.abilities[0].effect, card)
        hand = self.gs.pile_mgr.hands[0]
        self.assertTrue(all(c.is_face_up for c in hand))
        self.gs.pile_mgr.draw(0, 1)
        self.assertTrue(all(c.is_face_up for c in hand))

    def test_reverse_damage(self):
        """The next time a source of your choice would deal damage to you this turn, prevent that damage.
        You gain life equal to the damage prevented this way."""
        damage_dealer = self.g.battlefield('grizzly-bears', owner=1)
        PassTheTurn(0, self.gs).play()
        card = self.g.card('reverse-damage')
        self.g.cast_and_accept(card, damage_dealer, card.abilities[0])
        self.g.combat(damage_dealer, None)
        self.assertEqual(22, self.gs.life[0])

    def test_rock_hydra(self):
        """XRR RH enters with X +1/+1 counters.
        For each 1 damage that would be dealt to this creature, if it has a +1/+1 counter on it, remove a +1/+1 counter
        & prevent that 1 damage.
        {R}: Prevent the next 1 damage that would be dealt to RH EOT.
        {RRR}: Add a +1/+1 counter on this creature. Activate only during your upkeep."""
        card = self.g.hand('rock-hydra')
        self.g.mana('RRRRRR')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[3])
        pipeline.advance()
        possible_actions = self.gs.pending_choice.get_actions()
        self.assertEqual({1, 2, 3, 4}, {a.x for a in possible_actions})

        pipeline.x_value = 4
        pipeline.resolve_ability()  # RH = 4/4
        self.assertEqual(4, card.counters.get_count(PLUS_ONE))

        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.cast_and_accept(bolt, card, bolt.abilities[0], 1)
        self.assertEqual(0, card.damage_received_this_turn)
        self.assertEqual(1, card.counters.get_count(PLUS_ONE))  # RH = 1/1
        self.assertEqual(1, card.power)

        self.g.mana('RRR')
        aa_add_ctr = card.activated_abilities[1]
        self.g.activate_ability(aa_add_ctr, card)
        self.assertEqual(2, card.counters.get_count(PLUS_ONE))

        random_source = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        self.g.next_turn(True)
        self.g.mana('R')
        aa_prevent = card.activated_abilities[0]
        self.g.activate_ability(aa_prevent, card)
        self.g.combat(random_source, card)
        self.assertEqual(0, card.damage_received_this_turn)

        # TODO: the auto damage reduction is competing w the activated ability that is creating a diff damage reducer
        #  need to lookup the rule on this
        # self.assertEqual(2, card.power)

    def test_rocket_launcher(self):
        """{2}: RL deals 1 damage to any target. Destroy this artifact at end step.
        Activate only if you've controlled this artifact continuously since the beginning of your most recent turn."""
        card = self.g.battlefield('rocket-launcher')
        aa = card.activated_abilities[0]
        self.g.mana('RR')
        can_activate_effect = aa.eff_spec.effect.can_activate(self.gs, card)
        self.assertFalse(can_activate_effect)

        self.g.next_turn()
        self.g.activate_ability(aa, 1)
        self.assertEqual(19, self.gs.life[1])

        self.gs.event_mgr.emit(EndStepEvent(0))
        self.assertIn(card, self.g.gy[0])

    def test_rohgahh_of_kher_keep(self):
        """At your upkeep, you may pay {RRR} or: tap ROKK, all Kobolds of Kher Keep & opponent gains control of them.
        Creatures you control named Kobolds of Kher Keep get +2/+2."""
        card = self.g.battlefield('rohgahh-of-kher-keep')
        kobold = self.g.battlefield('kobolds-of-kher-keep')  # 0/1
        self.assertEqual(2, kobold.power)

        self.g.mana('RRR')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        the_bad_option = self.gs.pending_choice.get_actions()[1]
        the_bad_option.play()
        self.assertTrue(card.is_tapped)
        self.assertTrue(kobold.is_tapped)
        self.assertEqual(1, card.owner_id)
        self.assertEqual(1, kobold.owner_id)

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

    def test_sacrifice(self):
        """Sac a creature to add {B} = to sac'd card MV"""
        mv_5_card = self.g.battlefield('serra-angel')
        card = self.g.hand('sacrifice')
        self.g.mana('B')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        sac = SacCardCost(selected_card=mv_5_card)
        pipeline.cost_result = sac.pay(self.gs, card)
        pipeline.finish()
        pipeline.resolve_ability()

        self.assertEqual(5, self.gs.mana_pools[0].available_mana.get('B'))
        self.assertIn(mv_5_card, self.g.gy[0])

    def test_safe_haven(self):
        """{2}, {T}: Exile target creature you control.
        At your upkeep, you may sacrifice SH to return each card exiled by SH to the battlefield."""
        card = self.g.battlefield('safe-haven')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('phantom-monster')
        self.g.mana('BBBBBB')
        self.g.activate_ability(aa, target)
        self.assertIn(target, self.gs.pile_mgr.exiles[0])

        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
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
        self.assertIn(card, self.g.gy[0])

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
        self.assertEqual(19, self.gs.life[0])

    def test_scarwood_bandits(self):
        """2GT: Unless opponent pays {2}, gain control of target artifact for as long as SB stays on the battlefield ...
        I don't have a great way of adding an opponent's choice at the exact right time, I'm just creating a Listener
        to add a choice to the stack for the opponent"""
        card = self.g.battlefield('scarwood-bandits')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('sol-ring', owner=1)
        self.g.mana('GGG')
        self.g.mana('WW', owner=1)

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, targets=[target])
        pipeline.advance()
        prevent_steal_action = self.gs.pending_choice.get_actions()[0]
        prevent_steal_action.play()
        self.assertEqual(1, target.owner_id)

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, targets=[target])
        pipeline.advance()
        allow_steal_action = self.gs.pending_choice.get_actions()[-1]
        allow_steal_action.play()
        pipeline.resolve_ability()
        self.assertEqual(0, target.owner_id)

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
        self.g.battlefield('season-of-the-witch')
        wall = self.g.battlefield('wall-of-wood')
        has_haste = self.g.battlefield('nether-shadow')
        regular = self.g.battlefield('savannah-lions')
        gy = self.g.gy[0]
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.assertIn(has_haste, gy)
        self.assertNotIn(wall, gy)
        self.assertNotIn(regular, gy)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.gs.pending_choice.get_actions()[0].play()
        self.assertEqual(18, self.gs.life[0])

        self.gs.phase_mgr.set_phase(Phase.END_STEP)
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
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertIn('Sacrifice Island', [a.__repr__() for a in self.gs.pending_choice.get_actions()])
        self.gs.pending_choice.options[0].play()
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertEqual(17, self.gs.life[0])
        self.assertIn(sd, self.g.gy[0])

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
        self.gs.combat_mgr.create_combat(snake)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(1, self.gs.score_mgr.poison_counters[1])
        # TODO: The above fails ... Am I ever looking up 'snake' in slug-effect map??

    def test_shimian_night_stalker(self):
        """All damage that would be dealt to you this turn by target attacking creature is dealt to SNS instead"""
        card = self.g.battlefield('shimian-night-stalker')
        aa = card.activated_abilities[0]
        self.g.mana('BBB')
        attacker = self.g.battlefield('grizzly-bears', owner=1)

        self.g.next_turn(True)
        self.assertNotIn(attacker, aa.eff_spec.target_spec.get_targets(self.gs, card))
        self.gs.combat_mgr.create_combat(attacker)
        self.assertIn(attacker, aa.eff_spec.target_spec.get_targets(self.gs, card))

        ap = AbilityPipeline(0, self.gs, card, card.abilities[0])
        ap.advance()
        ap.targets.append(attacker)
        ap.resolve_ability()
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(2, card.damage_received_this_turn)
        self.assertEqual(20, self.gs.life[0])

    def test_sindbad(self):
        """{T}: Draw a card and reveal it. If it isn't a land card, discard it."""
        card = self.g.battlefield('sindbad')
        land_atop_lib = self.g.library('island')
        Sindbad().resolve(self.gs, card, None)
        self.assertIn(land_atop_lib, self.gs.pile_mgr.hands[0])
        non_land_atop_lib = self.g.library('serendib-efreet')
        Sindbad().resolve(self.gs, card, None)
        self.assertIn(non_land_atop_lib, self.g.gy[0])

    def test_sirens_call(self):
        """All non-Wall creatures the active player has controlled continuously since BOT must attack.
        Destroy at end step if it didn't attack this turn.
        Cast only during an opponent's turn, before attackers are declared."""
        card = self.g.hand('sirens-call')
        attacker = self.g.battlefield('savannah-lions', owner=1)
        non_attacker = self.g.battlefield('tundra-wolves', owner=1)
        wall = self.g.battlefield('wall-of-brambles', owner=1)
        self.assertFalse(any(a for a in self.gs.available_actions_from_hand()
                             if isinstance(a, AbilityPipeline) and a.source is card))

        self.g.next_turn(True)
        has_sickness = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        self.g.cast_and_accept(card, None, card.abilities[0])
        self.g.combat(attacker, None)
        self.gs.event_mgr.emit(EndStepEvent(1))
        self.assertNotIn(attacker, self.g.gy[1])
        self.assertIn(non_attacker, self.g.gy[1])
        self.assertNotIn(wall, self.g.gy[1])
        self.assertNotIn(has_sickness, self.g.gy[1])

    def test_soul_net(self):
        self.g.battlefield('soul-net')
        creature = self.g.battlefield('grizzly-bears')
        bolt = self.g.card('lightning-bolt')
        self.g.cast_and_accept(bolt, creature, bolt.abilities[0])
        self.assertTrue(any(isinstance(a, PayManaForLife) for a in self.gs.pending_choice.get_actions()))

    def test_spectral_cloak(self):
        """Enchanted creature has shroud as long as it's untapped. (It can't be the target of spells or abilities.)"""
        creature = self.g.battlefield('giant-spider')  # 4/4
        self.g.mana('RRR')
        bolt = self.g.hand('lightning-bolt')
        pipeline = AbilityPipeline(0, self.gs, bolt, bolt.abilities[0])
        pipeline.advance()
        self.assertIn(creature, [a.target for a in self.gs.pending_choice.get_actions()])

        spectral_cloak = self.g.battlefield('spectral-cloak')
        Attach(0, self.gs, spectral_cloak, creature).play()
        pipeline = AbilityPipeline(0, self.gs, bolt, bolt.abilities[0])
        pipeline.advance()
        self.assertNotIn(creature, self.gs.pending_choice.targets)

    def test_spell_blast(self):
        """Counter target spell with mana value X. (For example, if that spell's mana cost is {3UU}, X is 5.)"""
        self.gs.hands[0].clear()
        card = self.g.hand('spell-blast')  # casting_cost = XU
        self.g.mana('UU')
        large_card = self.g.hand('shivan-dragon', owner=1)
        small_card = self.g.hand('monss-goblin-raiders', owner=1)

        self.g.next_turn(True)
        self.gs.action_stack.push(CastPermanentAction(1, self.gs, large_card), self.gs)
        self.assertEqual(0, self.gs.action_on_idx)
        self.assertFalse(any(a.source is card for a in self.gs.available_actions_from_hand()))
        self.gs.action_stack.clear_()

        self.g.next_turn()
        self.gs.action_stack.push(CastPermanentAction(1, self.gs, small_card), self.gs)
        self.assertEqual(0, self.gs.action_on_idx)
        self.assertTrue(any(a.source is card for a in self.gs.available_actions_from_hand()))

    def test_spirit_link(self):
        """Whenever enchanted creature deals damage, you gain that much life"""
        host = self.g.battlefield('giant-spider')  # 4/4
        spirit_link = self.g.battlefield('spirit-link')
        Attach(0, self.gs, spirit_link, host).play()
        self.gs.apply_damage(host, 4, 1, is_combat=True)
        self.assertEqual(24, self.gs.life[0])

    def test_sprit_shackle(self):
        """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it"""
        host = self.g.battlefield('giant-spider')  # 4/4
        spirit_shackle = self.g.battlefield('spirit-shackle')
        Attach(0, self.gs, spirit_shackle, host).play()
        host.tap()
        self.assertEqual(2, host.toughness)

    def test_stangg(self):
        """When S enters, create Stangg Twin, a legendary 3/4 red and green Human Warrior creature token.
        Exile that token when S leaves the battlefield. Sacrifice S when that token leaves the battlefield."""
        card = self.g.battlefield('stangg')
        self.g.resolve_spell(card)
        stangg_twin = next(c for c in self.gs.card_filter.on_player_board(0).result() if c is not card)
        self.assertIn(stangg_twin, self.gs.pile_mgr.boards[0])
        self.gs.pile_mgr.destroy(card)
        self.assertNotIn(stangg_twin, self.gs.pile_mgr.boards[0])

        card = self.g.battlefield('stangg')
        self.g.resolve_spell(card)
        stangg_twin = next(c for c in self.gs.card_filter.on_player_board(0).result() if c is not card)
        self.gs.pile_mgr.destroy(stangg_twin)
        self.assertNotIn(card, self.gs.pile_mgr.boards[0])

    def test_stasis(self):
        """Players skip their untap steps. At your upkeep, pay {U} or sac Stasis."""
        card = self.g.battlefield('stasis')
        self.gs.event_mgr.register(card.abilities[0].effect, card)
        self.gs.event_mgr.register(card.abilities[1].effect, card)
        self.g.mana('U')
        tapped_card = self.g.battlefield('nether-void')
        tapped_card.tap()
        self.g.battlefield('grizzly-bears')

        self.g.next_turn()
        self.assertTrue(tapped_card.is_tapped)

        self.gs.event_mgr.emit(UpkeepEvent(0))
        sac_stasis_action = self.gs.pending_choice.options[1]
        sac_stasis_action.play()

        self.g.next_turn()
        self.assertFalse(tapped_card.is_tapped)

    def test_stone_giant(self):
        """{T}: Target creature you control with toughness < SG's power gains flying EOT. Destroy target at end step."""
        card = self.g.card('stone-giant')  # 3/4
        aa = card.activated_abilities[0]
        legal_target = self.g.battlefield('grizzly-bears')  # 2/2
        illegal_target = self.g.battlefield('sengir-vampire')  # 4/4
        self.assertIn(legal_target, aa.eff_spec.target_spec.get_targets(self.gs, card))
        self.assertNotIn(illegal_target, aa.eff_spec.target_spec.get_targets(self.gs, card))

        self.g.activate_ability(aa, legal_target)
        self.assertIn('Flying', legal_target.keyword_abilities)
        self.gs.event_mgr.emit(EndStepEvent(0))
        self.assertEqual(legal_target.zone, Zone.GRAVEYARD)

    def test_storm_seeker(self):
        """SS deals damage to target player equal to the number of cards in that player's hand"""
        card = self.g.hand('storm-seeker')
        card.abilities[0].effect.resolve(self.gs, card, 1)
        self.assertEqual(13, self.gs.life[1])

    def test_sylvan_library_2(self):
        """At your draw step, you may draw two additional cards.
        For each card beyond the first, pay 4 life or put the card on top of your library.
        This test draws 2 cards"""
        self.gs.hands[0].clear()
        self.gs.pile_mgr.libraries[0].clear()
        self.g.battlefield('sylvan-library')
        self.g.library('alabaster-potion')
        self.g.library('blue-elemental-blast')
        c3 = self.g.library('colossus-of-sardia')

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        yes_draw_extra_cards = self.gs.pending_choice.get_actions()[0]
        yes_draw_extra_cards.play()  # there are now a total of three cards drawn
        self.assertEqual(3, len(self.gs.hands[0]))

        draw_c2 = self.gs.pending_choice.get_actions()[1]
        draw_c2.play()  # select blue-elemental-blast as the normal card drawn

        select_c1 = self.gs.pending_choice.get_actions()[1]
        select_c1.play()  # select alabaster-potion as the card you want to engage with
        add_to_hand_for_4_life = self.gs.pending_choice.get_actions()[0]
        add_to_hand_for_4_life.play()  # keep alabaster-potion in hand, decrement 4 life
        self.assertEqual(16, self.gs.life[0])

        select_c3 = self.gs.pending_choice.get_actions()[0]
        select_c3.play()  # select colossus-of-sardia as the card you want to engage with (it's the only remaining card)
        place_atop_library = self.gs.pending_choice.get_actions()[-1]
        place_atop_library.play()  # place colossus-of-sardia atop the library
        self.assertEqual(c3, self.gs.pile_mgr.libraries[0][0])

        self.assertIsNone(self.gs.pending_choice)

    def test_syphon_soul(self):
        """SS deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
        card = self.g.hand('syphon-soul')
        card.abilities[0].effect.resolve(self.gs, card, 1)
        # self.g.mana('BBB')
        # self.g.cast_and_accept(card, 1, card.abilities[0])
        self.assertEqual([22, 18], self.gs.life)

    def test_tablet_of_epityr(self):
        """Whenever an artifact you control is put into a graveyard from battlefield, you may pay {1} to gain 1 life."""
        self.g.battlefield('tablet-of-epityr')
        your_artifact = self.g.battlefield('barls-cage')
        self.g.mana('U')
        self.gs.pile_mgr.destroy(your_artifact)
        self.gs.pending_choice.options[0].play()
        self.assertEqual(21, self.gs.life[0])


if __name__ == '__main__':
    unittest.main()
