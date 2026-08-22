import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import AbilityAction, SelectXAction2
from models.game_card.counter_tokens import HUNGER
from models.events_all import UpkeepEvent
from models.systems.phase import Phase
from models.constants import Zone
from tests.setup_helpers import TestGame


class TestCardsDEF(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_dance_of_many(self):
        """... When DOM ETB, create a token copy of target nontoken creature -- copies its original props w/o mods ...
        When DOM LTB, exile the token. When the token LTB, sac DOM"""
        card = self.g.hand('dance-of-many')
        target = self.g.battlefield('grizzly-bears')  # 2/2
        aura = self.g.hand('holy-strength')  # +1/+2
        self.g.cast_and_accept(aura, target, aura.abilities[0])
        self.assertEqual(3, target.power)

        self.g.cast_and_accept(card, target, card.abilities[1])
        the_copy = next(c for c in self.gs.boards[0] if not c.is_land and c not in (card, target, aura))
        self.assertEqual(Zone.BATTLEFIELD, the_copy.zone)
        self.assertEqual(2, the_copy.power)

        self.g.next_turn()
        self.assertTrue(self.gs.perm_querier.can_attack(the_copy))

        self.gs.pile_mgr.sacrifice(card)
        self.assertNotIn(the_copy, self.gs.boards[0])

    def test_demonic_torment(self):
        """Host can't attack. Prevent all combat damage that would be dealt by host."""
        card = self.g.hand('demonic-torment')
        host = self.g.battlefield('grizzly-bears')
        attacker = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        self.g.cast_and_accept(card, host, card.abilities[0])

        self.g.next_turn()
        self.assertFalse(self.gs.perm_querier.can_attack(host))

        self.g.next_turn(True)
        self.g.combat(attacker, host)
        self.assertIn(host, self.gs.pile_mgr.boards[0])

    def test_disharmony(self):
        """Cast this spell only during combat before blockers are declared.
        Untap target attacking creature and remove it from combat. Gain control of that creature EOT."""
        card = self.g.hand('disharmony')
        attacker = self.g.battlefield('grizzly-bears', owner=1)

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        self.g.cast_and_accept(card, attacker, card.abilities[0])
        self.assertEqual(0, attacker.owner_id)

        self.g.next_turn(True)
        self.assertEqual(1, attacker.owner_id)

    def test_disintegrate(self):
        """D deals X damage to any target.
        If it's a creature, no regen allow EOT, & if it would die EOT, exile instead."""
        card = self.g.hand('disintegrate')
        self.g.mana('RRRRR')
        target = self.g.battlefield('will-o-the-wisp', owner=1)

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[target])
        x_action = SelectXAction2(0, self.gs, pipeline, 4)
        x_action.play()
        pipeline.advance()
        self.assertFalse(self.gs.pending_choice)
        pipeline.resolve_ability()
        self.assertIn(target, self.gs.exiles[1])

    def test_drafnas_restoration(self):
        """Put any number of target artifact cards from target player's graveyard atop of their library in ANY ORDER"""
        card = self.g.hand('drafnas-restoration')
        aladdins_lamp = self.g.graveyard('aladdins-lamp')
        self.g.graveyard('basalt-monolith')
        colossus = self.g.graveyard('colossus-of-sardia')
        self.g.graveyard('dwarven-warriors')  # not an artifact
        self.g.cast_and_accept(card, 0, card.abilities[0])
        self.assertEqual(4, len(self.gs.pending_choice.get_actions()))  # 3 artifacts & finish action
        select_aladdins_lamp = next(a for a in self.gs.pending_choice.get_actions()
                                    if a.description.startswith('Move ALADDIN'))
        self.gs.choice_mgr.choose(select_aladdins_lamp)
        select_colossus = next(a for a in self.gs.pending_choice.get_actions()
                               if a.description.startswith('Move COLOSSUS'))
        self.gs.choice_mgr.choose(select_colossus)
        finish_action = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(finish_action)
        self.assertEqual([colossus, aladdins_lamp], self.gs.pile_mgr.libraries[0][:2])
        self.assertFalse(self.gs.pending_choice)

    def test_dwarven_warriors(self):
        """{T}: Target creature with power 2 or less can't be blocked this turn"""
        card = self.g.battlefield('dwarven-warriors')
        aa = card.activated_abilities[0]
        attacker = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        blocker = self.g.battlefield('grizzly-bears', owner=1)

        self.g.next_turn()
        self.g.activate_ability(aa, attacker)
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

    def test_enchanted_being(self):
        """"Prevent all combat damage that would be dealt to this creature by enchanted creatures"""
        card = self.g.battlefield('enchanted-being')  # 2/2
        attacker = self.g.battlefield('craw-wurm', owner=1)  # 6/4
        aura = self.g.hand('holy-strength', owner=1)
        self.g.cast_and_accept(aura, attacker, card.abilities[0], owner=1)
        self.assertTrue(attacker is aura.host)

        self.g.next_turn()
        self.g.combat(attacker, card)
        self.assertIn(card, self.gs.pile_mgr.boards[0])

    def test_enchantment_alteration(self):
        """Attach target Aura attached to a creature or land to another permanent of that type"""
        card = self.g.hand('enchantment-alteration')
        aura = self.g.hand('holy-strength')
        original_host = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.cast_and_accept(aura, original_host, aura.abilities[0])

        illegal_host = self.g.battlefield('island')
        self.assertNotIn(illegal_host, card.abilities[0].target_spec.get_targets(self.gs, card))

        legal_host = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.cast_and_accept(card, aura, card.abilities[0])
        self.assertEqual(1, len(self.gs.pending_choice.get_actions()))

    def test_eureka(self):
        """Both players may take any permanent in their hand and put it directly into play.
        Players take turns playing one card from their hand until neither wants to play more permanents.
        No other spells/effects may be used while E is in effect. If a spell has an X in casting cost, X=0."""
        [h.clear() for h in self.gs.hands]
        card = self.g.hand('eureka')
        p0c1 = self.g.hand('merfolk-of-the-pearl-trident')
        self.g.hand('aladdins-lamp')
        self.g.hand('winter-orb', owner=1)
        p1c2 = self.g.hand('grizzly-bears', owner=1)
        self.g.cast_and_accept(card, None, card.abilities[0])

        merfolk_to_board = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(merfolk_to_board)
        self.assertIn(p0c1, self.gs.boards[0])

        grizzly_bears_to_board = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(grizzly_bears_to_board)
        self.assertIn(p1c2, self.gs.boards[1])

        p0_finish_playing = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(p0_finish_playing)
        p1_finish_playing = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(p1_finish_playing)
        self.assertFalse(self.gs.pending_choice)

    def test_eye_for_an_eye(self):
        """The next time a source of your choice would deal damage to you this turn,
        instead that source deals that much damage to you and EYAE deals that much damage to that source's controller"""
        card = self.g.hand('eye-for-an-eye')
        attacker = self.g.battlefield('grizzly-bears', owner=1)  # 2/2

        self.g.next_turn(True)
        self.g.cast_and_accept(card, attacker, card.abilities[0])
        self.g.combat(attacker, None)
        self.assertEqual([18, 18], self.gs.life)

    def test_fasting(self):
        """At your upkeep, put a hunger counter on F. Destroy F if it has >=5 hunger counters.
        If you would begin your draw step, you may skip that step instead to gain 2 life.
        When you draw a card, destroy F."""
        card = self.g.battlefield('fasting')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertEqual(1, card.counters.get_count(HUNGER))
        skip_draw_gain_life = self.gs.pending_choice.get_actions()[0]
        skip_draw_gain_life.play()

        self.g.next_turn()
        self.assertEqual(7, len(self.gs.pile_mgr.hands[0]))
        self.assertEqual(22, self.gs.life[0])

        self.gs.event_mgr.emit(UpkeepEvent(0))
        do_not_skip_draw = self.gs.pending_choice.get_actions()[1]
        do_not_skip_draw.play()
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        self.assertEqual(8, len(self.gs.pile_mgr.hands[0]))
        self.assertIn(card, self.g.gy[0])

    def test_fellwar_stone_1(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('plains', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)  # type: ignore
        self.assertEqual(1, len(self.gs.pending_choice.get_actions()))

    def test_fellwar_stone_2(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('birds-of-paradise', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)  # type: ignore
        self.assertEqual(5, len(self.gs.pending_choice.get_actions()))

    def test_festival(self):
        """Cast this spell only during an opponent's upkeep. Creatures can't attack this turn."""
        card = self.g.hand('festival')
        self.g.mana('WWWW')
        self.assertNotIn(card, [a.source for a in self.gs.available_actions_from_hand()
                                if isinstance(a, AbilityPipeline)])
        attacker = self.g.battlefield('grizzly-bears', owner=1)
        self.g.next_turn(True)

        self.g.cast_and_accept(card, None, card.abilities[0])
        self.assertFalse(self.gs.perm_querier.can_attack(attacker))

    def test_field_of_dreams(self):
        """Players play with the top card of their libraries revealed"""
        card = self.g.battlefield('field-of-dreams')
        self.g.resolve_spell(card)
        top_card = self.gs.pile_mgr.libraries[0][0]
        self.assertTrue(top_card.is_face_up)
        self.gs.pile_mgr.draw(0)
        top_card = self.gs.pile_mgr.libraries[0][0]
        self.assertTrue(top_card.is_face_up)

    def test_firestorm_phoenix(self):
        """If this card would die, bounce it instead; it cannot be re-summoned this turn"""
        self.gs.hands[0].clear()
        card = self.g.battlefield('firestorm-phoenix')  # 3/2
        bolt = self.g.hand('lightning-bolt')
        self.g.mana('RRRRRRRRRRRRR')
        self.g.cast_and_accept(bolt, card, bolt.abilities[0])
        self.assertIn(card, self.gs.hands[0])
        self.assertFalse(any(a.source is card for a in self.gs.available_actions_from_hand()))

        self.g.next_turn()
        self.assertTrue(any(a.source is card for a in self.gs.available_actions_from_hand()))

    def test_force_spike_1(self):
        """Counter target spell unless its controller pays {1} ... This is the counter test"""
        card = self.g.hand('force-spike')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('U')
        self.g.mana('RR', owner=1)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[0])
        bolt_pipeline.advance()
        self.assertIn(bolt_pipeline, [a.pipeline for a in self.gs.action_stack.actions if isinstance(a, AbilityAction)])
        bolt_stack_action = next(a for a in self.gs.action_stack.actions)

        card_pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[bolt_stack_action])
        card_pipeline.advance()
        card_pipeline.resolve_ability()
        allow_bolt_countered = self.gs.pending_choice.get_actions()[1]
        allow_bolt_countered.play()
        self.assertTrue(20, self.gs.life[1])
        self.assertTrue(self.gs.pending_choice is None)

    def test_force_spike_2(self):
        """Counter target spell unless its controller pays {1} ... This is the pay mana test"""
        card = self.g.hand('force-spike')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('U')
        self.g.mana('RR', owner=1)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[0])
        bolt_pipeline.advance()
        self.assertIn(bolt_pipeline, [a.pipeline for a in self.gs.action_stack.actions if isinstance(a, AbilityAction)])
        bolt_stack_action = next(a for a in self.gs.action_stack.actions)

        card_pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[bolt_stack_action])
        card_pipeline.advance()
        pay_mana_to_prevent_counter = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_mana_to_prevent_counter)
        self.assertTrue(any(a.source is bolt for a in self.gs.action_stack.actions),
                        'Lightning Bolt should still be on the stack but is not')
        self.assertEqual(17, self.gs.life[0],
                         "We never go back and resolve lightning-bolt"
                         "I'm not even sure that's correct, once the mana paid,"
                         "maybe priority goes back to the counterer")
        self.assertIsNone(self.gs.pending_choice)

    def test_fog(self):
        """Prevent all combat damage this turn"""
        card = self.g.hand('fog')
        attacker = self.g.battlefield('grizzly-bears', owner=1)  # 2/2
        bolt = self.g.hand('lightning-bolt', owner=1)

        self.g.next_turn(True)
        self.g.cast_and_accept(card, None, card.abilities[0])
        self.assertTrue(self.g.card_has_a_registered_listener(card))
        self.g.combat(attacker, None)
        self.assertEqual(20, self.gs.life[0])

        self.g.cast_and_accept(bolt, 0, bolt.abilities[0], owner=1)
        self.assertEqual(17, self.gs.life[0])  # doesn't prevent non-combat damage

        self.g.next_turn()
        self.g.combat(attacker, None)
        self.assertEqual(15, self.gs.life[0])  # effect wears off EOT

    def test_force_of_nature(self):
        """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
        self.g.battlefield('force-of-nature')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(12, self.gs.life[0])

        self.g.mana('GGGGG')  # five forests
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        pay_gggg = self.gs.pending_choice.get_actions()[0]
        pay_gggg.play()
        self.assertEqual(1, len([c for c in self.gs.pile_mgr.boards[0]
                                 if c.props.slug == 'forest' and not c.is_tapped]))

    def test_forcefield(self):
        """{1}: The next time an unblocked creature of your choice would deal combat damage to you this turn,
        prevent all but 1 of that damage"""
        ff = self.g.battlefield('forcefield', owner=1)
        self.g.mana('U', owner=1)
        attacker = self.g.battlefield('grizzly-bears')  # 2/2
        self.gs.combat_mgr.create_combat(attacker)
        self.g.activate_ability(ff.activated_abilities[0], attacker, 1)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(19, self.gs.life[1])

    def test_forethought_amulet(self):
        """At your upkeep, pay {3} or sac FA. If an instant or sorcery source would deal >=3 damage to you,
        it deals 2 damage to you instead."""
        card = self.g.battlefield('forethought-amulet')
        self.g.mana('UUUUUUUU')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        pay_mana = self.gs.pending_choice.get_actions()[0]
        pay_mana.play()

        self.g.next_turn(True)
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.cast_and_accept(bolt, 0, bolt.abilities[0], owner=1)
        self.assertEqual(18, self.gs.life[0])

        self.g.next_turn(True)
        self.gs.event_mgr.emit(UpkeepEvent(0))
        sac_fa = self.gs.pending_choice.get_actions()[1]
        sac_fa.play()
        self.assertIn(card, self.g.gy[0])


if __name__ == '__main__':
    unittest.main()

