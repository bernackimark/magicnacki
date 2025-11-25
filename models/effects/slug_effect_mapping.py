from models.effects.can_attack import *
from models.effects.can_block import *
from models.effects.cast import *
from models.effects.common import *
from models.effects.leave import *
from models.effects.tap import *
from models.effects.upkeep import *
from models.effects.untap import *

SLUG_EFFECTS: dict[str, list[Effect]] = {
        'animate-wall': [animate_wall_on_cast()],
        'amrou-kithkin': [amrou_kithkin_can_be_blocked()],
        'armageddon': [send_to_graveyard_all_lands()],
        'brainwash': [brainwash_on_cast()],
        'castle': [castle_on_cast(), castle_on_leave()],
        'creature-bond': [creature_bond_on_leave()],
        'crusade': [crusade_on_cast(), crusade_on_leave()],
        'disenchant': [disenchant_on_cast()],
        'divine-transformation': [divine_transformation_on_cast()],
        'drain-power': [drain_power_on_cast()],
        'energy-tap': [energy_tap_on_cast()],
        'farmstead': [farmstead_on_cast()],
        'feedback': [feedback_on_upkeep()],
        'flight': [flying_on_cast()],
        'giant-tortoise': [giant_tortoise_on_cast(), giant_tortoise_on_tap(), giant_tortoise_on_untap()],
        'holy-armor': [holy_armor_on_cast()],
        'holy-strength': [holy_strength_on_cast()],
        'island': [island_on_leave()],
        'jump': [jump_on_cast()],
        'karma': [karma_on_upkeep()],
        'lance': [lance_on_cast()],
        'lord-of-atlantis': [lord_of_atlantis_on_cast(), lord_of_atlantis_on_leave()],
        'mana-short': [mana_short_on_cast()],
        'pirate-ship': [islandhome_can_attack_effect()],
        'sea-serpent': [islandhome_can_attack_effect()],
        'seeker': [seeker_enchanted_creature_can_be_blocked()],
        'serendib-efreet': [serendib_efreet_on_upkeep()],
        'swords-to-plowshares': [swords_to_plowshares_on_cast()],
        'twiddle': [twiddle_on_cast()],
        'unsummon': [unsummon_on_cast()],
        'wrath-of-god': [wrath_of_god_on_cast()],

        '_default_leave': [default_clear_on_leave()],
    }
