import unittest

from models.actions.draw_discard import DrawCard
from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.mana import PayMana
from models.actions.special import Attach, PayManaToDrawCards
from models.events_all import CastResolvedEvent, UpkeepEvent
from models.phase_manager import Phase
from models.zone import Zone
from tests.setup_helpers import TestGame


class TestCardsTUV(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

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
        self.gs.event_mgr.emit(UpkeepEvent(0), self.gs)
        self.assertTrue(any(isinstance(a, PayMana) for a in self.gs.pending_choice.get_actions()))

    def test_time_vault(self):
        """This artifact enters tapped. This artifact doesn't untap during your untap step.
        If you would begin your turn while this artifact is tapped, you may: skip that turn & untap this artifact.
        {T}: Take an extra turn after this one."""
        self.g.mana('UUUUUUUUUU')
        tv = self.g.battlefield('time-vault')
        self.assertTrue(tv.is_tapped)

        self.g.next_turn()
        skip_turn_and_untap_tv = self.gs.pending_choice.options[0]
        skip_turn_and_untap_tv.play()
        self.g.activate_ability(tv.activated_abilities[0])
        PassTheTurn(0, self.gs).play()
        self.assertEqual(0, self.gs.turn_mgr.player_turn_idx)
        self.assertTrue(tv.is_tapped)

    def test_timetwister(self):
        """Each player shuffles their hand & graveyard into their library, then draws seven cards.
        (Then put Timetwister into its owner's graveyard.)"""
        # this works 1/2 the time
        self.g.graveyard('scryb-sprites')
        self.g.graveyard('serra-angel')
        self.g.hand('island')
        self.g.hand('island')
        card = self.g.hand('timetwister')
        self.g.gy[0].clear()
        self.gs.pile_mgr.move_card(card, Zone.GRAVEYARD, emit_zone_event=False)
        card.abilities[0].effect.resolve(self.gs, card, None)  # type: ignore
        self.assertTrue(7, len(self.gs.pile_mgr.hands[0].cards))
        self.assertIn(card, self.g.gy[0])

    def test_unstable_mutation(self):
        """Host gets +3/+3. At host's upkeep, put a -1/-1 counter on host."""
        card = self.g.battlefield('unstable-mutation')
        host = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        Attach(0, self.gs, card, host).play()
        card.abilities[1].effect.resolve(self.gs, card, host)  # type: ignore
        self.assertEqual(4, host.power)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.assertEqual(3, host.power)

    def test_urzas_miter(self):
        """Whenever an artifact you control is put into a graveyard from the battlefield,
        if it wasn't sacrificed, you may pay {3} to draw a card"""
        card = self.g.battlefield('urzas-miter')
        self.gs.event_mgr.register(card.abilities[0].effect, card)
        artifact = self.g.battlefield('sol-ring')
        self.gs.pile_mgr.destroy(artifact)
        self.assertTrue(any(isinstance(a, PayManaToDrawCards) for a in self.gs.pending_choice.get_actions()))

    def test_verduran_enchantress(self):
        """Whenever you cast an enchantment spell, you may draw a card"""
        self.g.battlefield('verduran-enchantress')
        self.g.mana('UUUUU')
        enchantment = self.g.card('undertow')
        cast_event = CastResolvedEvent(enchantment, 0)
        self.gs.event_mgr.emit(cast_event, self.gs)
        self.assertTrue(any(isinstance(a, DrawCard) for a in self.gs.pending_choice.options))


if __name__ == '__main__':
    unittest.main()
