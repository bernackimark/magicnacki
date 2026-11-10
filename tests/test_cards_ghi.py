import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastWithNoSpellEffect
from models.events_all import EndStepEvent, CombatEndEvent, DrawStepEvent, AttackEvent
from models.systems.phase import Phase
from models.constants import Zone
from tests.setup_helpers import TestGame

class TestCardsGHI(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_gabriel_angelfire(self):
        """At your upkeep, choose flying, first strike, trample, or rampage 3.
        GA gains that ability until your next upkeep"""

    def test_gaeas_avenger(self):
        """GA PT are each equal to 1 plus the number of artifacts your opponents control."""

    def test_gaeas_liege(self):
        """As long as GL isn't attacking, PT are each = of Forests you control.
        As long as GL is attacking, PT are each equal = Forests defending player controls.
        {T}: Target land becomes a Forest until GL leaves the battlefield."""

    def test_gaeas_touch_forest_to_battlefield(self):
        """{0}: You may put a basic Forest card from your hand onto the battlefield.
        Activate only as a sorcery and only once each turn."""
        card = self.g.battlefield('gaeas-touch')
        aa = card.activated_abilities[1]
        self.g.mana('G')
        self.g.next_turn()
        forest = self.g.hand('forest')
        self.g.activate_ability(aa, forest)
        self.assertTrue(self.gs.mana_pools[0].can_pay('GG'))
        self.g.hand('forest')
        ability = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        self.assertFalse(ability.can_begin())

    def test_gaeas_touch_add_gg(self):
        """Sacrifice this enchantment: Add {GG}."""
        card = self.g.battlefield('gaeas-touch')
        aa = card.activated_abilities[0]
        self.g.activate_ability(aa, 0)
        self.assertTrue(self.gs.mana_pools[0].can_pay('GG'))
        self.assertIn(card, self.g.gy[0])

    def test_gaseous_form(self):
        """Prevent all combat damage that would be dealt to and dealt by enchanted creature"""
        host = self.g.battlefield('merfolk-of-the-pearl-trident')
        card = self.g.battlefield('gaseous-form')
        self.g.attach(card, host)
        blocker = self.g.battlefield('scryb-sprites')
        self.g.next_turn()
        self.g.combat(host, blocker)
        self.assertTrue(host.zone == Zone.BATTLEFIELD)
        self.assertTrue(blocker.zone == Zone.BATTLEFIELD)

    def test_gate_to_phyrexia(self):
        """Sacrifice a creature: Destroy target artifact. Activate only during your upkeep and only once each turn."""

    def test_gauntlet_of_might(self):
        """Red creatures get +1/+1. Whenever a Mountain is tapped for mana, its controller adds an additional {R}"""
        self.g.battlefield('gauntlet-of-might')
        goblin = self.g.battlefield('monss-goblin-raiders')  # 1/1
        self.assertEqual((2, 2), (goblin.power, goblin.toughness))

        # mountain tapped for mana, extra {R} added
        mountain = self.g.battlefield('mountain')
        bolt = self.g.hand('lightning-bolt')
        self.g.cast_and_accept(bolt, 1, bolt.abilities[0], add_lots_of_mana=False)
        self.assertTrue(mountain.is_tapped)
        self.assertEqual(1, self.gs.mana_pools[0].available_mana['R'])

        # plains tapped for mana, doesn't add {W} & doesn't add {R}
        plains = self.g.battlefield('plains')
        holy_day = self.g.hand('holy-day')
        self.g.cast_and_accept(holy_day, eff_spec=holy_day.abilities[0], add_lots_of_mana=False)
        self.assertTrue(plains.is_tapped)
        self.assertEqual(0, self.gs.mana_pools[0].available_mana['W'])
        self.assertEqual(1, self.gs.mana_pools[0].available_mana['R'])

    def test_gauntlets_of_chaos(self):
        """{5}, Sac GOT: Exchange control of target artifact, creature, or land you control with
        target permanent opp controls that shares one of those types with it.
        If those permanents are exchanged this way, destroy all Auras attached to them."""
        self.g.mana('WWWWW')
        self.g.mana('W', owner=1)
        card = self.g.battlefield('gauntlets-of-chaos')
        aa = card.activated_abilities[0]
        aura = self.g.hand('holy-strength', owner=1)
        your_card = self.g.battlefield('ornithopter')
        opp_card = self.g.battlefield('grizzly-bears', owner=1)
        self.g.cast_and_accept(aura, opp_card, aura.abilities[0], owner=1, add_lots_of_mana=False)
        self.g.battlefield('sol-ring', owner=1)

        self.g.activate_ability(aa)
        select_ornithopter = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(select_ornithopter)

        self.assertEqual(2, len(self.gs.pending_choice.get_actions()))  # grizzly-bears & sol-ring, not plains
        select_grizzly_bears = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(select_grizzly_bears)

        self.assertEqual(0, opp_card.owner_id)
        self.assertEqual(1, your_card.owner_id)
        self.assertIn(aura, self.g.gy[1])
        self.assertIsNone(self.gs.pending_choice)

    def test_ghazban_ogre(self):
        """At your upkeep, transfer ownership of GO to the player with _solo_ the most life"""

    def test_ghost_ship(self):
        """Flying {UUU}: Regenerate this creature."""

    def test_ghosts_of_the_damned(self):
        """{T}: Target creature gets -1/-0 until end of turn."""

    def test_giant_growth(self):
        """Target creature gets +3/+3 until end of turn."""

    def test_giant_shark(self):
        """Islandhome. Whenever GS combats a creature that's been dealt damage this turn, GS gets +2/+0 & trample EOT"""

    def test_giant_slug(self):
        """{5}: At your next upkeep, GS gains landwalk of any type until the end of that turn."""
        card = self.g.battlefield('giant-slug')
        aa = card.activated_abilities[0]
        self.g.mana('UUUUU')
        self.g.activate_ability(aa, card)
        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(5, len(self.gs.pending_choice.get_actions()))

    def test_giant_strength(self):
        """Enchant creature Enchanted creature gets +2/+2."""

    def test_giant_tortoise(self):
        """This creature gets +0/+3 as long as it's untapped."""

    def test_giant_turtle(self):
        """This creature can't attack if it attacked during your last turn."""

    def test_glasses_of_urza(self):
        """{T}: Look at target player's hand."""

    def test_gloom(self):
        """White spells cost {3} more to cast. Activated abilities of white enchantments cost {3} more to activate."""

    def test_glyph_of_delusion(self):
        """Put X glyph counters on target creature that target Wall blocked this turn; X = power of blocked creature.
        The creature gains 'This creature doesn't untap during your untap step if it has a glyph counter on it' &
        'At your upkeep, remove a glyph counter from this creature.'"""

    def test_glyph_of_destruction(self):
        """Target blocking Wall you control gets +10/+0 until end of combat.
        Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
        card = self.g.hand('glyph-of-destruction')
        wall = self.g.battlefield('wall-of-bone')
        attacker = self.g.battlefield('grizzly-bears', owner=1)  # 2/2

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        com = self.gs.combat_mgr.get_combat(attacker)
        com.add_blocker(wall)
        self.g.cast_and_accept(card, wall, card.abilities[0])
        self.assertTrue(wall.power > 9)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(0, wall.damage_dealt_this_turn)
        self.gs.event_mgr.emit(EndStepEvent(0))
        self.assertIn(wall, self.g.gy[0])

    def test_glyph_of_doom(self):
        """At combat end, destroy all creatures that were blocked by that target wall this turn."""
        card = self.g.hand('glyph-of-doom')
        wall = self.g.battlefield('wall-of-brambles')  # 2/3
        attacker = self.g.battlefield('craw-wurm', owner=1)  # 6/4

        self.g.next_turn(True)
        self.g.cast_and_accept(card, wall, card.abilities[0])
        self.g.combat(attacker, wall)
        self.gs.event_mgr.emit(CombatEndEvent(0))
        self.assertIn(attacker, self.g.gy[1])

    def test_glyph_of_life(self):
        """Whenever target wall is dealt damage by an attacking creature this turn, you gain that much life."""
        card = self.g.hand('glyph-of-life')
        wall = self.g.battlefield('wall-of-brambles')  # 2/3
        attacker = self.g.battlefield('craw-wurm', owner=1)  # 6/4

        self.g.next_turn(True)
        self.g.cast_and_accept(card, wall, card.abilities[0])
        self.assertTrue(self.g.card_has_a_registered_listener(card))
        self.assertTrue(attacker.zone == Zone.BATTLEFIELD)
        self.assertTrue(wall.zone == Zone.BATTLEFIELD)
        self.g.combat(attacker, wall)
        self.assertEqual(26, self.gs.life[0])

    def test_glyph_of_reincarnation(self):
        """Cast this spell only after combat. Destroy all creatures blocked by target Wall this turn w/o regen.
        For each creature that died this way, put a creature card from the graveyard of the player who controlled
        that creature the last time it became blocked by that Wall onto the battlefield under its owner's control."""

    def test_goblin_balloon_brigade(self):
        """{R}: This creature gains flying until end of turn."""

    def test_goblin_caves(self):
        """Enchant land As long as enchanted land is a basic Mountain, Goblin creatures get +0/+2."""

    def test_goblin_digging_team(self):
        """{T}, Sacrifice this creature: Destroy target Wall."""

    def test_goblin_king(self):
        """Other Goblins get +1/+1 and have mountainwalk."""

    def test_goblin_rock_sled(self):
        """GRS doesn't untap during your untap step if it attacked during your last turn.
        GRS can't attack unless defending player controls a Mountain."""

    def test_goblin_shrine(self):
        """As long as host is a basic Mountain, all Goblins get +1/+0. When GS LTB, it deals 1 damage to each Goblin"""
        card = self.g.hand('goblin-shrine')
        host = self.g.battlefield('mountain')
        self.g.cast_and_accept(card, host, card.abilities[0])
        goblin = self.g.battlefield('monss-goblin-raiders')  # 1/1
        self.assertEqual(2, goblin.power)
        self.gs.pile_mgr.destroy(card)
        self.assertIn(goblin, self.g.gy[0])

    def test_goblin_wizard(self):
        """{T}: You may put a Goblin permanent card from your hand onto the battlefield.
        {R}: Target Goblin gains protection from white EOT."""

    def test_goblins_of_the_flarg(self):
        """When you control a Dwarf, sacrifice this creature."""

    def test_golgothian_sylex(self):
        """{1}, {T}: Each nontoken permanent with a name originally printed in the Antiquities expansion is sac'ed"""

    def test_gosta_dirk(self):
        """First strike Creatures with islandwalk can be blocked as though they didn't have islandwalk."""

    def test_granite_gargoyle(self):
        """Flying {R}: This creature gets +0/+1 until end of turn."""

    def test_grapeshot_catapult(self):
        """{T}: This creature deals 1 damage to target creature with flying."""

    def test_grave_robbers(self):
        """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""

    def test_gravity_sphere(self):
        """All creatures lose flying."""

    def test_great_defender(self):
        """Target creature gets +0/+X until end of turn, where X is its mana value."""

    def test_great_wall(self):
        """Creatures with plainswalk can be blocked as though they didn't have plainswalk."""

    def test_greater_realm_of_preservation(self):
        """{1W}: The next time a black or red source of your choice would deal you damage EOT, prevent that damage."""

    def test_greed(self):
        """{B}, Pay 2 life: Draw a card."""

    def test_green_mana_battery(self):
        """{2}, {T}: Put a charge counter on GMB.
        {T}, Remove x charge counters from this artifact: Add {G}, + {G} * x"""

    def test_green_ward(self):
        """Enchant creature Enchanted creature has protection from green. This effect doesn't remove this Aura."""

    def test_guardian_angel(self):
        """Prevent the next X damage that would be dealt to any target EOT.
        EOT, you may pay {1} any time you could cast an instant to prevent the next 1 damage that would be dealt to
        that permanent or player EOT."""

    def test_guardian_beast(self):
        """As long as GB is untapped, noncreature artifacts you control can't be enchanted, they have indestructible, &
        other players can't gain control of them. This effect doesn't remove Auras already attached."""
        # TODO: other players can't gain control of them
        card = self.g.battlefield('guardian-beast')
        protected = self.g.battlefield('sol-ring')
        artifact_destroyer = self.g.hand('disenchant')
        artifact_aura = self.g.hand('artifact-possession')
        self.g.mana('BBBWWW')

        self.assertFalse(self.gs.perm_querier.can_target(protected, artifact_aura))
        card.tap()
        self.assertTrue(self.gs.perm_querier.can_target(protected, artifact_aura))

        card.untap()
        destroy_pipeline = AbilityPipeline(0, self.gs, artifact_destroyer, artifact_destroyer.abilities[0],
                                           targets=[protected])
        destroy_pipeline.advance()
        destroy_pipeline.resolve_ability()
        self.assertIn(protected, self.gs.boards[0])

    def test_gwendlyn_di_corci(self):
        """{T}: Target player discards a card at random. Activate only during your turn."""

    def test_halfdane(self):
        """H's base PT = (3, 3)
        At your upkeep, change H's base PT = PT of target creature other than H until end of your NEXT upkeep
        If no legal targets, H's base PT = (3, 3)"""
        card = self.g.battlefield('halfdane')
        self.assertEqual((3, 3), card.base_pt)
        creature1 = self.g.battlefield('sengir-vampire')  # 4/4
        creature2 = self.g.battlefield('grizzly-bears')  # 2/2
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        set_pt_eq_to_sengir = self.gs.pending_choice.get_actions()[0]
        print(set_pt_eq_to_sengir)
        set_pt_eq_to_sengir.play()
        self.assertEqual(4, card.power)

        self.g.next_turn()
        self.gs.pile_mgr.destroy(creature1)
        self.gs.pile_mgr.destroy(creature2)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(3, card.power)

    def test_hammerheim(self):
        """{T}: Add {R}. {T}: Target creature loses all landwalk abilities until end of turn."""

    def test_hasran_ogress(self):
        """Whenever this creature attacks, it deals 3 damage to you unless you pay {2}"""
        card = self.g.battlefield('hasran-ogress')
        self.g.mana('GG')

        self.g.next_turn()
        self.gs.event_mgr.emit(AttackEvent(card))
        take_3_damage = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(take_3_damage)
        self.assertEqual(17, self.gs.life[0])

    def test_haunting_wind(self):
        """Whenever an artifact becomes tapped or a player activates an artifact's ability
        without {T} in its activation cost, HW deals 1 damage to that artifact's controller."""
        self.g.battlefield('haunting-wind')
        artifact_1 = self.g.battlefield('sol-ring', owner=1)
        artifact_1.tap()
        self.assertEqual(19, self.gs.life[1], '1 damage should be dealt for a tap unrelated to AA')

        artifact_2 = self.g.battlefield('aladdins-ring', owner=1)
        aa = artifact_2.activated_abilities[0]  # {8}, {T}
        self.g.mana('UUUUUUUUUUU')
        self.g.activate_ability(aa, 0)
        self.assertEqual(18, self.gs.life[1], '1 damage should be dealt for AA w tap')

        artifact_3 = self.g.battlefield('jade-statue', owner=1)
        aa = artifact_3.activated_abilities[0]  # {2}
        self.g.mana('RRRR')
        self.g.activate_ability(aa, artifact_3)
        self.assertEqual(17, self.gs.life[1], '1 damage should be dealt for AA w/o tap')

        non_artifact = self.g.battlefield('dragon-whelp')
        aa = non_artifact.activated_abilities[0]
        self.g.mana('R')
        self.g.activate_ability(aa, non_artifact)
        self.assertEqual(17, self.gs.life[1], '0 damage should be dealt for a non-artifact')

    def test_hazezon_tamar(self):
        """When Hazezon enters, create X 1/1 Sand Warrior creature tokens that are RGW at your next upkeep,
        where X is the number of lands you control at that time.
        When Hazezon leaves the battlefield, exile all Sand Warriors"""
        self.g.mana('W')
        card = self.g.battlefield('hazezon-tamar')
        self.assertEqual(1, len(self.gs.card_filter.on_player_board(0).creatures().result()))

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(2, len(self.gs.card_filter.on_player_board(0).creatures().result()))

        self.gs.pile_mgr.destroy(card)
        self.assertEqual(0, len(self.gs.card_filter.on_player_board(0).creatures().result()))

    def test_healing_salve(self):
        """Choose 1 - * Target player gains 3 life. * Prevent next 3 damage that would be dealt to any target EOT."""

    def test_heavens_gate(self):
        """One or more target creatures become white until end of turn."""

    def test_hellfire(self):
        """Destroy all nonblack creatures. H deals X plus 3 damage to you, X = creature count that died this way."""
        card = self.g.hand('hellfire')
        self.g.mana('BBBBBBBB')
        regen_creature = self.g.battlefield('sedge-troll', owner=1)
        aa = regen_creature.activated_abilities[0]
        self.g.mana('B', owner=1)

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.advance()

        regen_pipeline = AbilityPipeline(1, self.gs, regen_creature, aa.eff_spec, targets=[regen_creature])
        regen_pipeline.advance()

        regen_pipeline.resolve_ability()
        pipeline.resolve_ability()

        self.assertNotIn(regen_creature, self.g.gy[0])
        self.assertEqual(17, self.gs.life[0])

    def test_hell_swarm(self):
        """All creatures get -1/-0 until end of turn."""

    def test_hells_caretaker(self):
        """{T}, sac a creature: Reanimate target creature card from your gy. Activate only during your upkeep."""

    def test_hidden_path(self):
        """Green creatures have forestwalk"""

    def test_holy_armor(self):
        """Enchant creature Enchanted creature gets +0/+2. {W}: Enchanted creature gets +0/+1 until end of turn."""

    def test_holy_day(self):
        """Prevent all combat damage that would be dealt this turn."""

    def test_holy_light(self):
        """Nonwhite creatures get -1/-1 until end of turn."""

    def test_holy_strength(self):
        """Enchant creature Enchanted creature gets +1/+2."""

    def test_horn_of_deafening(self):
        """{2}, {T}: Prevent all combat damage that would be dealt by target creature this turn."""

    def test_horror_of_horrors(self):
        """Sacrifice a Swamp: Regenerate target black creature
        The next time that creature would be destroyed EOT, instead tap, remove from combat, and heal all its damage"""

    def test_howl_from_beyond(self):
        """Target creature gets +X/+0 until end of turn."""

    def test_howling_mine(self):
        """At each player's draw step, if this artifact is untapped, that player draws an additional card."""

    def test_hurkyls_recall(self):
        """Return all artifacts target player owns to their hand."""

    def test_hurr_jackal(self):
        """{T}: Target creature can't be regenerated this turn."""

    def test_hurricane(self):
        """Hurricane deals X damage to each creature with flying and each player"""
        card = self.g.card('hurricane')
        self.g.mana('GGG')
        flier = self.g.battlefield('ornithopter')  # 0/2
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=2)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertIn(flier, self.g.gy[0])
        self.assertEqual(18, self.gs.life[1])

    def test_hyperion_blacksmith(self):
        """{T}: You may tap or untap target artifact an opponent controls."""

    def test_hypnotic_specter(self):
        """When HS deals damage to an opp, opp discards a card at random"""
        card = self.g.battlefield('hypnotic-specter')

        self.g.next_turn()
        opp_card_cnt = len(self.gs.hands[1])
        self.gs.combat_mgr.create_combat(card)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(len(self.gs.hands[1]), opp_card_cnt - 1)

    def test_ichneumon_druid(self):
        """Whenever an opponent casts an instant spell other than the first instant spell that player casts each turn,
        ID deals 4 damage to that player."""
        self.g.battlefield('ichneumon-druid')
        self.g.mana('RR', owner=1)
        bolt = self.g.hand('lightning-bolt', owner=1)
        bolt_2 = self.g.hand('lightning-bolt', owner=1)
        self.g.cast_and_accept(bolt, 0, bolt.abilities[0], owner=1)
        self.g.cast_and_accept(bolt_2, 0, bolt_2.abilities[0], owner=1)
        self.assertEqual(16, self.gs.life[1])

    def test_icy_manipulator(self):
        """{1}, {T}: Tap target artifact, creature, or land."""

    def test_ice_storm(self):
        """Destroy target land."""

    def test_ifh_biff_efreet(self):
        """{G}: IBE deals 1 damage to each creature with flying & each player. Any player may activate this ability."""

    def test_immolation(self):
        """Enchant creature Enchanted creature gets +2/-2."""

    def test_in_the_eye_of_chaos(self):
        """Whenever a player casts an instant spell, counter it unless that player pays {X}, where X = its mana value"""
        self.g.battlefield('in-the-eye-of-chaos')
        self.g.mana('WWWWWWWWWW')
        instant = self.g.hand('swords-to-plowshares')
        creature = self.g.battlefield('grizzly-bears')

        instant_pipeline = AbilityPipeline(0, self.gs, instant, instant.abilities[0], targets=[creature])
        instant_pipeline.advance()
        pay_mana_to_not_have_countered = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_mana_to_not_have_countered)
        instant_pipeline.resolve_ability()
        self.assertIn(creature, self.gs.exiles[0])

        sorcery = self.g.hand('wrath-of-god')
        creature = self.g.battlefield('monss-goblin-raiders')
        sorcery_pipeline = AbilityPipeline(0, self.gs, sorcery, sorcery.abilities[0], targets=[creature])
        sorcery_pipeline.advance()
        self.assertFalse(self.gs.pending_choice)

    def test_indestructible_aura(self):
        """Prevent all damage that would be dealt to target creature this turn."""

    def test_infernal_medusa(self):
        """Whenever IM blocks a creature, destroy that creature at end of combat.
        Whenever IM becomes blocked by a non-Wall creature, destroy that creature at end of combat."""

    def test_inferno(self):
        """Inferno deals 6 damage to each creature and each player."""

    def test_infinite_authority(self):
        """Whenever host combats a creature with toughness <= 3, destroy the other creature at end of combat.
        At end step, if that creature was destroyed this way, put a +1/+1 counter on the first creature."""

    def test_instill_energy(self):
        """Enchanted creature can attack as though it had haste.
        {0}: Untap enchanted creature. Activate only during your turn and only once each turn."""
        host = self.g.battlefield('merfolk-of-the-pearl-trident')
        card = self.g.hand('instill-energy')
        self.g.cast_and_accept(card, host, card.abilities[0])
        give_haste_eff_spec = card.abilities[0]
        aa = card.activated_abilities[0]
        give_haste_eff_spec.effect.resolve(self.gs, card, host)
        self.assertTrue(self.gs.perm_querier.can_attack(host))

        card.tap()
        self.g.activate_ability(aa, host)
        self.assertFalse(host.is_tapped)

        card.tap()
        ability = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        self.assertFalse(ability.can_begin(), 'Should not be able to activate 2x in a turn')

    def test_invisibility(self):
        """Enchant creature Enchanted creature can't be blocked except by Walls."""

    def test_inquisition(self):
        """Target player reveals their hand. I deals damage = the number of white cards in their hand."""

    def test_invoke_prejudice(self):
        """Whenever an opponent casts a creature spell that DOESN'T SHARE A COLOR with a creature you control,
        counter that spell unless that player pays {X}, X = its mana value"""
        self.g.battlefield('invoke-prejudice')
        self.g.battlefield('grizzly-bears')
        self.g.battlefield('will-o-the-wisp')
        unaffected = self.g.hand('chromium', owner=1)  # WUB
        affected = self.g.hand('savannah-lions', owner=1)
        self.g.mana('WWWWUUUUBBBB', owner=1)

        unaffected_pipeline = AbilityPipeline(1, self.gs, unaffected, unaffected.abilities[0])
        unaffected_pipeline.advance()
        self.assertFalse(self.gs.pending_choice)
        unaffected_pipeline.resolve_ability()

        CastWithNoSpellEffect(1, self.gs, affected).play()
        self.assertTrue(self.gs.pending_choice.get_actions())

    def test_iron_star(self):
        """Whenever a player casts a red spell, you may pay {1}. If you do, you gain 1 life."""

    def test_ironclaw_orcs(self):
        """This creature can't block creatures with power 2 or greater."""

    def test_island_fish_jasconius(self):
        """Islandhome. IFJ doesn't untap during your untap step. At your upkeep, you may pay {UUU} to untap IFJ."""

    def test_island_of_wak_wak(self):
        """{T}: Target creature with flying has base power 0 until end of turn."""

    def test_island_sanctuary(self):
        """At your draw step, you may skip your draw and until your next turn,
        you can only be attacked by creatures with flying and/or islandwalk"""
        self.g.battlefield('island-sanctuary')
        illegal_attacker = self.g.battlefield('grizzly-bears', owner=1)
        legal_attacker = self.g.battlefield('scryb-sprites', owner=1)
        hand_len = len(self.gs.hands[0])

        self.g.next_turn()
        self.gs.event_mgr.emit(DrawStepEvent(0))
        self.assertEqual(hand_len, len(self.gs.hands[0]))
        skip_draw_and_gain_protection_action = self.gs.pending_choice.get_actions()[0]
        skip_draw_and_gain_protection_action.play()

        self.g.next_turn(True)
        self.assertTrue(self.gs.perm_querier.can_attack(legal_attacker))
        self.assertFalse(self.gs.perm_querier.can_attack(illegal_attacker))

        self.g.next_turn(True)
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        do_nothing_action = self.gs.pending_choice.get_actions()[1]
        do_nothing_action.play()
        self.assertEqual(8, len(self.gs.hands[0]))
        self.gs.hands[0].clear()

        self.g.next_turn(True)
        self.assertTrue(self.gs.perm_querier.can_attack(legal_attacker))
        self.assertTrue(self.gs.perm_querier.can_attack(illegal_attacker))

    def test_ivory_cup(self):
        """Whenever a player casts a white spell, you may pay {1}. If you do, you gain 1 life."""

    def test_ivory_guardians(self):
        """Creatures named Ivory Guardians get +1/+1 as long as an opponent controls a nontoken red permanent."""

    def test_ivory_tower(self):
        """At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4."""


if __name__ == '__main__':
    unittest.main()
