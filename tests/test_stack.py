import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastWithNoSpellEffect
from models.actions.stack_accept_counter import PassPriority
from models.events_all import CastResolvedEvent
from tests.setup_helpers import TestGame

class TestStackResolution(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_stack_resolves_lifo_1(self):
        """P0: Giant Growth -> Grizzly Bears
        P1: Lightning Bolt -> Grizzly Bears
        both players pass; Grizzly Bears dies; Giant Growth fizzles"""
        gg = self.g.hand('giant-growth')
        bolt = self.g.hand('lightning-bolt', owner=1)
        creature = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.mana('G')
        self.g.mana('R', owner=1)

        gg_pipeline = AbilityPipeline(0, self.gs, gg, gg.abilities[0], targets=[creature])
        gg_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #1
        self.assertEqual(1, self.gs.action_on_idx)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[creature])
        bolt_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #0
        self.assertEqual(0, self.gs.action_on_idx)

        PassPriority(0, self.gs).play()  # player 0 passes priority (adds nothing else to the stack)
        PassPriority(1, self.gs).play()  # player 1 also passes priority, thus the entire stack should resolve

        self.assertIn(creature, self.gs.graveyards[0])
        self.assertIn(bolt, self.gs.graveyards[1])
        self.assertIn(gg, self.gs.graveyards[0])
        self.assertEqual(0, self.gs.action_on_idx)

    def test_stack_resolves_lifo_2(self):
        """P1: Lightning Bolt -> Grizzly Bears
        P0: Giant Growth -> Grizzly Bears
        both players pass"""
        gg = self.g.hand('giant-growth')
        bolt = self.g.hand('lightning-bolt', owner=1)
        creature = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.mana('G')
        self.g.mana('R', owner=1)

        self.g.next_turn(True)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[creature])
        bolt_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #0
        self.assertEqual(0, self.gs.action_on_idx)

        gg_pipeline = AbilityPipeline(0, self.gs, gg, gg.abilities[0], targets=[creature])
        gg_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #1
        self.assertEqual(1, self.gs.action_on_idx)

        PassPriority(1, self.gs).play()  # player 1 passes priority (adds nothing else to the stack)
        PassPriority(0, self.gs).play()  # player 0 also passes priority, thus the entire stack should resolve

        self.assertNotIn(creature, self.gs.graveyards[0])
        self.assertIn(bolt, self.gs.graveyards[1])
        self.assertIn(gg, self.gs.graveyards[0])
        self.assertEqual(1, self.gs.action_on_idx)

    def test_counter_spell_removes_spell(self):
        """P0 casts Shivan Dragon
        P1 casts Counterspell targeting Dragon
        resolve stack"""
        spell = self.g.hand('shivan-dragon')
        self.g.mana('RRRRRRRRRR')
        CastWithNoSpellEffect(0, self.gs, spell).play()  # push CastPermanentAction on stack
        stack_item = self.gs.action_stack.last_action

        counter = self.g.hand('counterspell', owner=1)
        self.g.mana('UU', owner=1)
        counter_pipeline = AbilityPipeline(1, self.gs, counter, counter.abilities[0], targets=[stack_item])
        counter_pipeline.advance()
        self.assertEqual(0, self.gs.action_on_idx)

        PassPriority(0, self.gs).play()
        PassPriority(1, self.gs).play()
        self.assertFalse(len(self.gs.action_stack.actions))
        self.assertIn(spell, self.g.gy[0])

    def test_counter_spell_a_counter_spell(self):
        """P0 casts Shivan Dragon
        P1 casts Counterspell targeting Dragon
        P0 casts Counterspell targeting Counterspell"""
        spell = self.g.hand('shivan-dragon')
        self.g.mana('RRRRRRRRRR')
        CastWithNoSpellEffect(0, self.gs, spell).play()  # push CastPermanentAction on stack
        spell_item = self.gs.action_stack.last_action

        counter = self.g.hand('counterspell', owner=1)
        self.g.mana('UU', owner=1)
        counter_pipeline = AbilityPipeline(1, self.gs, counter, counter.abilities[0], targets=[spell_item])
        counter_pipeline.advance()
        counter_item = self.gs.action_stack.last_action
        self.assertEqual(0, self.gs.action_on_idx)

        ctr_ctr = self.g.hand('counterspell')
        self.g.mana('UU')
        cc_pipeline = AbilityPipeline(0, self.gs, ctr_ctr, ctr_ctr.abilities[0], targets=[counter_item])
        cc_pipeline.advance()
        self.assertEqual(1, self.gs.action_on_idx)

        PassPriority(1, self.gs).play()
        PassPriority(0, self.gs).play()
        self.assertFalse(len(self.gs.action_stack.actions))
        self.assertIn(spell, self.gs.boards[0])

    def test_ability_survives_source_ltb(self):
        """Prodigal Sorcerer taps
        Bolt kills Sorcerer
        Ability still resolves"""
        card = self.g.battlefield('prodigal-sorcerer')
        aa = card.activated_abilities[0]
        bolt = self.g.battlefield('lightning-bolt', owner=1)
        self.g.mana('R', owner=1)

        self.g.next_turn()
        card_pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, targets=[1])
        card_pipeline.advance()
        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[card])
        bolt_pipeline.advance()

        PassPriority(0, self.gs).play()
        PassPriority(1, self.gs).play()
        self.assertEqual(19, self.gs.life[1])
        self.assertIn(card, self.g.gy[0])

    def test_illegal_target_fizzles(self):
        """Bolt -> Bears
        Unsummon Bears
        resolve"""
        bears = self.g.battlefield('grizzly-bears')
        unsummon = self.g.hand('unsummon')
        self.g.mana('UU')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('R', owner=1)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[bears])
        bolt_pipeline.advance()
        unsummon_pipleline = AbilityPipeline(0, self.gs, unsummon, unsummon.abilities[0], targets=[bears])
        unsummon_pipleline.advance()

        PassPriority(1, self.gs).play()
        PassPriority(0, self.gs).play()
        self.assertEqual(0, bears.damage_received_this_turn)
        self.assertIn(bears, self.gs.hands[0])
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_priority_changes(self):
        """P0 casts;
        assert priority=P1;
        P1 responds;
        assert priority=P0;
        P0 passes;
        assert priority=P1"""
        creature = self.g.hand('grizzly-bears')  # 2/2
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('GG')
        self.g.mana('R', owner=1)

        cast_creature = CastWithNoSpellEffect(0, self.gs, creature)
        cast_creature.play()
        self.assertEqual(1, self.gs.action_on_idx)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[creature])
        bolt_pipeline.advance()  # AbilityAction is pushed onto stack; priority moves to player #0
        self.assertEqual(0, self.gs.action_on_idx)

        PassPriority(0, self.gs).play()  # player 0 passes priority (adds nothing else to the stack)
        PassPriority(1, self.gs).play()  # player 1 also passes priority, thus the entire stack should resolve
        self.assertEqual(0, self.gs.action_on_idx)

    def test_counter_removes_only_its_target(self):
        """Bolt
        Growth
        Counterspell -> Growth
        resolve stack; bolt should have resolved"""
        creature = self.g.battlefield('grizzly-bears', owner=1)
        bolt = self.g.hand('lightning-bolt')
        gg = self.g.hand('giant-growth', owner=1)
        counter = self.g.hand('counterspell')
        self.g.mana('RUU')
        self.g.mana('G', owner=1)

        bolt_pipeline = AbilityPipeline(0, self.gs, bolt, bolt.abilities[0], targets=[creature])
        bolt_pipeline.advance()

        gg_pipeline = AbilityPipeline(1, self.gs, gg, gg.abilities[0], targets=[creature])
        gg_pipeline.advance()
        gg_stack_item = self.gs.action_stack.last_action

        counter_pipeline = AbilityPipeline(0, self.gs, counter, counter.abilities[0], targets=[gg_stack_item])
        counter_pipeline.advance()

        PassPriority(1, self.gs).play()
        PassPriority(0, self.gs).play()
        self.assertIn(creature, self.g.gy[1])
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_activated_ability_followed_by_spell(self):
        """Tap Prodigal Sorcerer
        Respond with Giant Growth
        resolve"""
        creature = self.g.battlefield('merfolk-of-the-pearl-trident')
        prodigal = self.g.battlefield('prodigal-sorcerer', owner=1)
        gg = self.g.hand('giant-growth')
        self.g.mana('G')

        prodigal_pipeline = AbilityPipeline(1, self.gs, prodigal, prodigal.abilities[0], targets=[creature])
        prodigal_pipeline.advance()

        gg_pipeline = AbilityPipeline(0, self.gs, gg, gg.abilities[0], targets=[creature])
        gg_pipeline.advance()

        PassPriority(1, self.gs).play()
        PassPriority(0, self.gs).play()
        self.assertIn(creature, self.gs.boards[0])
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_x_value_persists(self):
        """Braingeyser X=4;
        Counterspell;
        Counterspell"""
        self.gs.hands[0].clear()
        bg = self.g.hand('braingeyser')
        ctr1 = self.g.hand('counterspell')
        ctr2 = self.g.hand('counterspell', owner=1)
        self.g.mana('UUUUUUUUUU')
        self.g.mana('UU', owner=1)

        bg_pipeline = AbilityPipeline(0, self.gs, bg, bg.abilities[0], x_value=4, targets=[0])
        bg_pipeline.advance()
        bg_stack_item = self.gs.action_stack.last_action

        ctr2_pipeline = AbilityPipeline(1, self.gs, ctr2, ctr2.abilities[0], targets=[bg_stack_item])
        ctr2_pipeline.advance()
        ctr2_stack_item = self.gs.action_stack.last_action

        ctr1_pipeline = AbilityPipeline(0, self.gs, ctr1, ctr1.abilities[0], targets=[ctr2_stack_item])
        ctr1_pipeline.advance()

        PassPriority(1, self.gs).play()
        PassPriority(0, self.gs).play()
        self.assertEqual(4, len(self.gs.hands[0]))
        self.assertFalse(len(self.gs.action_stack.actions))

    def test_counter_precludes_cast_resolved_event(self):
        """Cast Raiders
        Cast Counterspell
        Resolve Counterspell
        Validate no CastResolvedEvent for Raiders
        """
        [h.clear() for h in self.gs.hands]
        self.gs.event_mgr._event_listeners.clear()
        raiders = self.g.hand('monss-goblin-raiders')
        self.g.mana('R')
        CastWithNoSpellEffect(0, self.gs, raiders).play()  # push CastPermanentAction on stack
        stack_item = self.gs.action_stack.last_action

        counter = self.g.hand('counterspell', owner=1)
        self.g.mana('UU', owner=1)
        counter_pipeline = AbilityPipeline(1, self.gs, counter, counter.abilities[0], targets=[stack_item])
        counter_pipeline.advance()
        self.assertEqual(0, self.gs.action_on_idx)

        PassPriority(0, self.gs).play()
        PassPriority(1, self.gs).play()
        self.assertFalse(any(e.card is raiders for e in
                             self.gs.event_mgr.get_events(self.gs.turn_mgr.turn_number, CastResolvedEvent)))


if __name__ == '__main__':
    unittest.main()
