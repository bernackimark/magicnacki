import unittest

from models.actions.end_step_pass_turn import PassTheTurn
from models.effects.base import Listener
from models.effects.listeners_generic import SkipUntaps
from models.effects.listeners_permission import UnblockableEOT, Meekstone
from models.events_all import CanCastQueryEvent, CanTargetQueryEvent
from models.systems.phase import Phase
from tests.setup_helpers import (add_to_battlefield, get_card,
                                 put_onto_battlefield_last_turn, put_onto_battlefield_this_turn, TestGame)

class TestCanAttack(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_creature_with_summoning_sickness_cannot_attack(self):
        creature = self.g.battlefield('serendib-efreet')
        self.assertTrue(creature.has_summoning_sickness)
        self.assertFalse(self.gs.perm_querier.can_attack(creature))

    def test_haste_overrides_summoning_sickness(self):
        # the new TestGame class .battlefield() failed with has summoning sickness
        creature = get_card(self.gs, 'ball-lightning')
        put_onto_battlefield_this_turn(creature, self.gs)
        # creature = self.g.battlefield('ball-lightning')
        self.assertTrue(creature.has_summoning_sickness)
        self.assertTrue(self.gs.perm_querier.can_attack(creature))

    def test_creature_can_attack_turn_after_etb(self):
        # the new TestGame class .battlefield() failed with has summoning sickness
        creature = get_card(self.gs, 'serendib-efreet')
        put_onto_battlefield_last_turn(creature, self.gs)
        self.assertFalse(creature.has_summoning_sickness)
        self.assertTrue(self.gs.perm_querier.can_attack(creature))

    def test_defender_cannot_attack(self):
        # the new TestGame class .battlefield() failed with has summoning sickness
        creature = get_card(self.gs, 'wall-of-swords')
        put_onto_battlefield_last_turn(creature, self.gs)
        self.assertFalse(creature.has_summoning_sickness)
        self.assertFalse(self.gs.perm_querier.can_attack(creature))

class TestCanBlock(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_creature_can_block_normally(self):
        attacker = self.g.battlefield('tundra-wolves')
        blocker = self.g.battlefield('savannah-lions', owner=1)
        self.assertTrue(self.gs.perm_querier.can_block(blocker, attacker))

    def test_tapped_creature_cannot_block(self):
        attacker = self.g.battlefield('tundra-wolves')
        blocker = self.g.battlefield('savannah-lions', owner=1)
        blocker.tap()
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

    def test_flying_creature_cannot_be_blocked_by_non_flying_creature(self):
        attacker = self.g.battlefield('serendib-efreet')
        blocker = self.g.battlefield('savannah-lions', owner=1)
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

    def test_flying_creature_can_be_blocked_by_flying_creature(self):
        attacker = self.g.battlefield('serendib-efreet')
        blocker = self.g.battlefield('wall-of-swords', owner=1)
        self.assertTrue(self.gs.perm_querier.can_block(blocker, attacker))

    def test_flying_creature_can_be_blocked_by_reach_creature(self):
        attacker = self.g.battlefield('serendib-efreet')
        blocker = self.g.battlefield('giant-spider', owner=1)
        self.assertTrue(self.gs.perm_querier.can_block(blocker, attacker))

    def test_unblockable_creature_cannot_be_blocked(self):
        attacker = self.g.battlefield('tundra-wolves')
        blocker = self.g.battlefield('savannah-lions', owner=1)
        self.gs.event_mgr.register(UnblockableEOT(attacker), attacker)
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

class TestCanCast(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_can_cast_creature_when_mana_is_sufficient(self):
        creature = self.g.hand('serendib-efreet')
        self.g.mana('GRU')
        self.assertTrue(self.gs.perm_querier.can_cast(creature, p_id=0))

    def test_cannot_cast_creature_without_any_mana(self):
        card = self.g.hand('serendib-efreet')
        self.assertFalse(self.gs.perm_querier.can_cast(card, p_id=0))

    def test_cannot_cast_creature_without_correct_mana(self):
        card = get_card(self.gs, 'serendib-efreet', 0)
        self.g.mana('GR')
        self.assertFalse(self.gs.perm_querier.can_cast(card, p_id=0))

    def test_cannot_cast_land_if_land_already_played(self):
        land = self.g.hand('plains')
        self.gs.turn_mgr.has_played_land = True
        self.assertFalse(self.gs.perm_querier.can_cast(land, p_id=0))

    def test_can_cast_instant_on_opponents_turn(self):
        instant = self.g.hand('giant-growth')
        self.g.mana('GRU')
        self.g.next_turn(True)
        self.assertTrue(self.gs.perm_querier.can_cast(instant, p_id=0))

    def test_cannot_cast_sorcery_on_opponents_turn(self):
        sorcery = self.g.hand('timetwister')
        self.g.mana('GRU')
        self.g.next_turn(True)
        self.assertFalse(self.gs.perm_querier.can_cast(sorcery, p_id=0))

    def test_permission_effect_can_prevent_cast(self):
        card = self.g.hand('merfolk-of-the-pearl-trident')
        self.g.mana('GRU')

        class CantCastCreatures(Listener):
            listens_to = CanCastQueryEvent

            def on_event(self, gs, source, event: CanCastQueryEvent):
                if 'Creature' in event.card.card_types:
                    event.permission = False

        self.gs.event_mgr.register(CantCastCreatures(), source_card=card)
        self.assertFalse(self.gs.perm_querier.can_cast(card, p_id=0))


class TestCanDamage(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_creature_can_damage_another_creature(self):
        source = self.g.card('grizzly-bears')
        target = self.g.card('hill-giant', 1)
        self.assertTrue(self.gs.perm_querier.can_damage(target, source))

    def test_creature_can_damage_player(self):
        source = self.g.card('grizzly-bears')
        self.assertTrue(self.gs.perm_querier.can_damage(1, source))

    def test_black_knight_can_be_damaged_by_black_source(self):
        source = self.g.card('drudge-skeletons')
        target = self.g.card('black-knight', 1)
        self.assertTrue(self.gs.perm_querier.can_damage(target, source))

    def test_black_knight_cannot_be_damaged_by_white_source(self):
        source = self.g.card('savannah-lions')
        target = self.g.card('black-knight', 1)
        self.assertFalse(self.gs.perm_querier.can_damage(target, source))


class TestCanTarget(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_can_target_normal_creature(self):
        source = self.g.card('lightning-bolt')
        target = self.g.card('grizzly-bears', 1)
        self.assertTrue(self.gs.perm_querier.can_target(target, source))

    def test_can_target_player(self):
        # currently a player can always be targeted
        source = self.g.card('lightning-bolt')
        self.assertTrue(self.gs.perm_querier.can_target(1, source))

    def test_black_knight_cannot_be_targeted_by_white_source(self):
        source = self.g.card('swords-to-plowshares')
        target = self.g.card('black-knight', 1)
        self.assertFalse(self.gs.perm_querier.can_target(target, source))

    def test_listener_can_forbid_targeting(self):
        source = self.g.card('lightning-bolt')
        target = self.g.card('grizzly-bears', 1)

        class CannotBeTargeted(Listener):
            listens_to = CanTargetQueryEvent

            def on_event(self, gs, source_card, event: CanTargetQueryEvent):
                if event.target is target:
                    event.permission = False

        self.gs.event_mgr.register(CannotBeTargeted(), target)
        self.assertFalse(self.gs.perm_querier.can_target(target, source))


class TestCanUntap(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_creature_can_untap_by_default(self):
        creature = self.g.card('grizzly-bears')
        self.assertTrue(self.gs.perm_querier.can_untap(creature))

    def test_meekstone_prevents_large_creature_from_untapping(self):
        meekstone = self.g.battlefield('meekstone')
        large_creature = self.g.card('craw-wurm', 1)
        self.gs.event_mgr.register(Meekstone(), meekstone)
        add_to_battlefield(large_creature, self.gs)
        self.assertFalse(self.gs.perm_querier.can_untap(large_creature))

    def test_meekstone_allows_small_creature_to_untap(self):
        meekstone = self.g.battlefield('meekstone')
        small_creature = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        self.assertTrue(self.gs.perm_querier.can_untap(small_creature))

    def test_barls_cage(self):
        barls_cage = self.g.card('barls-cage')
        affected = self.g.card('grizzly-bears', 1)
        unaffected = self.g.card('hill-giant', 1)
        self.gs.event_mgr.register(SkipUntaps(affected), barls_cage)
        PassTheTurn(0, self.gs).play()
        self.gs.phase_mgr.set_phase(Phase.UNTAP, self.gs)
        self.assertFalse(self.gs.perm_querier.can_untap(affected), f"barls-cage didn't prevent {affected}'s untap")
        self.assertTrue(self.gs.perm_querier.can_untap(unaffected), f"Barl's Cage should have let {unaffected} untap")


if __name__ == '__main__':
    unittest.main()
