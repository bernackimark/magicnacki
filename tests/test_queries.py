import unittest

from models.actions.end_step_pass_turn import PassTheTurn
from models.effects.base import Listener
from models.effects.listeners_generic import SkipUntaps
from models.effects.listeners_permission import UnblockableEOT, Meekstone
from models.events_all import CanCastQueryEvent, CanTargetQueryEvent
from models.phase_manager import Phase
from tests.setup_helpers import (add_to_battlefield, create_engine_and_universe, get_card,
                                 put_onto_battlefield_last_turn, put_onto_battlefield_this_turn)

class TestCanAttack(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_creature_with_summoning_sickness_cannot_attack(self):
        creature = get_card(self.gs, 'serendib-efreet')
        put_onto_battlefield_this_turn(creature, self.gs)
        self.assertTrue(creature.has_summoning_sickness)
        self.assertFalse(self.gs.perm_querier.can_attack(creature))

    def test_haste_overrides_summoning_sickness(self):
        creature = get_card(self.gs, 'ball-lightning')
        put_onto_battlefield_this_turn(creature, self.gs)
        self.assertTrue(creature.has_summoning_sickness)
        self.assertTrue(self.gs.perm_querier.can_attack(creature))

    def test_creature_can_attack_turn_after_etb(self):
        creature = get_card(self.gs, 'serendib-efreet')
        put_onto_battlefield_last_turn(creature, self.gs)
        self.assertFalse(creature.has_summoning_sickness)
        self.assertTrue(self.gs.perm_querier.can_attack(creature))

    def test_defender_cannot_attack(self):
        creature = get_card(self.gs, 'wall-of-swords')
        put_onto_battlefield_last_turn(creature, self.gs)
        self.assertFalse(creature.has_summoning_sickness)
        self.assertFalse(self.gs.perm_querier.can_attack(creature))

class TestCanBlock(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_creature_can_block_normally(self):
        attacker = get_card(self.gs, 'tundra-wolves', 0)
        blocker = get_card(self.gs, 'savannah-lions', 1)
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        self.assertTrue(self.gs.perm_querier.can_block(blocker, attacker))

    def test_tapped_creature_cannot_block(self):
        attacker = get_card(self.gs, 'tundra-wolves', 0)
        blocker = get_card(self.gs, 'savannah-lions', 1)
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        blocker.tap()
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

    def test_flying_creature_cannot_be_blocked_by_non_flying_creature(self):
        attacker = get_card(self.gs, 'serendib-efreet', 0)
        blocker = get_card(self.gs, 'savannah-lions', 1)
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

    def test_flying_creature_can_be_blocked_by_flying_creature(self):
        attacker = get_card(self.gs, 'serendib-efreet', 0)
        blocker = get_card(self.gs, 'wall-of-swords', 0)
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        self.assertTrue(self.gs.perm_querier.can_block(blocker, attacker))

    def test_flying_creature_can_be_blocked_by_reach_creature(self):
        attacker = get_card(self.gs, 'serendib-efreet', 0)
        blocker = get_card(self.gs, 'giant-spider', 0)
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        self.assertTrue(self.gs.perm_querier.can_block(blocker, attacker))

    def test_unblockable_creature_cannot_be_blocked(self):
        attacker = get_card(self.gs, 'tundra-wolves', 0)
        blocker = get_card(self.gs, 'savannah-lions', 1)
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        self.gs.event_mgr.register(UnblockableEOT(attacker), attacker)
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

class TestCanCast(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_can_cast_creature_when_mana_is_sufficient(self):
        creature = get_card(self.gs, 'serendib-efreet', 0)
        lands = [get_card(self.gs, 'island', 0), get_card(self.gs, 'forest', 0), get_card(self.gs, 'mountain', 0)]
        [add_to_battlefield(land, self.gs) for land in lands]
        self.assertTrue(self.gs.perm_querier.can_cast(creature, p_id=0))

    def test_cannot_cast_creature_without_any_mana(self):
        card = get_card(self.gs, 'serendib-efreet', 0)
        self.assertFalse(self.gs.perm_querier.can_cast(card, p_id=0))

    def test_cannot_cast_creature_without_correct_mana(self):
        card = get_card(self.gs, 'serendib-efreet', 0)
        lands = [get_card(self.gs, 'forest', 0), get_card(self.gs, 'mountain', 0)]
        [add_to_battlefield(land, self.gs) for land in lands]
        self.assertFalse(self.gs.perm_querier.can_cast(card, p_id=0))

    def test_cannot_cast_land_if_land_already_played(self):
        land = get_card(self.gs, 'plains', 0)
        self.gs.turn_mgr.has_played_land = True
        self.assertFalse(self.gs.perm_querier.can_cast(land, p_id=0))

    def test_can_cast_instant_on_opponents_turn(self):
        instant = get_card(self.gs, 'giant-growth', 0)
        lands = [get_card(self.gs, 'island', 0), get_card(self.gs, 'forest', 0), get_card(self.gs, 'mountain', 0)]
        [add_to_battlefield(land, self.gs) for land in lands]
        self.gs.turn_mgr.player_turn_idx = 1  # opponent's turn
        self.assertTrue(self.gs.perm_querier.can_cast(instant, p_id=0))

    def test_cannot_cast_sorcery_on_opponents_turn(self):
        sorcery = get_card(self.gs, 'timetwister', 0)
        lands = [get_card(self.gs, 'island', 0), get_card(self.gs, 'forest', 0), get_card(self.gs, 'mountain', 0)]
        [add_to_battlefield(land, self.gs) for land in lands]
        self.gs.turn_mgr.player_turn_idx = 1  # opponent's turn
        self.assertFalse(self.gs.perm_querier.can_cast(sorcery, p_id=0))

    def test_permission_effect_can_prevent_cast(self):
        card = get_card(self.gs, 'merfolk-of-the-pearl-trident', 0)
        lands = [get_card(self.gs, 'island', 0), get_card(self.gs, 'forest', 0), get_card(self.gs, 'mountain', 0)]
        [add_to_battlefield(land, self.gs) for land in lands]

        class CantCastCreatures(Listener):
            listens_to = CanCastQueryEvent

            def on_event(self, gs, source, event: CanCastQueryEvent):
                if 'Creature' in event.card.card_types:
                    event.permission = False

        self.gs.event_mgr.register(CantCastCreatures(), source_card=card)
        self.assertFalse(self.gs.perm_querier.can_cast(card, p_id=0))


class TestCanDamage(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_creature_can_damage_another_creature(self):
        source = get_card(self.gs, 'grizzly-bears', 0)
        target = get_card(self.gs, 'hill-giant', 1)
        self.assertTrue(self.gs.perm_querier.can_damage(target, source))

    def test_creature_can_damage_player(self):
        source = get_card(self.gs, 'grizzly-bears', 0)
        self.assertTrue(self.gs.perm_querier.can_damage(1, source))

    def test_black_knight_can_be_damaged_by_black_source(self):
        source = get_card(self.gs, 'drudge-skeletons', 0)
        target = get_card(self.gs, 'black-knight', 1)
        self.assertTrue(self.gs.perm_querier.can_damage(target, source))

    def test_black_knight_cannot_be_damaged_by_white_source(self):
        source = get_card(self.gs, 'savannah-lions', 0)
        target = get_card(self.gs, 'black-knight', 1)
        self.assertFalse(self.gs.perm_querier.can_damage(target, source))


class TestCanTarget(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_can_target_normal_creature(self):
        source = get_card(self.gs, 'lightning-bolt', 0)
        target = get_card(self.gs, 'grizzly-bears', 1)
        self.assertTrue(self.gs.perm_querier.can_target(target, source))

    def test_can_target_player(self):
        # currently a player can always be targeted
        source = get_card(self.gs, 'lightning-bolt', 0)
        self.assertTrue(self.gs.perm_querier.can_target(1, source))

    def test_black_knight_cannot_be_targeted_by_white_source(self):
        source = get_card(self.gs, 'swords-to-plowshares', 0)
        target = get_card(self.gs, 'black-knight', 1)
        self.assertFalse(self.gs.perm_querier.can_target(target, source))

    def test_listener_can_forbid_targeting(self):
        source = get_card(self.gs, 'lightning-bolt', 0)
        target = get_card(self.gs, 'grizzly-bears', 1)

        class CannotBeTargeted(Listener):
            listens_to = CanTargetQueryEvent

            def on_event(self, gs, source_card, event: CanTargetQueryEvent):
                if event.target is target:
                    event.permission = False

        self.gs.event_mgr.register(CannotBeTargeted(), target)
        self.assertFalse(self.gs.perm_querier.can_target(target, source))


class TestCanUntap(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_creature_can_untap_by_default(self):
        creature = get_card(self.gs, 'grizzly-bears', 0)
        self.assertTrue(self.gs.perm_querier.can_untap(creature))

    def test_meekstone_prevents_large_creature_from_untapping(self):
        meekstone = get_card(self.gs, 'meekstone', 0)
        large_creature = get_card(self.gs, 'craw-wurm', 1)
        add_to_battlefield(meekstone, self.gs)
        self.gs.event_mgr.register(Meekstone(), meekstone)
        add_to_battlefield(large_creature, self.gs)
        self.assertFalse(self.gs.perm_querier.can_untap(large_creature))

    def test_meekstone_allows_small_creature_to_untap(self):
        meekstone = get_card(self.gs, 'meekstone', 0)
        small_creature = get_card(self.gs, 'merfolk-of-the-pearl-trident', 1)
        add_to_battlefield(meekstone, self.gs)
        add_to_battlefield(small_creature, self.gs)
        self.assertTrue(self.gs.perm_querier.can_untap(small_creature))

    def test_barls_cage(self):
        barls_cage = get_card(self.gs, 'barls-cage', 0)
        affected = get_card(self.gs, 'grizzly-bears', 1)
        unaffected = get_card(self.gs, 'hill-giant', 1)
        self.gs.event_mgr.register(SkipUntaps(affected), barls_cage)
        PassTheTurn(0, self.gs).play()
        self.gs.phase_mgr.set_phase(Phase.UNTAP, self.gs)
        self.assertFalse(self.gs.perm_querier.can_untap(affected), f"barls-cage didn't prevent {affected}'s untap")
        self.assertTrue(self.gs.perm_querier.can_untap(unaffected), f"Barl's Cage should have let {unaffected} untap")


if __name__ == '__main__':
    unittest.main()
