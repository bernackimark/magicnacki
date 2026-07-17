import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.effects.resolvers_generic import PreventNextDamageTo, GraveyardToExileInItsEntirety, TakeAnotherTurn
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestPreventDamage(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

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
        cast_target_action = next(a for a in self.gs.available_actions_from_hand() if a.source is target)
        # TODO: casting a vanilla permanent never hits the stack; CastPermanentAction contains .play()

    def test_prevents_all_damage_when_amount_is_none(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        PreventNextDamageTo().resolve(self.gs, target, target)
        self.gs.apply_damage(attacker, 5, target)
        self.assertEqual(target.damage_received_this_turn, 0)

    def test_prevents_specified_amount(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        PreventNextDamageTo(3).resolve(self.gs, target, target)
        self.gs.apply_damage(attacker, 5, target)
        self.assertEqual(target.damage_received_this_turn, 2)

    def test_only_prevents_first_damage_event(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        PreventNextDamageTo(3).resolve(self.gs, target, target)
        self.gs.apply_damage(attacker, 2, target)
        self.gs.apply_damage(attacker, 2, target)
        self.assertEqual(target.damage_received_this_turn, 2)

    def test_combat_only_does_not_prevent_noncombat_damage(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        PreventNextDamageTo(3, combat_only=True).resolve(self.gs, target, target)
        self.gs.apply_damage(attacker, 3, target, is_combat=False)
        self.assertEqual(target.damage_received_this_turn, 3)

    def test_combat_only_prevents_combat_damage(self):
        attacker = self.g.card('goblin-hero')
        target = self.g.battlefield('grizzly-bears', owner=1)
        PreventNextDamageTo(3, combat_only=True).resolve(self.gs, target, target)
        self.gs.apply_damage(attacker, 3, target, is_combat=True)
        self.assertEqual(target.damage_received_this_turn, 0)

    def test_graveyard_to_exile_in_its_entirety(self):
        gy = self.g.gy[0]
        self.g.graveyard('merfolk-of-the-pearl-trident')
        self.assertEqual(1, len(gy))
        GraveyardToExileInItsEntirety().resolve(self.gs, None, 0)
        self.assertEqual(0, len(gy))

    def test_take_another_turn(self):
        time_walk = self.g.card('time-walk')
        TakeAnotherTurn().resolve(self.gs, time_walk, None)
        self.gs.phase_mgr.set_phase(Phase.PASS_THE_TURN, self.gs)


if __name__ == '__main__':
    unittest.main()

