from models.effects.combat import islandhome_can_attack_effect, amrou_kithkin_can_be_blocked, \
        artifact_ward_can_be_blocked, argothian_pixies_can_be_blocked, bog_rats_can_be_blocked, \
        elder_spawn_can_be_blocked, elven_riders_can_be_blocked, evil_eye_of_orms_by_gore_can_be_blocked, \
        seeker_enchanted_creature_can_be_blocked, akron_legionnaire_on_leave, evil_eye_of_orms_by_gore_on_leave
from models.effects.counters import remove_plus_one_zero, scavenging_ghoul_on_end_step, spirit_shackle_on_tap, \
        fungusaur_on_damage, living_artifact_on_damage, fasting_on_upkeep, primordial_ooze_on_upkeep, \
        unstable_mutation_on_upkeep, venarian_gold_on_upkeep, voodoo_doll_on_upkeep, clockwork_avian_on_cast, \
        clockwork_beast_on_cast, cocoon_on_cast, tetravus_and_triskelion_on_cast, rock_hydra_on_cast
from models.effects.damage import erg_raiders_on_end_step, argothian_pixies_damage_prevention, \
        argothian_treefolk_damage_prevention, artifact_ward_damage_prevention, enchanted_being_damage_prevention, \
        marble_priest_damage_prevention, creature_bond_on_leave, martyrs_of_korlis_on_damage, copper_tablet_on_upkeep, \
        cursed_land_on_upkeep, elder_spawn_on_upkeep, curse_artifact_on_upkeep, feedback_and_warp_artifact_on_upkeep, \
        karma_on_upkeep, juzam_djinn_on_upkeep, lord_of_the_pit_on_upkeep, power_surge_on_upkeep, \
        serendib_efreet_on_upkeep, storm_world_on_upkeep, earthquake_on_cast, electric_eel_on_cast, \
        eternal_flame_on_cast, eye_for_an_eye_on_cast, indestructible_aura_on_cast, inferno_on_cast, \
        jovial_evil_on_cast, lightning_bolt_on_cast, typhoon_on_cast, gaseous_form_on_cast, psionic_blast_on_cast, \
        storm_seeker_on_cast
from models.effects.destroy_sac_regenerate import destroy_on_end_step, voodoo_doll_at_end_step, \
        season_of_the_witch_on_end_step, send_to_graveyard_all_lands, land_on_leave, island_on_leave, \
        conversion_on_upkeep, cosmic_horror_on_upkeep, erosion_on_upkeep, force_of_nature_on_upkeep, \
        forethought_amulet_on_upkeep, junun_efreet_on_upkeep, mana_vortex_on_upkeep, phantasmal_forces_on_upkeep, \
        season_of_the_witch_on_upkeep, sunken_city_on_upkeep, acid_rain_on_cast, cleanse_on_cast, \
        desert_twister_on_cast, disenchant_on_cast, wrath_of_god_on_cast, tivadars_crusade_on_cast, tranquility_on_cast, \
        tsunami_on_cast, sinkhole_and_stone_rain_on_cast, ice_storm_on_cast, mana_vortex_on_cast, flashfires_on_cast
from models.effects.draw_discard import cursed_rack_at_discard_phase, ancestral_recall_on_cast, braingeyser_on_cast
from models.effects.global_ import global_on_leave, angelic_voices_on_cast, bad_moon_on_cast, castle_on_cast, \
        crusade_on_cast, darkness_or_fog_or_holy_day_on_cast, sunken_city_on_cast
from models.effects.keywords import goblin_king_on_leave, erhnam_djinn_on_upkeep, akron_legionnaire_on_cast, \
        animate_wall_on_cast, brainwash_on_cast, burrowing_on_cast, demonic_torment_on_cast, \
        evil_eye_of_orms_by_gore_on_cast, flight_on_cast, fishliver_oil_on_cast, kobold_overlord_on_cast, lance_on_cast
from models.effects.life import spirit_link_on_damage, add_poison_counter_on_damage, add_two_poison_counters_on_damage, \
        el_hajjaj_on_damage, ivory_tower_on_upkeep, spiritual_sanctuary_on_upkeep, stream_of_life_on_cast
from models.effects.mana import dark_ritual_on_cast, drain_power_on_cast, energy_tap_on_cast
from models.effects.on_leave import *

from models.effects.piles import graveyard_to_board, graveyard_to_hand, boomerang_on_cast, unsummon_on_cast
from models.effects.pumps import dragon_whelp_on_end_step, giant_tortoise_on_untap, forest_on_leave, \
        kobold_drill_sergeant_on_leave, kobold_overlord_and_taskmaster_on_leave, lord_of_atlantis_on_leave, \
        blood_lust_on_cast, divine_transformation_on_cast, giant_growth_on_cast, giant_strength_on_cast, \
        giant_tortoise_on_cast, great_defender_on_cast, holy_armor_on_cast, holy_strength_on_cast, \
        howl_from_beyond_on_cast, instill_energy_on_cast, jump_on_cast, immolation_on_cast, unholy_strength_on_cast, \
        unstable_mutation_on_cast, weakness_on_cast, kobold_taskmaster_on_cast
from models.effects.special import cocoon_on_upkeep, serendib_djinn_on_upkeep, shapeshifter_on_upkeep, \
        active_volcano_on_cast, animate_dead_on_cast, crumble_on_cast, divine_offering_on_cast, earthbind_on_cast, \
        feint_on_cast, flash_flood_on_cast, forest_on_cast, goblin_king_on_cast, glyph_of_destruction_on_cast, \
        kobold_drill_sergeant_on_cast, lord_of_atlantis_on_cast, martyrs_cry_on_cast, reverse_damage_on_cast, \
        rocket_launcher_on_cast, shapeshifter_on_cast, subdue_on_cast, syphon_soul_on_cast, web_on_cast, \
        venarian_gold_on_cast, swords_to_plowshares_on_cast, farmstead_on_cast
from models.effects.tap_untap import *
from models.effects.tap_untap import host_stays_tapped_at_untap_phase, stays_tapped_at_untap_phase, \
        untap_option_at_untap_phase, cocoon_at_untap_phase, venarian_gold_at_untap_phase, leviathan_on_cast, \
        mana_short_on_cast, nevinyrrals_disk_on_cast, paralyze_on_cast, reset_on_cast, riptide_on_cast, twiddle_on_cast

SLUG_EFFECTS: dict[str, list[Effect]] = {
        'acid-rain': [acid_rain_on_cast()],
        'active-volcano': [active_volcano_on_cast()],
        'akron-legionnaire': [akron_legionnaire_on_cast(), akron_legionnaire_on_leave()],
        'ancestral-recall': [ancestral_recall_on_cast()],
        'angelic-voices': [angelic_voices_on_cast(), global_on_leave()],
        'animate-dead': [animate_dead_on_cast()],
        'animate-wall': [animate_wall_on_cast()],
        'amrou-kithkin': [amrou_kithkin_can_be_blocked()],
        'argothian-pixies': [argothian_pixies_can_be_blocked(), argothian_pixies_damage_prevention()],
        'argothian-treefolk': [argothian_treefolk_damage_prevention()],
        'armageddon': [send_to_graveyard_all_lands()],
        'artifact-ward': [artifact_ward_can_be_blocked(), artifact_ward_damage_prevention()],
        'ashnods-battle-gear': [untap_option_at_untap_phase()],
        'bad-moon': [bad_moon_on_cast(), global_on_leave()],
        'ball-lightning': [destroy_on_end_step()],
        'basalt-monolith': [stays_tapped_at_untap_phase()],
        'blood-lust': [blood_lust_on_cast()],
        'bog-rats': [bog_rats_can_be_blocked()],
        'boomerang': [boomerang_on_cast()],
        'braingeyser': [braingeyser_on_cast()],
        'brainwash': [brainwash_on_cast()],
        'brass-man': [stays_tapped_at_untap_phase()],
        'burrowing': [burrowing_on_cast()],
        'castle': [castle_on_cast(), global_on_leave()],
        'cleanse': [cleanse_on_cast()],
        'clockwork-avian': [clockwork_avian_on_cast(), remove_plus_one_zero()],
        'clockwork-beast': [clockwork_beast_on_cast(), remove_plus_one_zero()],
        'cocoon': [cocoon_on_cast(), cocoon_on_upkeep(), cocoon_at_untap_phase()],
        'colossus-of-sardia': [stays_tapped_at_untap_phase()],
        'conversion': [conversion_on_upkeep()],  # still need to code the identity change aspect
        'copper-tablet': [copper_tablet_on_upkeep()],
        'cosmic-horror': [cosmic_horror_on_upkeep()],
        'creature-bond': [creature_bond_on_leave()],
        'crumble': [crumble_on_cast()],
        'crusade': [crusade_on_cast(), global_on_leave()],
        'curse-artifact': [curse_artifact_on_upkeep()],
        'cursed-land-on-upkeep': [cursed_land_on_upkeep()],
        'cursed-rack': [cursed_rack_at_discard_phase()],
        'dark-ritual': [dark_ritual_on_cast()],
        'darkness': [darkness_or_fog_or_holy_day_on_cast()],
        'demonic-torment': [demonic_torment_on_cast()],
        'desert-twister': [desert_twister_on_cast()],
        'disenchant': [disenchant_on_cast()],
        'divine-offering': [divine_offering_on_cast()],
        'divine-transformation': [divine_transformation_on_cast()],
        'drain-power': [drain_power_on_cast()],
        'dragon-whelp': [dragon_whelp_on_end_step()],
        'earthbind': [earthbind_on_cast()],
        'earthquake': [earthquake_on_cast()],
        'el-hajjâj': [el_hajjaj_on_damage()],
        'elder-spawn': [elder_spawn_on_upkeep(), elder_spawn_can_be_blocked()],
        'electric-eel': [electric_eel_on_cast()],
        'elven-riders': [elven_riders_can_be_blocked()],
        'enchanted-being': [enchanted_being_damage_prevention()],
        'energy-tap': [energy_tap_on_cast()],
        'erg-raiders': [erg_raiders_on_end_step()],
        'erhnam-djinn': [erhnam_djinn_on_upkeep()],
        'erosion': [erosion_on_upkeep()],
        'eternal-flame': [eternal_flame_on_cast()],
        'evil-eye-of-orms-by-gore': [evil_eye_of_orms_by_gore_on_cast(), evil_eye_of_orms_by_gore_on_leave(),
                                     evil_eye_of_orms_by_gore_can_be_blocked()],
        'eye-for-an-eye': [eye_for_an_eye_on_cast()],
        'farmstead': [farmstead_on_cast()],
        'fasting': [fasting_on_upkeep()],
        'feedback': [feedback_and_warp_artifact_on_upkeep()],
        'feint': [feint_on_cast()],
        'fishliver-oil': [fishliver_oil_on_cast()],
        'flash-flood': [flash_flood_on_cast()],
        'flashfires': [flashfires_on_cast()],
        'flight': [flight_on_cast()],
        'fog': [darkness_or_fog_or_holy_day_on_cast()],
        'force-of-nature': [force_of_nature_on_upkeep()],
        'forest': [forest_on_cast(), forest_on_tap(), forest_on_leave(), land_on_leave()],
        'forethought-amulet': [forethought_amulet_on_upkeep()],  # effect need to be coded still
        'fungusaur': [fungusaur_on_damage()],
        'gaseous-form': [gaseous_form_on_cast()],
        'giant-growth': [giant_growth_on_cast()],
        'giant-strength': [giant_strength_on_cast()],
        'giant-tortoise': [giant_tortoise_on_cast(), giant_tortoise_on_tap(), giant_tortoise_on_untap()],
        'glyph-of-destruction': [glyph_of_destruction_on_cast()],
        'goblin-king': [goblin_king_on_cast(), goblin_king_on_leave()],
        'great-defender': [great_defender_on_cast()],
        'holy-armor': [holy_armor_on_cast()],
        'holy-day': [darkness_or_fog_or_holy_day_on_cast()],
        'holy-strength': [holy_strength_on_cast()],
        'howl-from-beyond': [howl_from_beyond_on_cast()],
        'ice-storm': [ice_storm_on_cast()],
        'immolation': [immolation_on_cast()],
        'indestructible-aura': [indestructible_aura_on_cast()],
        'inferno': [inferno_on_cast()],
        'instill-energy': [instill_energy_on_cast()],
        'island': [island_on_leave(), land_on_leave()],
        'island-fish-jasconius': [stays_tapped_at_untap_phase()],
        'ivory-tower': [ivory_tower_on_upkeep()],
        'jovian-evil': [jovial_evil_on_cast()],
        'jump': [jump_on_cast()],
        'junan-efreet': [junun_efreet_on_upkeep()],
        'juzam-djinn': [juzam_djinn_on_upkeep()],
        'karma': [karma_on_upkeep()],
        'kobold-drill-sergeant': [kobold_drill_sergeant_on_cast(), kobold_drill_sergeant_on_leave()],
        'kobold-overlord': [kobold_overlord_on_cast(), kobold_overlord_and_taskmaster_on_leave()],
        'kobold-taskmaster': [kobold_taskmaster_on_cast(), kobold_overlord_and_taskmaster_on_leave()],
        'lance': [lance_on_cast()],
        'leviathan': [leviathan_on_cast(), stays_tapped_at_untap_phase()],  # lots of other things to code
        'lightning-bolt': [lightning_bolt_on_cast()],
        'living-artifact': [living_artifact_on_damage()],
        'lord-of-atlantis': [lord_of_atlantis_on_cast(), lord_of_atlantis_on_leave()],
        'lord-of-the-pit': [lord_of_the_pit_on_upkeep()],
        'mana-short': [mana_short_on_cast()],
        'mana-vault': [stays_tapped_at_untap_phase()],
        'mana-vortex': [mana_vortex_on_cast(), mana_vortex_on_upkeep()],
        'marble-priest': [marble_priest_damage_prevention()],  # NOT CODED: All Walls able to block this creature do so
        'marsh-viper': [add_two_poison_counters_on_damage()],
        'martyrs-cry': [martyrs_cry_on_cast()],
        'martyrs-on-korlis': [martyrs_of_korlis_on_damage()],
        'mountain': [mountain_on_tap(), land_on_leave()],
        'nevinyrrals-disk': [nevinyrrals_disk_on_cast()],
        'old-man-of-the-sea': [untap_option_at_untap_phase()],
        'paralyze': [paralyze_on_cast(), host_stays_tapped_at_untap_phase()],
        'phantasmal-forces': [phantasmal_forces_on_upkeep()],
        'phyrexian-gremlins': [untap_option_at_untap_phase()],
        'pirate-ship': [islandhome_can_attack_effect()],
        'pit-scorpion': [add_poison_counter_on_damage()],
        'plains': [land_on_leave()],
        'power_surge': [power_surge_on_upkeep()],
        'preacher': [untap_option_at_untap_phase()],
        'primordial-ooze': [primordial_ooze_on_upkeep()],
        'psionic_blast': [psionic_blast_on_cast()],
        'raise-dead': [graveyard_to_hand()],
        'reconstruction': [graveyard_to_hand()],
        'regrowth': [graveyard_to_hand()],
        'reset': [reset_on_cast()],
        'resurrection': [graveyard_to_board()],
        'reverse-damage': [reverse_damage_on_cast()],
        'riptide': [riptide_on_cast()],
        'rock-hydra': [rock_hydra_on_cast()],
        'rocket-launcher': [rocket_launcher_on_cast()],
        'scavenging-ghoul': [scavenging_ghoul_on_end_step()],
        'sea-serpent': [islandhome_can_attack_effect()],
        'season-of-the-witch': [season_of_the_witch_on_upkeep(), season_of_the_witch_on_end_step()],
        'seeker': [seeker_enchanted_creature_can_be_blocked()],
        'serendib-djinn': [serendib_djinn_on_upkeep()],
        'serendib-efreet': [serendib_efreet_on_upkeep()],
        'shapeshifter': [shapeshifter_on_cast(), shapeshifter_on_upkeep()],
        'sinkhole': [sinkhole_and_stone_rain_on_cast()],
        'swamp': [land_on_leave()],
        'spirit-link': [spirit_link_on_damage()],
        'spirit-shackle': [spirit_shackle_on_tap()],
        'spiritual-sanctuary': [spiritual_sanctuary_on_upkeep()],
        'stone-rain': [sinkhole_and_stone_rain_on_cast()],
        'storm-seeker': [storm_seeker_on_cast()],
        'storm-world': [storm_world_on_upkeep()],
        'stream-of-life': [stream_of_life_on_cast()],
        'subdue': [subdue_on_cast()],
        'sunken-city': [sunken_city_on_cast(), sunken_city_on_upkeep(), global_on_leave()],
        'swords-to-plowshares': [swords_to_plowshares_on_cast()],
        'syphon-soul': [syphon_soul_on_cast()],
        'tawnoss-coffin': [untap_option_at_untap_phase()],
        'tawnoss-weaponry': [untap_option_at_untap_phase()],
        'tetravus': [tetravus_and_triskelion_on_cast()],
        'time-vault': [stays_tapped_at_untap_phase()],
        'tivadars-crusade': [tivadars_crusade_on_cast()],
        'tranquility': [tranquility_on_cast()],
        'triskelion': [tetravus_and_triskelion_on_cast()],
        'tsunami': [tsunami_on_cast()],
        'twiddle': [twiddle_on_cast()],
        'typhoon': [typhoon_on_cast()],
        'unholy-strength': [unholy_strength_on_cast()],
        'unstable-mutation': [unstable_mutation_on_cast(), unstable_mutation_on_upkeep()],
        'unsummon': [unsummon_on_cast()],
        'venarian-gold': [venarian_gold_on_cast(), venarian_gold_at_untap_phase(), venarian_gold_on_upkeep()],
        'voodoo-doll': [voodoo_doll_on_upkeep(), voodoo_doll_at_end_step()],
        'warp-artifact': [feedback_and_warp_artifact_on_upkeep()],
        'weakness': [weakness_on_cast()],
        'web': [web_on_cast()],
        'wrath-of-god': [wrath_of_god_on_cast()],

    }
