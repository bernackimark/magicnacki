import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.cost import SacCardCost, CostResult
from models.game_card.counter_tokens import HATCHLING, STUN, PLUS_ONE
from models.events_all import CastResolvedEvent, UpkeepEvent, CombatEndEvent
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestCardsTUV(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_tablet_of_epityr(self):
        """Whenever an artifact you control dies, {1}: Gain 1 life"""
        self.g.battlefield('tablet-of-epityr')
        self.g.mana('U')
        artifact = self.g.battlefield('sol-ring')
        self.gs.pile_mgr.destroy(artifact)
        pay_1_gain_1 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_1_gain_1)
        self.assertEqual(21, self.gs.life[0])

    def test_tawnoss_coffin(self):
        """You may choose not to untap TC during your untap step.
        3T: Exile target creature and all attached auras. Note the number & kind of counters that were on that creature.
        When TC leaves the battlefield or becomes untapped, return that exiled card to the battlefield under its owner's
        control tapped with the original counters & auras on it."""

    def test_telekinesis(self):
        """Tap target creature. Prevent all combat damage that would be dealt by that creature this turn.
        It doesn't untap during its controller's next two untap steps."""
        card = self.g.hand('telekinesis')
        target = self.g.battlefield('grizzly-bears', owner=1)

        self.g.next_turn(True)
        self.g.cast_and_accept(card, target, card.abilities[0])
        self.assertTrue(target.is_tapped)

        self.g.next_turn()
        self.assertTrue(target.is_tapped)

    def test_teleport(self):
        """Cast this spell only during the declare attackers step. Target creature can't be blocked this turn."""
        card = self.g.hand('teleport')
        attacker = self.g.battlefield('grizzly-bears')
        blocker = self.g.battlefield('scryb-sprites', owner=1)
        different_attacker = self.g.battlefield('merfolk-of-the-pearl-trident')

        self.g.next_turn()
        self.g.cast_and_accept(card, attacker, card.abilities[0])
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))
        self.assertTrue(self.gs.perm_querier.can_block(blocker, different_attacker))

    def test_tetravus(self):
        """T enters with 3 +1/+1 counters on it.
        At your upkeep, you may remove X +1/+1 counters from T to create X 1/1
        colorless Tetravite artifact creature tokens, who each fly & "This token can't be enchanted."
        At your upkeep, you may exile any number of tokens created with T to put that many +1/+1 counters on T."""
        card = self.g.hand('tetravus')
        self.g.cast_and_accept(card, None, card.abilities[0])
        self.gs.choice_mgr.clear_current()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        create_2_tokens = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(create_2_tokens)
        self.assertEqual(2, len(self.gs.card_filter.by_slug('tetravite').result()))
        self.assertEqual(1, card.counters.get_count(PLUS_ONE))

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        decline_creating_more_tetravites = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(decline_creating_more_tetravites)
        decline_creating_more_tetravites.play()
        exile_2_tetravites = self.gs.pending_choice.get_actions()[-2]
        self.gs.choice_mgr.choose(exile_2_tetravites)
        self.assertEqual(0, len(self.gs.card_filter.by_slug('tetravite').result()))
        self.assertEqual(3, card.counters.get_count(PLUS_ONE))

    def test_tetsuo_umezawa(self):
        """TU can't be the target of Aura spells. {UBBR}, {T}: Destroy target tapped or blocking creature."""
        card = self.g.card('tetsuo-umezawa')
        aa = card.activated_abilities[0]
        aura = self.g.hand('holy-strength')
        self.g.mana('WWWWUBBR')
        self.assertEqual(0, len(aura.abilities[0].target_spec.get_targets(self.gs, card)))

        self.g.next_turn()
        tapped_target = self.g.battlefield('grizzly-bears')
        tapped_target.tap()
        self.g.activate_ability(aa, tapped_target)
        self.assertIn(tapped_target, self.g.gy[0])

        self.g.next_turn()
        illegal_target = self.g.battlefield('savannah-lions')
        self.assertNotIn(illegal_target, aa.eff_spec.target_spec.get_targets(self.gs, card))

        self.g.next_turn()
        attacker = self.g.battlefield('azure-drake')  # 2/4
        blocker = self.g.battlefield('giant-spider')  # 2/4
        self.g.combat(attacker, blocker)
        self.assertIn(blocker, aa.eff_spec.target_spec.get_targets(self.gs, card))

    def test_the_tabernacle_at_pendrell_vale(self):
        """All creatures have 'At the beginning of your upkeep, pay {1} or destroy this creature'"""
        card = self.g.card('the-tabernacle-at-pendrell-vale')
        self.gs.event_mgr.register(card.abilities[0].effect, card)
        self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.battlefield('phantom-monster')
        self.g.mana('UUUU')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertTrue(len(self.gs.pending_choice.get_actions()))

    def test_the_wretched(self):
        """At combat end, gain control of all creatures blocking TW for as long as you control TW"""
        card = self.g.battlefield('the-wretched')  # 2/5
        blocker = self.g.battlefield('serra-angel', owner=1)

        self.g.next_turn()
        self.gs.combat_mgr.create_combat(card)
        self.gs.combat_mgr.add_blocker(card, blocker)
        self.gs.combat_mgr.handle_damage_step(False)
        self.gs.phase_mgr.set_phase(Phase.COMBAT_END)
        self.assertEqual(0, blocker.owner_id)

        self.gs.pile_mgr.destroy(card)
        self.assertEqual(1, blocker.owner_id)

    def test_time_vault(self):
        """This artifact enters tapped. This artifact doesn't untap during your untap step.
        If you would begin your turn while this artifact is tapped, you may: skip that turn & untap this artifact.
        {T}: Take an extra turn after this one."""
        self.g.mana('UUUUUUUUUU')
        card = self.g.battlefield('time-vault')
        self.g.resolve_spell(card, card)
        self.assertTrue(card.is_tapped)

        self.g.next_turn()
        skip_turn_and_untap_tv = self.gs.pending_choice.options[0]
        skip_turn_and_untap_tv.play()
        self.assertEqual(1, self.gs.player_turn_idx)

        self.g.next_turn(True)
        self.g.activate_ability(card.activated_abilities[0])
        self.gs.phase_mgr.set_phase(Phase.PASS_THE_TURN)
        self.assertEqual(0, self.gs.player_turn_idx)
        self.assertTrue(card.is_tapped)

    def test_timetwister(self):
        """Each player shuffles their hand & graveyard into their library, then draws seven cards.
        (Then put Timetwister into its owner's graveyard.)"""
        # this works 1/2 the time
        self.g.mana('UUUUU')
        self.g.gy[0].clear()
        self.g.graveyard('scryb-sprites')
        self.g.graveyard('serra-angel')
        hand_snapshot = self.gs.pile_mgr.hands[0][:]
        self.g.hand('island')
        self.g.hand('island')
        card = self.g.hand('timetwister')
        # self.g.cast_and_accept(card, None, card.abilities[0])
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertTrue(7, len(self.gs.pile_mgr.hands[0]))
        self.assertIn(card, self.g.gy[0])
        self.assertNotEqual(hand_snapshot, self.gs.pile_mgr.hands[0])

    def test_transmute_artifact_1(self):
        """Sac an artifact: tutor an artifact. If that card's MV <= the sacrificed artifact's MV,
        put it onto the battlefield. If >, you may pay {X}, as the difference.
        If you do, put it onto the battlefield.
        If you don't, put it into its owner's graveyard.
        Shuffle."""
        self.gs.pile_mgr.libraries[0].clear()
        self.g.mana('UUUU')
        a2 = self.g.library('colossus-of-sardia')  # MV = 9
        sac = self.g.battlefield('chaos-orb')  # MV = 2
        card = self.g.hand('transmute-artifact')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0],
                                   selected_extra_costs=[SacCardCost(selected_card=sac)],
                                   cost_result=CostResult([sac]))
        pipeline.advance()
        pipeline.resolve_ability()
        select_a2 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(select_a2)
        self.assertIn(a2, self.g.gy[0])

    def test_transmute_artifact_2(self):
        """Sac an artifact: tutor an artifact. If that card's MV <= the sacrificed artifact's MV,
        put it onto the battlefield. If >, you may pay {X}, as the difference.
        If you do, put it onto the battlefield.
        If you don't, put it into its owner's graveyard.
        Shuffle."""
        self.gs.pile_mgr.libraries[0].clear()
        self.g.mana('UUUU')
        a1 = self.g.library('sol-ring')  # MV = 1
        sac = self.g.battlefield('chaos-orb')  # MV = 2
        card = self.g.hand('transmute-artifact')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0],
                                   selected_extra_costs=[SacCardCost(selected_card=sac)],
                                   cost_result=CostResult([sac]))
        pipeline.advance()
        pipeline.resolve_ability()
        select_a1 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(select_a1)
        self.assertIn(a1, self.gs.boards[0])

    def test_transmute_artifact_3(self):
        """Sac an artifact: tutor an artifact. If that card's MV <= the sacrificed artifact's MV,
        put it onto the battlefield. If >, you may pay {X}, as the difference.
        If you do, put it onto the battlefield.
        If you don't, put it into its owner's graveyard.
        Shuffle."""
        self.gs.pile_mgr.libraries[0].clear()
        self.g.mana('UUUU')
        a1 = self.g.library('basalt-monolith')  # MV = 3
        sac = self.g.battlefield('chaos-orb')  # MV = 2
        card = self.g.hand('transmute-artifact')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0],
                                   selected_extra_costs=[SacCardCost(selected_card=sac)],
                                   cost_result=CostResult([sac]))
        pipeline.advance()
        pipeline.resolve_ability()
        select_a1 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(select_a1)
        pay_1_to_put_on_battlefield = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_1_to_put_on_battlefield)
        self.assertIn(a1, self.gs.boards[0])
        self.assertIsNone(self.gs.pending_choice)

    def test_triassic_egg(self):
        """... Sac TE: Choose one. Activate only if there are two or more hatchling counters on this artifact.
        * You may put a creature card from your hand onto the battlefield.
        * Return target creature card from your graveyard to the battlefield."""
        self.gs.hands[0].clear()
        card = self.g.battlefield('triassic-egg')
        card.counters.add_counter(HATCHLING, 2)
        self.assertFalse(any(a.source is card for a in self.gs.add_activated_abilities_from_board()))

        card_in_hand = self.g.hand('grizzly-bears')
        self.g.graveyard('merfolk-of-the-pearl-trident')
        self.assertEqual(2, len(self.gs.add_activated_abilities_from_board()))

        hand_to_battlefield = self.gs.add_activated_abilities_from_board()[0]
        self.g.activate_ability(hand_to_battlefield, card_in_hand)
        self.assertIn(card, self.g.gy[0])
        self.assertIn(card_in_hand, self.gs.boards[0])

    def test_unstable_mutation(self):
        """Host gets +3/+3. At host's upkeep, put a -1/-1 counter on host."""
        card = self.g.battlefield('unstable-mutation')
        host = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        self.g.attach(card, host)
        card.abilities[1].effect.resolve(self.gs, card, host)
        self.assertEqual(4, host.power)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(3, host.power)

    def test_urzas_miter(self):
        """Whenever an artifact you control is put into a graveyard from the battlefield,
        if it wasn't sacrificed, you may pay {3} to draw a card"""
        card = self.g.battlefield('urzas-miter')
        self.gs.event_mgr.register(card.abilities[0].effect, card)
        artifact = self.g.battlefield('sol-ring')
        self.gs.pile_mgr.destroy(artifact)
        self.assertTrue(any(a.description.startswith('Pay ') for a in self.gs.pending_choice.get_actions()))

    def test_venarian_gold(self):
        """When VG enters, tap host & put X stun counters on it."""
        card = self.g.hand('venarian-gold')
        self.g.mana('UUUUUUUU')
        host = self.g.battlefield('monss-goblin-raiders', owner=1)
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=1)
        card.extras['x'] = 1
        pipeline.advance()
        pipeline.targets.append(host)
        pipeline.finish()
        pipeline.resolve_ability()
        self.assertTrue(host.is_tapped)
        self.assertEqual(1, host.counters.get_count(STUN))

        self.g.next_turn(True)
        self.assertTrue(host.is_tapped)

        self.g.next_turn()
        self.assertFalse(host.is_tapped)

    def test_venom_vs_non_wall(self):
        """Whenever host blocks / becomes blocked by a non-Wall creature, destroy that creature at end of combat"""
        card = self.g.hand('venom')
        host = self.g.battlefield('grizzly-bears')
        self.g.cast_and_accept(card, host, card.abilities[0])
        blocker = self.g.battlefield('shivan-dragon', owner=1)
        self.g.next_turn()

        self.gs.combat_mgr.create_combat(host)
        com = self.gs.combat_mgr.get_combat(host)
        com.add_blocker(blocker)
        self.gs.phase_mgr.set_phase(Phase.PRE_COMBAT_DAMAGE)
        self.gs.event_mgr.emit(CombatEndEvent(0))
        self.assertIn(blocker, self.g.gy[1])

    def test_venom_vs_wall(self):
        """Whenever host blocks / becomes blocked by a non-Wall creature, destroy that creature at end of combat"""
        card = self.g.hand('venom')
        host = self.g.battlefield('grizzly-bears')
        self.g.cast_and_accept(card, host, card.abilities[0])
        blocker = self.g.battlefield('wall-of-brambles', owner=1)
        self.g.next_turn()

        self.gs.combat_mgr.create_combat(host)
        com = self.gs.combat_mgr.get_combat(host)
        com.blockers.append(blocker)
        self.gs.phase_mgr.set_phase(Phase.PRE_COMBAT_DAMAGE)
        self.gs.event_mgr.emit(CombatEndEvent(0))
        self.assertNotIn(blocker, self.g.gy[1])

    def test_verduran_enchantress(self):
        """Whenever you cast an enchantment spell, you may draw a card"""
        self.g.battlefield('verduran-enchantress')
        self.g.mana('UUUUU')
        enchantment = self.g.card('undertow')
        cast_event = CastResolvedEvent(enchantment, 0)
        self.gs.event_mgr.emit(cast_event)
        self.assertTrue(len([a for a in self.gs.pending_choice.options if a.description == 'Draw a card']))


if __name__ == '__main__':
    unittest.main()
