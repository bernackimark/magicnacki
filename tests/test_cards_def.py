import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.mana import PayMana
from models.actions.special import Attach
from models.counter_tokens import HUNGER
from models.events_all import UpkeepEvent
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestCardsDEF(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

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
        self.assertIn(legal_host, [a.host for a in self.gs.pending_choice.get_actions() if isinstance(a, Attach)])

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

    def test_fog(self):
        """Prevent all combat damage this turn"""
        card = self.g.hand('fog')
        attacker = self.g.battlefield('grizzly-bears', owner=1)  #2/2
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
        for a in self.gs.pending_choice.get_actions():
            if isinstance(a, PayMana):
                a.play()
        self.assertEqual(1, len([c for c in self.gs.pile_mgr.boards[0]
                                 if c.props.slug == 'forest' and not c.is_tapped]))

    def test_forcefield(self):
        """{1}: The next time an unblocked creature of your choice would deal combat damage to you this turn,
        prevent all but 1 of that damage"""
        ff = self.g.battlefield('forcefield', owner=1)
        self.g.mana('U', owner=1)
        attacker = self.g.battlefield('grizzly-bears')  # 2/2
        self.gs.combat_mgr.create_combat(attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        self.g.activate_ability(ff.activated_abilities[0], attacker, 1)
        combat.handle_damage()
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

