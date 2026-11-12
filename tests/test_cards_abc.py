import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import SelectXAction2
from models.actions.stack_accept_counter import PassPriority
from models.constants import KW, Zone
from models.cost import SacCardCost
from models.game_card.counter_tokens import PLUS_ONE_ZERO, PUPA, STORAGE, DOOM, WIND, STUN, SCREAM, MIRE, PLUS_ONE
from models.effects.listeners_misc import ArtifactPossessionActivation
from models.effects.resolvers_a_to_e import BloodLust
from models.events_all import AbilityActivatedEvent, CombatEndEvent, UpkeepEvent, DiscardStepEvent, StateBasedEvent, \
    DrawStepEvent
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestCardsAtoC(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_abomination(self):
        """Whenever A blocks or becomes blocked by a green or white creature, destroy that creature at end of combat."""
        card = self.g.battlefield('abomination')  # 2/6
        non_green_white = self.g.battlefield('juggernaut', owner=1)  # 5/3
        self.g.combat(card, non_green_white)
        self.assertNotIn(non_green_white, self.g.gy[1])

        self.g.next_turn(True)
        self.g.combat(non_green_white, card)
        self.assertNotIn(non_green_white, self.g.gy[1])

        self.g.next_turn(True)
        green = self.g.battlefield('war-mammoth', owner=1)  # 3/3
        self.g.combat(card, green)
        self.assertIn(green, self.g.gy[1])

    def test_abu_jafar(self):
        """When this creature dies, destroy all creatures blocking or blocked by it. They can't be regenerated."""
        card = self.g.battlefield('abu-jafar')  # 0/1
        blocker = self.g.battlefield('drudge-skeletons', owner=1)  # 1/1, {B}: Regenerate
        self.g.mana('B', owner=1)
        self.g.activate_ability(blocker.activated_abilities[0], blocker, 1)

        # despite abu-jafar having 0 power, its combatant is sent to the graveyard w its regeneration shield ignored
        com = self.gs.combat_mgr.create_combat(card)
        com.add_blocker(blocker)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertIn(blocker, self.g.gy[1])

        # test the negative condition; a creature besides abu-jafar allows the combatants regeneration
        self.g.next_turn()
        card = self.g.battlefield('monss-goblin-raiders')  # 1/1
        blocker = self.g.battlefield('drudge-skeletons', owner=1)  # 1/1, {B}: Regenerate
        self.g.mana('B', owner=1)
        self.g.activate_ability(blocker.activated_abilities[0], blocker, 1)

        com = self.gs.combat_mgr.create_combat(card)
        com.add_blocker(blocker)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertNotIn(blocker, self.g.gy[1])

    def test_acid_rain(self):
        """Destroy all Forests."""

    def test_active_volcano(self):
        """Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand."""

    def test_adun_oakenshield(self):
        """{BRG}, {T}: Return target creature card from your graveyard to your hand."""

    def test_aisling_leprechaun(self):
        """Whenever AL blocks or becomes blocked by a creature, that creature becomes green indefinitely"""

    def test_akron_legionnaire(self):
        """Except for creatures named AL and artifact creatures, creatures you control can't attack."""

    def test_al_abaras_carpet(self):
        """{5}, {T}: Prevent all damage that would be dealt to you this turn by attacking creatures without flying."""

    def test_alabaster_potion(self):
        """Choose 1 - * Target player gains X life. * Prevent the next X damage that would be dealt to any target EOT"""

    def test_aladdin(self):
        """{1RR}, {T}: Gain control of target artifact for as long as you control this creature."""

    def test_aladdins_lamp(self):
        """The next time you would draw a card this turn, instead look at the top X (X > 0) cards of your library,
        put all but one of them on the bottom of your library in a random order, then draw a card."""
        card = self.g.battlefield('aladdins-lamp')
        aa = card.activated_abilities[0]
        self.g.mana('UUU')
        c3 = self.g.library('savannah-lions')
        c2 = self.g.library('grizzly-bears')
        c1 = self.g.library('shivan-dragon')

        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, x_value=3)
        pipeline.advance()
        pipeline.resolve_ability()

        self.gs.phase_mgr.set_phase(Phase.DRAW)
        dragon_atop_lib = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(dragon_atop_lib)
        self.assertIn(c1, self.gs.hands[0])
        bottom_2_cards = self.gs.pile_mgr.libraries[0][-2:]
        self.assertIn(c2, bottom_2_cards)
        self.assertIn(c3, bottom_2_cards)

    def test_aladdins_ring(self):
        """{8}, {T}: This artifact deals 4 damage to any target."""

    def test_ali_baba(self):
        """{R}: Tap target Wall."""

    def test_ali_from_cairo(self):
        """Damage that would reduce your life total to less than 1 reduces it to 1 instead."""

    def test_alchors_tomb(self):
        """{2}, {T}: Target permanent you control becomes the color of your choice. (This effect lasts indefinitely.)"""

    def test_all_hallows_eve(self):
        """Exile AHE with 2 scream counters on it. At your upkeep, if this card is in exile with >=1 scream counters,
        remove a scream counter from it.
        If there's 0 scream counters, move it into your gy & all players' creatures from their gy to the battlefield."""
        card = self.g.hand('all-hallows-eve')
        creature_in_gy = self.g.graveyard('grizzly-bears')
        self.g.cast_and_accept(card, eff_spec=card.abilities[0])
        self.assertTrue(self.g.card_has_a_registered_listener(card))
        self.assertIn(card, self.gs.exiles[0])
        self.assertEqual(2, card.counters.get_count(SCREAM))

        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, card.counters.get_count(SCREAM))

        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(0, card.counters.get_count(SCREAM))
        self.assertIn(card, self.g.gy[0])
        self.assertIn(creature_in_gy, self.gs.boards[0])
        self.assertFalse(self.g.card_has_a_registered_listener(card))

    def test_amnesia(self):
        """Target player reveals their hand and discards all nonland cards."""

    def test_amrou_kithkin(self):
        """This creature can't be blocked by creatures with power 3 or greater."""

    def test_amulet_of_kroog(self):
        """{2}, {T}: Prevent the next 1 damage that would be dealt to any target this turn."""

    def test_ancestral_recall(self):
        """Target player draws three cards."""

    def test_angelic_voices(self):
        """Creatures you control get +1/+1 as long as you control no nonartifact, nonwhite creatures."""

    def test_angus_mackenzie(self):
        """{GWUT}: Prevent all combat damage that would be dealt EOT. Activate only before the combat damage step."""

    def test_angry_mob(self):
        """During your turn, AM's P & T are = 2 plus + Swamps your opponents control. On not your turn, AM is 2/2."""

    def test_animate_artifact(self):
        card = self.g.hand('animate-artifact')
        host = self.g.battlefield('sol-ring')
        self.g.mana('UUUU')
        self.g.cast_and_accept(card, host, card.abilities[0])
        self.assertTrue(self.g.card_has_a_registered_listener(card))
        self.assertEqual(1, host.power)

    def test_animate_dead(self):
        card = self.g.hand('animate-dead')
        target = self.g.battlefield('grizzly-bears')  # 2/2
        bolt = self.g.hand('lightning-bolt')
        self.g.mana('BBB')
        self.g.cast_and_accept(bolt, target, bolt.abilities[0])
        self.assertIn(target, self.g.gy[0])

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.targets.append(target)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertIn(target, self.gs.boards[0])
        self.assertEqual(1, target.power)  # -1/0

    def test_animate_wall(self):
        card = self.g.hand('animate-wall')
        host = self.g.battlefield('wall-of-brambles')

        self.g.next_turn()
        self.assertFalse(self.gs.perm_querier.can_attack(host))
        self.g.cast_and_accept(card, host, card.abilities[0])
        self.assertTrue(self.gs.perm_querier.can_attack(host))

    def test_ankh_of_mishra(self):
        """Whenever a land enters, this artifact deals 2 damage to that land's controller."""

    def test_anti_aura_magic(self):
        card = self.g.hand('anti-magic-aura')
        host = self.g.battlefield('grizzly-bears')
        legal_target = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.cast_and_accept(card, host, card.abilities[2])
        bolt = self.g.hand('lightning-bolt')
        self.assertTrue(self.gs.perm_querier.can_target(legal_target, bolt))
        self.assertFalse(self.gs.perm_querier.can_target(host, bolt))

    def test_apprentice_wizard(self):
        """{U}, {T}: Add {CCC}."""

    def test_arboria(self):
        """Creatures can't attack a player unless that player cast a spell or put a nontoken permanent onto
        the battlefield during their last turn."""

    def test_arcades_sabboth(self):
        """At your upkeep, sac AS unless you pay {GWU}. Each untapped non-attacking creature you control gets +0/+2.
        {W}: Arcades Sabboth gets +0/+1 until end of turn."""

    def test_arena_of_the_ancients(self):
        """Legendary creatures don't untap during their untap steps. When AOTA enters, tap all legendary creatures."""

    def test_argivian_archaeologist(self):
        """{WW}, {T}: Return target artifact card from your graveyard to your hand."""

    def test_argivian_blacksmith(self):
        """{T}: Prevent the next 2 damage that would be dealt to target artifact creature this turn."""

    def test_argothian_pixies(self):
        """AP can't be blocked by artifact creatures. Prevent all damage that would be dealt to AP by
        artifact creatures."""

    def test_argothian_treefolk(self):
        """Prevent all damage that would be dealt to this creature by artifact sources."""

    def test_armageddon(self):
        """Destroy all lands."""

    def test_armageddon_clock(self):
        """At your upkeep, put a doom counter on AC.
        At your draw step, AC deals damage = its doom counters to each player.
        {4}: Remove a doom counter from AC. Any player may activate this ability but only during any upkeep step."""
        card = self.g.battlefield('armageddon-clock')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertEqual(1, card.counters.get_count(DOOM))

        self.g.next_turn()
        self.gs.event_mgr.emit(DrawStepEvent(0))
        self.assertEqual([19, 19], self.gs.life)
        self.gs.event_mgr.emit(UpkeepEvent(0))

        self.g.next_turn()
        self.gs.event_mgr.emit(DrawStepEvent(0))
        self.assertEqual([17, 17], self.gs.life)
        self.g.mana('RRRR')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(0, self.gs.action_on_idx)
        self.assertTrue(any(a.source is card for a in self.gs.add_activated_abilities_from_board()))

        self.g.next_turn(True)
        self.g.mana('WWWW', owner=1)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, self.gs.action_on_idx)
        self.assertTrue(any(a.source is card for a in self.gs.add_activated_abilities_from_board()))

    def test_army_of_allah(self):
        """Attacking creatures get +2/+0 until end of turn."""

    def test_artifact_blast(self):
        """Counter target artifact spell."""

    def test_artifact_possession(self):
        """Whenever enchanted artifact becomes tapped or a player activates an ability of enchanted artifact without {T}
        in its activation cost, this Aura deals 2 damage to that artifact's controller."""
        artifact = self.g.battlefield('barls-cage')  # Activated('3', ...)
        aura = self.g.card('artifact-possession')
        aura.host = artifact
        listener = ArtifactPossessionActivation()
        self.gs.event_mgr.register(listener, aura)
        aa = artifact.activated_abilities[0]
        self.gs.event_mgr.emit(AbilityActivatedEvent(0, aa))
        self.assertEqual(self.gs.life[0], 18)

    def test_artifact_ward(self):
        """Host can't be the target of abilities from artifact sources"""
        card = self.g.hand('artifact-ward')
        host = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.cast_and_accept(card, host, card.abilities[0])

        legal_target = self.g.battlefield('air-elemental')
        artifact = self.g.battlefield('icy-manipulator', owner=1)
        self.g.mana('UUUUUU', owner=1)
        self.assertFalse(self.gs.perm_querier.can_target(host, artifact))
        self.assertTrue(self.gs.perm_querier.can_target(legal_target, artifact))

    def test_ashes_to_ashes(self):
        """Exile two target nonartifact creatures. Ashes to Ashes deals 5 damage to you."""
        card = self.g.hand('ashes-to-ashes')
        self.g.mana('BBBB')
        t1 = self.g.battlefield('grizzly-bears', owner=1)
        t2 = self.g.battlefield('scryb-sprites', owner=1)
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[t1, t2])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(15, self.gs.life[0])
        self.assertIn(t1, self.gs.exiles[1])
        self.assertIn(t2, self.gs.exiles[1])

    def test_ashnods_altar(self):
        """Sacrifice a creature: Add {CC}."""

    def test_ashnods_battle_gear(self):
        """You may choose not to untap ABG during your untap step.
        {2}, {T}: Target creature you control gets +2/-2 for as long as ABG remains tapped."""

    def test_ashnods_transmogrant(self):
        """{T}, Sacrifice AT Put a +1/+1 counter on target nonartifact creature.
        That creature becomes an artifact in addition to its other types."""

    def test_aspect_of_wolf(self):
        """Host gets +X/+Y, X = your forest count // 2, Y = roundup(the number of Forests you control / 2)"""

    def test_atog(self):
        """Sacrifice an artifact: This creature gets +2/+2 until end of turn."""

    def test_avoid_fate(self):
        """Counter target instant or Aura spell that targets a permanent you control."""

    def test_axelrod_gunnarson(self):
        """Whenever a creature dealt damage by AG dies EOT, you gain 1 life & AG deals 1 damage to target player"""

    def test_backdraft(self):
        """Choose a player who cast one or more sorcery spells this turn. B deals damage to that player =
        1/2 damage (rounded down) dealt by one of those sorceries."""
        self.gs.hands[0].clear()
        self.g.mana('RR')
        self.g.mana('RRRR', owner=1)
        card = self.g.hand('backdraft')

        # not castable; no one has played a sorcery this turn
        self.gs.action_on_idx = 0
        castable_cards = {a.source for a in self.gs.available_actions_from_hand() if isinstance(a, AbilityPipeline)}
        self.assertNotIn(card, castable_cards)

        self.g.next_turn(True)

        # Player #1 deals 4 damage via sorcery (and 2 to itself)
        s1 = self.g.hand('eternal-flame', owner=1)
        self.g.cast_and_accept(s1, 0, s1.abilities[0], 1, False)
        self.assertEqual([16, 18], self.gs.life)

        # Player #1 deals 9 damage via sorcery (and 5 to itself)
        s2 = self.g.hand('eternal-flame', owner=1)
        self.g.mana('RRRRR', owner=1)
        self.g.cast_and_accept(s2, 0, s2.abilities[0], 1, False)
        self.assertEqual([7, 13], self.gs.life)

        # force the action back onto P# 0
        self.gs.action_on_idx = 0

        # spell is now castable
        castable_cards = {a.source for a in self.gs.available_actions_from_hand()}
        self.assertIn(card, castable_cards)

        # cast Backdraft
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[1])
        pipeline.advance()
        pipeline.resolve_ability()

        # options are to deal 4//2 or 9//2 damage to Player #1 (the options are sorted by p_id, damage); deal 9//2
        deal_4_damage = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(deal_4_damage)
        self.assertEqual([7, 9], self.gs.life)

    def test_backfire(self):
        """Whenever host deals damage to you, this Aura deals that much damage to that creature's controller."""

    def test_bad_moon(self):
        """Black creatures get +1/+1."""

    def test_badlands(self):
        """({T}: Add {B} or {R}.)u003c/iu003e"""

    def test_balance(self):
        """The player who owns more lands must sac lands down to the count owned by the player with the fewest;
        Discard in the same manner for cards in hand; sac in the same manner for creatures;
        If a player has no cards in that cat, all are disposed; if the players are tied, move to the next category"""
        [h.clear() for h in self.gs.hands]

        # Lands: [3, 1]; Hand: [0, 1]; Creatures: [1, 1]
        bears = self.g.hand('grizzly-bears', owner=1)
        swamp = self.g.battlefield('swamp')
        mountain = self.g.battlefield('mountain')
        plains = self.g.battlefield('plains')
        self.g.mana('BRW')
        self.g.mana('G', owner=1)
        self.g.battlefield('savannah-lions')
        self.g.battlefield('scryb-sprites', owner=1)

        card = self.g.hand('balance')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertNotIn(card, self.gs.hands[0])

        keep_swamp = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(keep_swamp)
        self.assertIn(swamp, self.gs.boards[0])
        self.assertIn(mountain, self.g.gy[0])
        self.assertIn(plains, self.g.gy[0])

        self.assertEqual(0, len(self.gs.hands[0]))

        self.assertNotIn(bears, self.gs.hands[1])
        self.assertIsNone(self.gs.pending_choice)

    def test_ball_lightning(self):
        """At the beginning of the end step, sac BL."""

    def test_banshee(self):
        """{X}, {T}: B deals X//2 to any target & roundup(X/2) to you."""

    def test_barls_cage(self):
        """{3}: Tap & add a stun counter to target creature"""
        card = self.g.battlefield('barls-cage')
        self.g.mana('UUU')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('scryb-sprites', owner=1)
        self.g.activate_ability(aa, target)
        self.assertTrue(target.is_tapped)
        self.assertEqual(1, target.counters.get_count(STUN))

    def test_bartel_runeaxe(self):
        """Vigilance Bartel Runeaxe can't be the target of Aura spells."""

    def test_basalt_monolith(self):
        """This artifact doesn't untap during your untap step. {T}: Add {CCC}. {3}: Untap this artifact."""

    def test_bayou(self):
        """({T}: Add {B} or {G}.)u003c/iu003e"""

    def test_bazaar_of_baghdad(self):
        """{T}: Draw two cards, then discard three cards."""

    def test_beasts_of_bogardan(self):
        """Protection from red This creature gets +1/+1 as long as an opponent controls a nontoken white permanent."""

    def test_berserk(self):
        """Cast this spell only before the combat damage step. Target creature gains trample and gets +X/+0 EOT,
        where X is its power. At end step, destroy that creature if it attacked this turn."""
        self.gs.hands[0].clear()
        card = self.g.hand('berserk')
        target = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.mana('GGG')
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.assertFalse(any(a for a in self.gs.available_actions_from_hand()
                         if isinstance(a, AbilityPipeline) and a.source is card))

        self.g.next_turn()
        card.abilities[0].effect.resolve(self.gs, card, target)
        self.g.combat(target, None)
        self.assertEqual(16, self.gs.life[1])
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.assertIn(target, self.g.gy[0])

    def test_birds_of_paradise(self):
        """Flying {T}: Add one mana of any color."""

    def test_black_lotus(self):
        """{T}, Sacrifice this artifact: Add three mana of any one color."""

    def test_black_mana_battery(self):
        """{2}, {T}: Put a charge counter on BMB.
        {T}, Remove X charge counters from BMB: Add {B}, then add {B} * X"""

    def test_black_vise(self):
        """As opponent's upkeep, this artifact deals X damage to that player, X is = cards in their hand minus 4"""
        card = self.g.battlefield('black-vise')
        self.g.next_turn(True)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(17, self.gs.life[1])

    def test_black_ward(self):
        """Enchant creature Enchanted creature has protection from black. This effect doesn't remove this Aura."""

    def test_blazing_effigy(self):
        """When BE dies, it deals X damage to target creature.
        X = 3 + the amount of damage dealt to BE this turn by other sources named 'Blazing Effigy'."""
        card = self.g.battlefield('blazing-effigy')
        be2 = self.g.battlefield('blazing-effigy')
        target = self.g.battlefield('craw-wurm')  # 6/4
        self.gs.apply_damage(be2, 1, card)
        self.gs.pile_mgr.destroy(card)
        deal_4_damage_to_craw_wurm = self.gs.pending_choice.get_actions()[2]
        deal_4_damage_to_craw_wurm.play()
        self.assertIn(target, self.g.gy[0])

    def test_blessing(self):
        """Enchant creature {W}: Enchanted creature gets +1/+1 until end of turn."""

    def test_blight(self):
        """Enchant land When enchanted land becomes tapped, destroy it."""
        
    def test_blood_lust(self):
        """If target creature has toughness 5 or greater, it gets +4/-4 until end of turn.
        Otherwise, it gets +4/-X until end of turn, where X is its toughness minus 1."""
        large_creature = self.g.battlefield('bartel-runeaxe')  # 6/5
        small_creature = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        blood_lust = self.g.card('blood-lust', 1)
        BloodLust().resolve(self.gs, blood_lust, large_creature)
        BloodLust().resolve(self.gs, blood_lust, small_creature)
        self.assertEqual(large_creature.power, 10)
        self.assertEqual(large_creature.toughness, 1)
        self.assertEqual(small_creature.power, 5)
        self.assertEqual(small_creature.toughness, 1)

    def test_blood_moon(self):
        """Nonbasic lands are Mountains."""

    def test_blood_of_the_martyr(self):
        """EOT, if damage would be dealt to any creature, you may have that damage dealt to you instead."""

    def test_blue_elemental_blast(self):
        """Choose one - * Counter target red spell. * Destroy target red permanent."""

    def test_blue_mana_battery(self):
        """{2}, {T}: Put a charge counter on BMB.
        {T}, Remove X charge counters from BMB: Add {U}, then add {U} * X"""
    def test_blue_ward(self):
        """Enchant creature Enchanted creature has protection from blue. This effect doesn't remove this Aura."""

    def test_bog_rats(self):
        """This creature can't be blocked by Walls."""

    def test_bone_flute(self):
        """2T: All creatures get -1/-0 until end of turn"""
        creature = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        card = self.g.battlefield('bone-flute')
        aa = card.activated_abilities[0]
        self.g.mana('RRRR')
        self.g.activate_ability(aa)
        self.assertEqual(0, creature.power)

        self.g.next_turn()
        self.assertEqual(1, creature.power)

    def test_book_of_rass(self):
        """Draw a card for 2 damage"""
        self.gs.hands[0].clear()
        self.g.mana('UUUUUUUU')
        card = self.g.battlefield('book-of-rass')
        aa = card.activated_abilities[0]
        self.g.activate_ability(aa)
        self.assertEqual(1, len(self.gs.hands[0]))
        self.assertEqual(18, self.gs.life[0])

    def test_boomerang(self):
        """Return target permanent to its owner's hand."""

    def test_boris_devilboon(self):
        """{2BR}, {T}: Create a 1/1 black and red Demon creature token named Minor Demon."""

    def test_bottle_of_suleiman(self):
        """{1}, sac BOM: Flip a coin. If you win the flip, create a 5/5 colorless Djinn flying artifact creature.
        If you lose the flip, this artifact deals 5 damage to you."""

    def test_braingeyser(self):
        """Target player draws X cards."""

    def test_brainwash(self):
        """Enchant creature Enchanted creature can't attack unless its controller pays {3}."""

    def test_brass_man(self):
        """This creature doesn't untap during your untap step. At your upkeep, you may pay {1} to untap BM."""

    def test_brine_hag(self):
        """When BH dies, change base PT of all creatures that dealt damage to it this turn to 0/2 for as long as that
        creature remains on the battlefield; State-based rules do evaluate & the creature will almost definitely die"""
        card = self.g.battlefield('brine-hag')  # 2/2
        creature = self.g.battlefield('craw-wurm', owner=1)  # 6/4

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(creature)
        self.gs.combat_mgr.add_blocker(creature, card)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertIn(creature, self.g.gy[1])

        card = self.g.battlefield('brine-hag')  # new brine-hag; last one wnet to the graveyard
        self.g.next_turn()
        globally_pumped_creature = self.g.battlefield('savannah-lions', owner=1)  # 2/1
        self.g.battlefield('crusade')
        self.g.battlefield('crusade')  # savannah-lions should now be 4/3
        self.gs.combat_mgr.create_combat(globally_pumped_creature)
        self.gs.combat_mgr.add_blocker(globally_pumped_creature, card)
        self.gs.combat_mgr.handle_damage_step(False)  # savannah-lions should now be (0/2) +1/+1 +1/+1 = 2/4
        self.assertIn(card, self.g.gy[0])
        self.assertEqual((2, 4), (globally_pumped_creature.power, globally_pumped_creature.toughness))
        self.assertIn(globally_pumped_creature, self.gs.boards[1])

    def test_bronze_horse(self):
        """If you control another creature, prevent all damage that would be dealt to BH by spells that target it"""
        # WARNING: this is a shortcut for "is the source a spell", since DamageProposedEvent doesn't carry eff_spec
        # This incorrectly handles instants/sorceries that deal damage w/o targeting
        card = self.g.battlefield('bronze-horse')  # 4/4
        bolt_1 = self.g.hand('lightning-bolt')

        self.g.cast_and_accept(bolt_1, card, eff_spec=bolt_1.abilities[0])  # BH's ability is off
        self.assertEqual(3, card.damage_received_this_turn)

        self.g.battlefield('grizzly-bears')  # BH's ability is on
        bolt_2 = self.g.hand('lightning-bolt')
        self.g.cast_and_accept(bolt_2, card, eff_spec=bolt_2.abilities[0])
        self.assertEqual(3, card.damage_received_this_turn)

        prodigal = self.g.battlefield('prodigal-sorcerer')
        aa = prodigal.activated_abilities[0]
        self.g.activate_ability(aa, card)  # BH's ability only covers spells not AAs
        self.assertIn(card, self.g.gy[0])

    def test_brothers_of_fire(self):
        """{1RR}: This creature deals 1 damage to any target and 1 damage to you."""

    def test_burrowing(self):
        """Host has mountainwalk"""

    def test_candelabra_of_tawnos(self):
        """{X}, {T}: Untap X target lands"""
        card = self.g.battlefield('candelabra-of-tawnos')
        aa = card.activated_abilities[0]
        swamp = self.g.battlefield('swamp')
        forest = self.g.battlefield('forest')
        self.assertFalse(aa.eff_spec.target_spec.get_targets(self.gs, card))
        swamp.tap()
        forest.tap()
        self.assertEqual(2, len(aa.eff_spec.target_spec.get_targets(self.gs, card)))

        self.g.battlefield('mountain')
        plains = self.g.battlefield('plains')
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        pipeline.x_value = 2
        pipeline.targets.append(swamp)
        pipeline.targets.append(forest)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertFalse(swamp.is_tapped)
        self.assertTrue(plains.is_tapped)

        self.g.next_turn()
        self.assertEqual(0, len(aa.eff_spec.target_spec.get_targets(self.gs, card)))

    def test_carrion_ants(self):
        """{1}: This creature gets +1/+1 until end of turn."""

    def test_castle(self):
        """Untapped creatures you control get +0/+2."""

    def test_cave_people(self):
        """Whenever this creature attacks, it gets +1/-2 until end of turn ..."""
        card = self.g.battlefield('cave-people')  # 1/4

        self.g.next_turn()
        self.gs.combat_mgr.create_combat(card)
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS)
        self.assertEqual(2, card.power)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS)
        self.assertEqual(1, card.power)

    def test_caverns_of_despair(self):
        """No more than two creatures can attack each combat. No more than two creatures can block each combat."""
        self.g.battlefield('caverns-of-despair')
        a1 = self.g.battlefield('scryb-sprites')
        a2 = self.g.battlefield('savannah-lions')
        a3 = self.g.battlefield('tundra-wolves')

        self.g.next_turn()
        self.gs.combat_mgr.create_combat(a1)
        self.assertTrue(self.gs.perm_querier.can_attack(a2))
        self.gs.combat_mgr.create_combat(a2)
        self.assertFalse(self.gs.perm_querier.can_attack(a3))

    def test_celestial_prism(self):
        """{2}, {T}: Add one mana of any color."""

    def test_chaos_orb(self):
        """{1}, {T}: If CO is on the battlefield, flip it onto the battlefield from a height of at least one foot.
        If CO turns over completely at least once during the flip, destroy all nontoken permanents it touches.
        Then destroy this artifact."""

    def test_chain_lightning_last_player_declines_copy(self):
        """CL deals 3 damage to any target. Then that player/target's owner may pay {RR}.
        If the player does, they may copy this spell and may choose a new target for that copy."""
        self.g.mana('RRRR')
        self.g.mana('RRRR', owner=1)
        card = self.g.hand('chain-lightning')

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[1])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(17, self.gs.life[1])
        self.assertEqual(1, self.gs.action_on_idx)

        pay_and_copy = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_and_copy)
        damage_p0 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(damage_p0)
        self.assertEqual(17, self.gs.life[0])

        pay_and_copy = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_and_copy)
        damage_p1 = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(damage_p1)
        self.assertEqual(14, self.gs.life[1])

        decline_pay_and_copy = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(decline_pay_and_copy)
        self.assertIsNone(self.gs.pending_choice)

    def test_chain_lightning_last_player_cant_pay(self):
        """CL deals 3 damage to any target. Then that player/target's owner may pay {RR}.
        If the player does, they may copy this spell and may choose a new target for that copy."""
        self.g.mana('RRRR')
        card = self.g.hand('chain-lightning')

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[1])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(17, self.gs.life[1])
        self.assertEqual(1, self.gs.action_on_idx)
        self.assertIsNone(self.gs.pending_choice)

    def test_chains_of_mephistopheles(self):
        """If a player would draw a 2nd card in a turn ... If no cards in hand, mill; else, discard then draw."""
        self.gs.hands[0].clear()
        self.g.battlefield('chains-of-mephistopheles')

        self.g.next_turn()
        island = self.g.library('island')
        self.gs.pile_mgr.draw(0)
        self.g.cast_and_accept(island)

        # hand is empty; mill a card
        swamp = self.g.library('swamp')
        self.gs.pile_mgr.draw(0)
        self.assertIn(swamp, self.g.gy[0])

        # hand is not empty; discard then draw
        self.g.next_turn()
        mountain = self.g.library('mountain')
        _ = self.g.library('plains')
        forest = self.g.library('forest')
        self.gs.pile_mgr.move_card(forest, Zone.HAND, cause='setting_up_the_test', emit_zone_event=False)
        self.gs.pile_mgr.draw(0)  # now forest & plains in hand
        self.gs.pile_mgr.draw(0)  # this attempt to draw mountain should emit to the Listener & create a pending_choice
        discard_forest = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(discard_forest)
        self.assertIn(forest, self.g.gy[0])
        self.assertIn(mountain, self.gs.hands[0])

    def test_channel(self):
        """Until EOT, any time you could activate a mana ability, you may: pay 1 life: add {C}"""
        self.gs.hands[0].clear()
        self.g.mana('GG')
        self.gs.phase_mgr.set_phase(Phase.MAIN)

        card = self.g.hand('channel')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.advance()
        PassPriority(1, self.gs).play()
        PassPriority(0, self.gs).play()

        self.assertIn(card, [em.source for em in self.gs.emblem_mgr.emblems])
        activate_channel = self.gs.get_available_actions(0)[-1]
        activate_channel.play()
        PassPriority(1, self.gs).play()
        PassPriority(0, self.gs).play()
        self.assertEqual(1, self.gs.mana_pools[0].available_mana['C'])
        self.assertEqual(19, self.gs.life[0], "Where are costs paid in Action.play()?")

    def test_chaoslace(self):
        """Target spell or permanent becomes red. (Its mana symbols remain unchanged.)"""

    def test_chromium(self):
        """At your upkeep, sac C unless you pay {WUB}."""

    def test_circle_of_protection_artifacts(self):
        """{2}: The next time an artifact source of your choice would deal damage to you EOT, prevent that damage."""

    def test_circle_of_protection_black(self):
        """{1}: The next time a black source of your choice would deal damage to you EOT, prevent that damage."""

    def test_circle_of_protection_blue(self):
        """{1}: The next time a blue source of your choice would deal damage to you EOT, prevent that damage."""

    def test_circle_of_protection_green(self):
        """{1}: The next time a green source of your choice would deal damage to you EOT, prevent that damage."""

    def test_circle_of_protection_red(self):
        """{1}: The next time a red source of your choice would deal damage to you EOT, prevent that damage."""

    def test_circle_of_protection_white(self):
        """{1}: The next time a white source of your choice would deal damage to you EOT, prevent that damage."""

    def test_citanul_druid(self):
        """Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature."""

    def test_city_in_a_bottle(self):
        """Whenever a nontoken permanent with a name originally printed in Arabian Nights is on battlefield, sac it"""
        an_card = self.g.battlefield('serendib-efreet')
        card = self.g.hand('city-in-a-bottle')
        self.g.cast_and_accept(card, None, card.abilities[2])
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertNotIn(an_card, self.gs.boards[0])

    def test_city_of_brass(self):
        """Whenever this land becomes tapped, it deals 1 damage to you. {T}: Add one mana of any color."""

    def test_city_of_shadows(self):
        """{T}, Exile a creature you control: Put a storage counter COS.
        {T}: Add {C} * storage counters on SOC."""
        card = self.g.battlefield('city-of-shadows')
        aa2 = card.activated_abilities[1]
        self.assertFalse(aa2.eff_spec.effect.can_activate(self.gs, card))  # type: ignore

        aa1 = card.activated_abilities[0]
        creature = self.g.battlefield('savannah-lions')
        pipeline = AbilityPipeline(0, self.gs, card, aa1.eff_spec,
                                   selected_extra_costs=[SacCardCost(selected_card=creature)])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(1, card.counters.get_count(STORAGE))
        self.assertIn(creature, self.g.gy[0])

        self.g.next_turn()
        self.g.activate_ability(aa2)
        self.assertEqual(1, self.gs.mana_pools[0].available_mana.get('C'))

    def test_clay_statue(self):
        """{2}: Regenerate this creature."""

    def test_cleanse(self):
        """Destroy all black creatures."""

    def test_cleansing(self):
        """For each land, destroy that land unless any player pays 1 life."""

    def test_clergy_of_the_holy_nimbus(self):
        """If COTN would be destroyed, regenerate it.
        {1}: COTN can't be regenerated this turn. Only your opponents may activate this ability."""
        card = self.g.battlefield('clergy-of-the-holy-nimbus')
        self.gs.pile_mgr.destroy(card)
        self.assertIn(card, self.gs.boards[0])

        self.gs.pile_mgr.destroy(card, allow_regeneration=False)
        self.assertIn(card, self.g.gy[0])

        card = self.g.battlefield('clergy-of-the-holy-nimbus')
        aa = card.activated_abilities[0]
        self.g.next_turn(True)
        self.g.mana('G', owner=1)
        self.g.activate_ability(aa, card, owner=1)
        self.gs.pile_mgr.destroy(card)
        self.assertIn(card, self.g.gy[0])

    def test_clockwork_avian(self):
        """CA enters with four +1/+0 counters. At combat end, if CA attacked or blocked, remove a +1/+0 counter from it.
        {X}, {T}: Put up to X +1/+0 counters on CA. Can't exceed 4 such counters. Activate only during your upkeep."""
        card = self.g.battlefield('clockwork-avian')
        self.g.resolve_spell(card, card)
        aa = card.activated_abilities[0]
        self.assertEqual(4, card.counters.get_count(PLUS_ONE_ZERO))
        self.g.mana('UUUUUUUU')

        for i in range(1, 3):
            self.g.next_turn()
            self.g.combat(card, None)
            self.gs.event_mgr.emit(CombatEndEvent(0))
            self.assertEqual(4 - i, card.counters.get_count(PLUS_ONE_ZERO))

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        pipeline.advance()
        x_options_cnt = len([a for a in self.gs.pending_choice.get_actions() if isinstance(a, SelectXAction2)])
        self.assertEqual(2, x_options_cnt, "Should only be able to activate for X=1 or X=2, due to counter cap of 4")

    def test_clockwork_beast(self):
        """CA enters with 7 +1/+0 counters. At combat end, if CA attacked or blocked, remove a +1/+0 counter from it.
        {X}, {T}: Put up to X +1/+0 counters on CB. Can't exceed 7 such counters. Activate only during your upkeep."""
        card = self.g.battlefield('clockwork-beast')
        self.g.resolve_spell(card, card)
        aa = card.activated_abilities[0]
        self.assertEqual(7, card.counters.get_count(PLUS_ONE_ZERO))
        self.g.mana('UUUUUUUU')

        for i in range(1, 4):
            self.g.next_turn()
            self.g.combat(card, None)
            self.gs.event_mgr.emit(CombatEndEvent(0))
            self.assertEqual(7 - i, card.counters.get_count(PLUS_ONE_ZERO))

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        pipeline.advance()
        x_options_cnt = len([a for a in self.gs.pending_choice.get_actions() if isinstance(a, SelectXAction2)])
        self.assertEqual(3, x_options_cnt, "Should only be able to activate for X=1, 2, or 3, due to counter cap of 7")

    def test_clone(self):
        """You may have this creature enter as a copy of any creature on the battlefield."""

    def test_coal_golem(self):
        """{3}, Sacrifice this creature: Add {RRR}."""

    def test_cockatrice(self):
        """Whenever C blocks or becomes blocked by a non-Wall creature, destroy that creature at end of combat."""

    def test_cocoon(self):
        """Enchant creature you control. When this Aura enters, tap host & put 3 pupa counters on C.
        Host doesn't untap during your untap step if C has a pupa counter on it.
        At your upkeep, remove a pupa counter from C.
        If you can't, sac C, put a +1/+1 counter on host & host gains flying."""
        card = self.g.hand('cocoon')
        host = self.g.battlefield('savannah-lions')  # 2/1
        self.g.mana('GGG')
        self.g.cast_and_accept(card, host, card.abilities[0])
        self.assertTrue(host.is_tapped)
        self.assertEqual(3, card.counters.get_count(PUPA))

        for i in range(1, 4):
            self.g.next_turn()
            self.gs.event_mgr.emit(UpkeepEvent(0))
            self.assertEqual(3 - i, card.counters.get_count(PUPA))
            self.assertTrue(host.is_tapped)

        self.g.next_turn()
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertIn(card, self.g.gy[0])
        self.assertEqual(3, host.power)
        self.assertIn(KW.FLYING, host.keyword_abilities)

    def test_colossus_of_sardia(self):
        """COS doesn't untap during your untap step. {9}: Untap this creature. Activate only during your upkeep."""

    def test_concordant_crossroads(self):
        """All creatures have haste"""
        creature = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.assertFalse(self.gs.perm_querier.can_attack(creature))
        self.g.battlefield('concordant-crossroads')
        self.assertTrue(self.gs.perm_querier.can_attack(creature))

    def test_consecrate_land(self):
        """Host has indestructible and can't be enchanted by other Auras"""
        card = self.g.hand('consecrate-land')
        host = self.g.battlefield('island')
        unprotected_land = self.g.battlefield('swamp')
        self.g.mana('W')

        ap = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[host])
        ap.advance()
        ap.resolve_ability()

        phantasmal_terrain = self.g.card('phantasmal-terrain')
        targets = phantasmal_terrain.abilities[0].target_spec.get_targets(self.gs, phantasmal_terrain)
        self.assertIn(unprotected_land, targets)
        self.assertNotIn(host, targets)

        stone_rain = self.g.card('stone-rain')
        stone_rain.abilities[0].effect.resolve(self.gs, stone_rain, host)
        self.assertNotIn(host, self.g.gy[0])

        stone_rain.abilities[0].effect.resolve(self.gs, stone_rain, unprotected_land)
        self.assertIn(unprotected_land, self.g.gy[0])

    def test_conservator(self):
        """{3}, {T}: Prevent the next 2 damage that would be dealt to you this turn."""

    def test_control_magic(self):
        """Enchant creature You control enchanted creature."""

    def test_conversion(self):
        """At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}. All Mountains are Plains."""

    def test_copper_tablet(self):
        """At the beginning of each player's upkeep, this artifact deals 1 damage to that player."""

    def test_copy_artifact(self):
        """You may have CA enter as a copy of any artifact on the battlefield,
        except it's an enchantment in addition to its other types."""

    def test_coral_helm(self):
        """{3}, Discard a card at random: Target creature gets +2/+2 until end of turn."""

    def test_cosmic_horror(self):
        """At your upkeep, destroy CH unless you pay {3BBB}. If CH is destroyed this way, it deals 7 damage to you."""

    def test_counterspell(self):
        """Counter target spell."""

    def test_crevasse(self):
        """Creatures with mountainwalk can be blocked as though they didn't have mountainwalk."""

    # def test_creature_bond(self):
    #     """When host dies, this Aura deals damage equal to that creature's toughness to the creature's controller."""
    #     # TODO: By the time CreatureBond.on_event() is called, the source.host is None;
    #     #  I'm guessing the aura is detached already
    #     host = get_card(self.gs, 'merfolk-of-the-pearl-trident', 0)  # 1/1
    #     creature_bond = get_card(self.gs, 'creature-bond', 1)
    #     host.auras.append(creature_bond)
    #     self.gs.event_mgr.register(creature_bond.abilities[0].effect, creature_bond)
    #     self.gs.pile_mgr.destroy(host)
    #     self.assertEqual(self.gs.life[0], 19)

    def test_crimson_manticore(self):
        """Flying {R}, {T}: This creature deals 1 damage to target attacking or blocking creature."""

    def test_crumble(self):
        """Destroy target artifact. It can't be regenerated. That artifact's controller gains life = its MV."""
        card = self.g.card('crumble')
        target = self.g.battlefield('colossus-of-sardia', owner=1)  # MV = 9
        self.g.cast_and_accept(card, target, card.abilities[0])
        self.assertEqual(29, self.gs.life[1])

    def test_crusade(self):
        """White creatures get +1/+1."""

    def test_crystal_rod(self):
        """Whenever a player casts a blue spell, you may pay {1}. If you do, you gain 1 life."""

    def test_cuombajj_witches(self):
        """{T}: CW deals 1 damage to any target and 1 damage to any target of an opponent's choice."""
        card = self.g.battlefield('cuombajj-witches')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('savannah-lions', owner=1)
        self.g.activate_ability(aa, target)
        self.assertIn(target, self.g.gy[1])
        print('-------------')
        print(self.gs.action_on_idx)
        print(self.gs.pending_choice.get_actions())
        deal_1_damage_to_play_0 = self.gs.pending_choice.get_actions()[1]
        deal_1_damage_to_play_0.play()
        self.assertEqual(19, self.gs.life[0])

    def test_curse_artifact(self):
        """At host controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
        card = self.g.hand('curse-artifact')
        self.g.mana('BBBB')
        target = self.g.battlefield('sol-ring', owner=1)

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[target])
        pipeline.advance()
        pipeline.resolve_ability()

        self.g.next_turn(True)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        take_2_damage = self.gs.pending_choice.get_actions()[0]
        take_2_damage.play()
        self.assertEqual(18, self.gs.life[1])

    def test_cursed_land(self):
        """At host's upkeep, this Aura deals 1 damage to that player."""

    def test_cursed_rack(self):
        """Opponent's maximum hand size is four [at their discard phase]"""
        self.g.battlefield('cursed-rack')
        opp_hand = self.gs.hands[1]
        opp_hand.pop()
        self.assertTrue(len(opp_hand) == 6)
        self.g.next_turn(True)
        self.gs.event_mgr.emit(DiscardStepEvent(1))
        self.assertEqual(15, len(self.gs.pending_choice.get_actions()))  # 6 card hand x 2 selections = 15 combos

    def test_cyclone(self):
        """At your upkeep, add a wind counter, then pay {G} for each wind counter on it or sac.
        If you pay, Cyclone deals damage = its wind counters to each creature and each player."""
        card = self.g.battlefield('cyclone')
        forest = self.g.battlefield('forest')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, card.counters.get_count(WIND))

        pay_g_to_deal_damage = self.gs.pending_choice.get_actions()[0]
        pay_g_to_deal_damage.play()
        self.assertEqual(19, self.gs.life[0])

        self.g.next_turn()
        self.gs.pile_mgr.destroy(forest)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertIn(card, self.g.gy[0])

    def test_cyclopean_mummy(self):
        """When this creature dies, exile it."""

    def test_cyclopean_tomb(self):
        """Put a mire counter on target non-Swamp land; it's a Swamp for as long as it has a mire counter on it ...
        When CT is put into a graveyard from the battlefield: At of each of your upkeeps for the rest of the game,
        remove all mire counters from a land that this card placed a mire counter on"""
        card = self.g.battlefield('cyclopean-tomb')
        aa = card.activated_abilities[0]
        self.g.mana('BBBB')
        t1 = self.g.battlefield('maze-of-ith', owner=1)
        t2 = self.g.battlefield('island', owner=1)

        self.g.activate_ability(aa, t1)
        self.g.activate_ability(aa, t2)
        self.assertTrue(t1.counters.get_count(MIRE))
        self.assertTrue(t2.counters.get_count(MIRE))

        self.gs.pile_mgr.destroy(card)
        self.assertTrue(self.g.card_has_a_registered_listener(card))

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        remove_mires_from_one_land = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(remove_mires_from_one_land)
        self.assertEqual(1, t1.counters.get_count(MIRE) + t2.counters.get_count(MIRE))

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        remove_mires_from_one_land = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(remove_mires_from_one_land)
        self.assertEqual(0, t1.counters.get_count(MIRE) + t2.counters.get_count(MIRE))

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertFalse(self.g.card_has_a_registered_listener(card))


if __name__ == '__main__':
    unittest.main()
