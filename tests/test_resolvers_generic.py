import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastWithNoSpellEffect
from models.actions.stack_accept_counter import PassPriority
from models.constants import KW
from models.game_card.counter_tokens import STUN
from models.effects.listeners_generic import PreventNextDamageTo, TakeAnotherTurn
from models.effects.resolvers_generic import GraveyardToExileInItsEntirety
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestResolversGeneric(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_add_stun_counter(self):
        barls_cage = self.g.battlefield('barls-cage')
        aa = barls_cage.activated_abilities[0]
        self.g.mana('RRRRRRRR')
        targeted = self.g.battlefield('grizzly-bears', owner=1)
        untargeted = self.g.battlefield('hill-giant', owner=1)
        untargeted.tap()
        self.g.activate_ability(aa, targeted)
        self.assertEqual(1, targeted.counters.get_count(STUN))

        self.g.next_turn(True)
        # is the phase already set to UNTAP in the line above, thus triggering 2x?
        self.assertFalse(untargeted.is_tapped)
        self.assertTrue(targeted.is_tapped)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UNTAP)
        self.assertFalse(targeted.is_tapped)

    def test_all_walks_removed(self):
        card = self.g.battlefield('hammerheim')
        aa = card.activated_abilities[1]  # remove all walks
        islandwalker = self.g.battlefield('segovian-leviathan')
        self.assertIn(KW.ISLANDWALK, islandwalker.keyword_abilities)
        self.g.activate_ability(aa, islandwalker)
        self.assertNotIn(KW.ISLANDWALK, islandwalker.keyword_abilities)

        self.g.next_turn()
        self.assertIn(KW.ISLANDWALK, islandwalker.keyword_abilities)

    def test_base_pt_p_and_t_declared(self):
        """Set target creature's base PT to specified values (p or t can be None, defaulting to its orig base value)"""
        card = self.g.battlefield('sorceress-queen')
        aa = card.activated_abilities[0]  # set target base PT to (0/2)
        target = self.g.battlefield('grizzly-bears')  # 2/2
        pump = self.g.hand('giant-growth')  # +3/+3

        self.g.next_turn()
        self.g.cast_and_accept(pump, target, pump.abilities[0])
        self.g.activate_ability(aa, target)
        self.assertEqual(3, target.power)
        self.assertEqual(5, target.toughness)

    def test_base_pt_only_p_declared(self):
        """Set target creature's base PT to specified values (p or t can be None, defaulting to its orig base value)"""
        card = self.g.battlefield('island-of-wak-wak')
        aa = card.activated_abilities[0]  # set power = 0
        target = self.g.battlefield('air-elemental')  # 4/4
        pump = self.g.hand('giant-growth')  # +3/+3

        self.g.cast_and_accept(pump, target, pump.abilities[0])
        self.g.activate_ability(aa, target)
        self.assertEqual(3, target.power)
        self.assertEqual(7, target.toughness)

        self.g.next_turn()
        self.assertEqual(4, target.power)
        self.assertEqual(4, target.toughness)

    def test_combat_only_does_not_prevent_noncombat_damage(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        eff = PreventNextDamageTo(3, combat_only=True)
        eff.protected = target
        self.gs.event_mgr.register(eff, attacker)
        self.gs.apply_damage(attacker, 3, target, is_combat=False)
        self.assertIn(target, self.g.gy[1])

    def test_combat_only_prevents_combat_damage(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        eff = PreventNextDamageTo(3, combat_only=True)
        eff.protected = target
        self.gs.event_mgr.register(eff, attacker)
        self.gs.apply_damage(attacker, 3, target, is_combat=True)
        self.assertEqual(target.damage_received_this_turn, 0)

    def test_counter_an_ability_action(self):
        card = self.g.hand('counterspell')
        target = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('UU')
        self.g.mana('R', owner=1)
        target_pipeline = AbilityPipeline(1, self.gs, target, target.abilities[0])
        target_pipeline.targets.append(0)
        target_pipeline.finish()
        target_ability = self.gs.action_stack.last_action
        card_pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        card_pipeline.targets.append(target_ability)
        card_pipeline.resolve_ability()
        self.assertEqual(0, len(self.gs.action_stack.actions))
        self.assertIn(card, self.g.gy[0])
        self.assertIn(target, self.g.gy[1])
        self.assertEqual(20, self.gs.life[0])

    def test_counter_a_vanilla_permanent(self):
        self.g.clear_hands()
        self.g.next_turn(True)
        card = self.g.hand('counterspell')
        target = self.g.hand('grizzly-bears', owner=1)
        self.g.mana('UU')
        self.g.mana('GGG', owner=1)
        CastWithNoSpellEffect(1, self.gs, target).play()  # adds grizzly-bears casting to stack
        target_spell = self.gs.action_stack.last_action
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[target_spell])
        pipeline.advance()
        PassPriority(0, self.gs).play()
        PassPriority(1, self.gs).play()
        self.assertIn(target, self.g.gy[1])
        self.assertFalse(self.gs.action_stack.actions)

    def test_prevents_all_damage_when_amount_is_none(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        eff = PreventNextDamageTo()
        eff.protected = target
        self.gs.event_mgr.register(eff, attacker)
        self.gs.apply_damage(attacker, 5, target)
        self.assertEqual(target.damage_received_this_turn, 0)

    def test_prevents_specified_amount(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        eff = PreventNextDamageTo(3)
        eff.protected = target
        self.gs.event_mgr.register(eff, attacker)
        self.gs.apply_damage(attacker, 4, target)
        self.assertEqual(1, target.damage_received_this_turn)

    def test_only_prevents_first_damage_event(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        eff = PreventNextDamageTo(3)
        eff.protected = target
        self.gs.event_mgr.register(eff, attacker)
        self.gs.apply_damage(attacker, 2, target)
        self.assertIn(target, self.gs.boards[1])
        self.gs.apply_damage(attacker, 2, target)
        self.assertIn(target, self.g.gy[1])

    def test_graveyard_to_exile_in_its_entirety(self):
        gy = self.g.gy[0]
        card = self.g.graveyard('merfolk-of-the-pearl-trident')
        self.assertEqual(1, len(gy))
        GraveyardToExileInItsEntirety().resolve(self.gs, card, 0)
        self.assertEqual(0, len(gy))

    def test_steal(self):
        card = self.g.battlefield('aladdin')
        aa = card.activated_abilities[0]
        self.g.mana('RRRR')
        target = self.g.battlefield('sol-ring', owner=1)
        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)
        self.assertIn(target, self.gs.boards[0])

        self.gs.pile_mgr.destroy(card)
        self.assertEqual(1, target.owner_id)
        self.assertIn(target, self.gs.boards[1])

    def test_take_another_turn(self):
        time_walk = self.g.card('time-walk')
        eff = TakeAnotherTurn()
        self.gs.event_mgr.register(eff, time_walk)
        self.gs.phase_mgr.set_phase(Phase.PASS_THE_TURN)


if __name__ == '__main__':
    unittest.main()

