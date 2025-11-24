card_statuses = {
    'air-elemental': 'done',
    'alabaster-potion': '',
    'amrou-kithkin': 'done',
    'angry-mob': '',
    'animate-artifact': 'excluded',
    'animate-wall': 'done',
    'apprentice-wizard': '',
    'armageddon': 'done',
    'backfire': 'done',
    'balance': '',
    'benalish-hero': 'excluded',
    'black-ward': '',
    'blessing': 'done',
    'blue-elemental-blast': 'excluded',
    'blue-ward': '',
    'braingeyser': '',
    'brainwash': '',
    'castle': 'done',
    'circle-of-protection-artifacts': 'excluded',
    'circle-of-protection-black': '',
    'circle-of-protection-blue': '',
    'circle-of-protection-green': 'excluded',
    'circle-of-protection-red': 'excluded',
    'circle-of-protection-white': '',
    'clone': '',
    'control-magic': '',
    'conversion': 'excluded',
    'copy-artifact': 'excluded',
    'counterspell': '',
    'creature-bond': 'test',  # When creature dies, deal damage = creature's toughness to the creature's controller
    'crusade': 'done',
    'death-ward': '',
    'disenchant': 'done',
    'divine-transformation': 'done',
    'drain-power': '',
    'elder-land-wurm': '',
    'energy-flux': 'excluded',
    'energy-tap': '',
    'erosion': '',
    'eye-for-an-eye': '',
    'farmstead': '',
    'feedback': 'done',
    'flight': 'done',
    'flood': 'done',
    'fortified-area': 'excluded',
    'gaseous-form': '',
    'ghost-ship': '',
    'giant-tortoise': 'done',
    'green-ward': 'excluded',
    'guardian-angel': '',
    'healing-salve': '',
    'holy-armor': 'done',
    'holy-strength': 'done',
    'hurkyls-recall': 'excluded',
    'island-fish-jasconius': '',
    'island-sanctuary': '',
    'jump': 'done',
    'karma': 'done',
    'kismet': '',
    'lance': 'done',
    'land-tax': '',
    'leviathan': '',
    'lifetap': 'excluded',
    'lord-of-atlantis': '',
    'magical-hack': '',
    'mahamoti-djinn': 'done',
    'mana-short': '',
    'merfolk-of-the-pearl-trident': 'done',
    'mesa-pegasus': 'excluded',
    'mind-bomb': '',
    'morale': '',
    'northern-paladin': '',  # Creature 2WW {WW}, {T}: Destroy target black permanent
    'osai-vultures': '',
    'pearled-unicorn': 'done',
    'personal-incarnation': '',
    'phantasmal-forces': '',
    'phantasmal-terrain': '',
    'phantom-monster': '',
    'piety': '',
    'pikemen': 'excluded',
    'pirate-ship': 'done',
    'power-leak': '',
    'power-sink': '',
    'prodigal-sorcerer': 'done',
    'psionic-entity': 'done',
    'psychic-venom': '',
    'purelace': '',
    'reconstruction': '',
    'red-ward': 'excluded',
    'relic-bind': 'excluded',
    'resurrection': '',
    'reverse-damage': '',
    'reverse-polarity': '',
    'righteousness': '',
    'samite-healer': '',
    'savannah-lions': 'done',
    'sea-serpent': 'done',
    'seeker': 'done',
    'segovian-leviathan': '',
    'serendib-efreet': 'done',
    'serra-angel': 'done',
    'sindbad': '',
    'sirens-call': '',
    'sleight-of-mind': '',
    'spell-blast': '',
    'spirit-link': '',
    'stasis': '',
    'steal-artifact': 'excluded',
    'sunken-city': '',
    'swords-to-plowshares': 'done',
    'thoughtlace': '',
    'time-elemental': '',
    'tundra-wolves': 'done',
    'twiddle': 'done',
    'unstable-mutation': '',
    'unsummon': 'done',
    'vesuvan-doppelganger': '',
    'veteran-bodyguard': '',
    'visions': '',
    'volcanic-eruption': 'excluded',
    'wall-of-air': 'done',
    'wall-of-swords': 'done',
    'wall-of-water': 'done',
    'water-elemental': 'done',
    'white-knight': '',
    'white-ward': '',
    'wrath-of-god': 'done',
    'zephyr-falcon': 'done',
}

if __name__ == '__main__':
    print("Cards to be tested:")
    for k, v in card_statuses.items():
        if v == 'test':
            print(k)

"""
Remaining:
-   Identity changers:
        clone: Creature You may have this creature enter as a copy of any creature on the battlefield
        phantasmal-terrain: Enchant land As Aura enters, choose a basic land type. Enchanted land is the chosen type
        purelace: Instant Target spell/permanent becomes white. (Mana symbols on that permanent remain unchanged.)
        magical-hack: Change the text of target spell or permanent by replacing all instances of one basic land type with another. u003cIu003e(For example, you may change "swampwalk" to "plainswalk." This effect lasts indefinitely.
        sleight-of-mind: Instant Change the text of target spell or permanent by replacing all instances of one color word with another. u003cIu003e(For example, you may change "target black spell" to "target blue spell." This effect lasts indefinitely.
        thoughtlace: Target spell/permanent becomes blue. u003cIu003e(Mana symbols on that permanent remain unchanged.
        vesuvan-doppelganger: Creature 'You may have this creature enter as a copy of any creature on the battlefield, except it doesn\'t copy that creature\'s color and it has "At the beginning of your upkeep, you may have this creature become a copy of target creature, except it doesn\'t copy that creature\'s color and it has this ability.

-   Card Theft:
        control-magic: Enchant creature You control enchanted creature

-   Counter Tokens:
        unstable-mutation: Aura gets +3/+3. At the beginning of controller upkeep, put a -1/-1 counter on that creature

-   Conditional Attack:
        brainwash: {'card_type': 'Aura', "Enchanted creature can't attack unless its controller pays {3}."}

-   Deals Damage (combat damage is currently handled in a completely separate place):
        spirit-link: Aura Whenever enchanted creature deals damage, you gain that much life

-   Activated Ability at a specific time:
        farmstead: Enchanted land has "At the beginning of your upkeep, {WW}: you gain 1 life
        
-   Mana mod:

        ### TODO NEXT ### MANA MODIFIERS ... RE-WORK HOW MANA IS HANDLED

        apprentice-wizard: 'Creature', {U}, {T}: Add {CCC}
        drain-power Sorcery UU Target player activates a mana ability of each land they control. Then that player loses all unspent mana and you add the mana lost this way
        energy-tap: 'Sorcery', "Tap target untapped creature you control; add an amount of {C} = its mana value.
        
 -  Missing a Phase/Step:  # (There's no casting period after FinishDeclaringAttacker & FinishDeclaringBlockers)
        morale: Instant, Attacking creatures get +1/+1 until end of turn  
        piety: Instant, Blocking creatures get +0/+3 until end of turn
        righteousness: Instant, Target blocking creature gets +7/+7 until end of turn

-   Next Damage Dealt:
        COP-black, blue, white: {1}: The next time a _ source of your choice would deal damage to you this turn, prevent
        eye-for-an-eye: Instant The next time a source of your choice would deal damage to you this turn, instead that source deals that much damage to you and Eye for an Eye deals that much damage to that source's controller
        gaseous-form: Enchant creature Prevent all combat damage that would be dealt to and dealt by enchanted creature
        guardian-angel Instant Prevent the next X damage that would be dealt to any target this turn. Until end of turn, you may pay {1} any time you could cast an instant. If you do, prevent the next 1 damage that would be dealt to that permanent or player this turn
        healing-salve: Instant Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.
        samite-healer: {T}: Prevent the next 1 damage that would be dealt to any target this turn

-   Protection:
        black-ward
        blue-ward
        red-ward
        white-knight

-   Regeneration:
        death-ward: Instant: Regenerate target creature
        ghost-ship: ['Flying'], {UUU}: Regenerate this creature.

-   Target player:
        'braingeyser': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Target player draws X cards.'},
        'mana-short: 'Instant', Tap all lands target player controls and that player loses all unspent mana

-   Trample:
        angry-mob

-   User choice:
        alabaster-potion: Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.
        balance: (All users chose) Each player chooses a number of lands they control equal to the number of lands controlled by the player who controls the fewest, then sacrifices the rest. Players discard cards and sacrifice creatures the same way
        erosion: Enchant land At begin of upkeep of controller, destroy that land unless that player pays {1} or 1 life
        healing-salve: Instant Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.
        phantasmal-forces: 'Creature', 'Flying' At begin of your upkeep, sac unless you pay {U}
        sunken-city: Enchantment', At the begin of your upkeep, sac unless you pay {UU}. Blue creatures get +1/+1

-   Variable cast:
        alabaster-potion: Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.
        spell-blast: Instant Counter target spell with mana value X
        
-   Variable PT:
        angry-mob: During your turn, Angry Mob's power and toughness are each equal to 2 plus the number of Swamps your opponents control. During turns other than yours, Angry Mob's power and toughness are each 2.

-   Walk:
        lord-of-atlantis: Creature UU Other Merfolk get +1/+1 and have islandwalk
        segovian-leviathan: Creature "Islandwalk (can't be blocked as long as defending player controls an Island.)

"""


"""
air-elemental Creature 3UU Flying
alabaster-potion Instant XWW Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.
amrou-kithkin Creature WW This creature can't be blocked by creatures with power 3 or greater.
angry-mob Creature 2WW Trample During your turn, Angry Mob's power and toughness are each equal to 2 plus the number of Swamps your opponents control. During turns other than yours, Angry Mob's power and toughness are each 2.
animate-artifact Aura 3U Enchant artifact As long as enchanted artifact isn't a creature, it's an artifact creature with power and toughness each equal to its mana value.
animate-wall Aura W Enchant Wall Enchanted Wall can attack as though it didn't have defender.
apprentice-wizard Creature 1UU {U}, {T}: Add {CCC}.
armageddon Sorcery 3W Destroy all lands.
backfire Aura U Enchant creature Whenever enchanted creature deals damage to you, this Aura deals that much damage to that creature's controller.
balance Sorcery 1W Each player chooses a number of lands they control equal to the number of lands controlled by the player who controls the fewest, then sacrifices the rest. Players discard cards and sacrifice creatures the same way.
benalish-hero Creature W Banding u003ciu003e(Any creatures with banding, and up to one without, can attack in a band. Bands are blocked as a group. If any creatures with banding you control are blocking or being blocked by a creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)u003c/iu003e
black-ward Aura W Enchant creature Enchanted creature has protection from black. This effect doesn't remove this Aura.
blessing Aura WW Enchant creature {W}: Enchanted creature gets +1/+1 until end of turn.
blue-elemental-blast Instant U Choose one - * Counter target red spell. * Destroy target red permanent.
blue-ward Aura W Enchant creature Enchanted creature has protection from blue. This effect doesn't remove this Aura.
braingeyser Sorcery XUU Target player draws X cards.
brainwash Aura W Enchant creature Enchanted creature can't attack unless its controller pays {3}.
castle Enchantment 3W Untapped creatures you control get +0/+2.
circle-of-protection-artifacts Enchantment 1W {2}: The next time an artifact source of your choice would deal damage to you this turn, prevent that damage.
circle-of-protection-black Enchantment 1W {1}: The next time a black source of your choice would deal damage to you this turn, prevent that damage.
circle-of-protection-blue Enchantment 1W {1}: The next time a blue source of your choice would deal damage to you this turn, prevent that damage.
circle-of-protection-green Enchantment 1W {1}: The next time a green source of your choice would deal damage to you this turn, prevent that damage.
circle-of-protection-red Enchantment 1W {1}: The next time a red source of your choice would deal damage to you this turn, prevent that damage.
circle-of-protection-white Enchantment 1W {1}: The next time a white source of your choice would deal damage to you this turn, prevent that damage.
clone Creature 3U You may have this creature enter as a copy of any creature on the battlefield.
control-magic Aura 2UU Enchant creature You control enchanted creature.
conversion Enchantment 2WW At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}. All Mountains are Plains.
copy-artifact Enchantment 1U You may have this enchantment enter as a copy of any artifact on the battlefield, except it's an enchantment in addition to its other types.
counterspell Instant UU Counter target spell.
creature-bond Aura 1U Enchant creature When enchanted creature dies, this Aura deals damage equal to that creature's toughness to the creature's controller.
crusade Enchantment WW White creatures get +1/+1.
death-ward Instant W Regenerate target creature.
disenchant Instant 1W Destroy target artifact or enchantment.
divine-transformation Aura 2WW Enchant creature Enchanted creature gets +3/+3.
drain-power Sorcery UU Target player activates a mana ability of each land they control. Then that player loses all unspent mana and you add the mana lost this way.
elder-land-wurm Creature 4WWW Defender, trample When this creature blocks, it loses defender.
energy-flux Enchantment 2U All artifacts have "At the beginning of your upkeep, sacrifice this artifact unless you pay {2}."
energy-tap Sorcery U Tap target untapped creature you control. If you do, add an amount of {C} equal to that creature's mana value.
erosion Aura UUU Enchant land At the beginning of the upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life.
eye-for-an-eye Instant WW The next time a source of your choice would deal damage to you this turn, instead that source deals that much damage to you and Eye for an Eye deals that much damage to that source's controller.
farmstead Aura WWW Enchant land Enchanted land has "At the beginning of your upkeep, you may pay {WW}. If you do, you gain 1 life."
feedback Aura 2U Enchant enchantment At the beginning of the upkeep of enchanted enchantment's controller, this Aura deals 1 damage to that player.
flight Aura U Enchant creature Enchanted creature has flying.
flood Enchantment U {UU}: Tap target creature without flying.
fortified-area Enchantment 1WW Wall creatures you control get +1/+0 and have banding. u003ciu003e(Any creatures with banding, and up to one without, can attack in a band. Bands are blocked as a group. If any creatures with banding you control are blocking or being blocked by a creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)u003c/iu003e
gaseous-form Aura 2U Enchant creature Prevent all combat damage that would be dealt to and dealt by enchanted creature.
ghost-ship Creature 2UU Flying {UUU}: Regenerate this creature.
giant-tortoise Creature 1U This creature gets +0/+3 as long as it's untapped.
green-ward Aura W Enchant creature Enchanted creature has protection from green. This effect doesn't remove this Aura.
guardian-angel Instant XW Prevent the next X damage that would be dealt to any target this turn. Until end of turn, you may pay {1} any time you could cast an instant. If you do, prevent the next 1 damage that would be dealt to that permanent or player this turn.
healing-salve Instant W Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.
holy-armor Aura W Enchant creature Enchanted creature gets +0/+2. {W}: Enchanted creature gets +0/+1 until end of turn.
holy-strength Aura W Enchant creature Enchanted creature gets +1/+2.
hurkyls-recall Instant 1U Return all artifacts target player owns to their hand.
island-fish-jasconius Creature 4UUU This creature doesn't untap during your untap step. At the beginning of your upkeep, you may pay {UUU}. If you do, untap this creature. This creature can't attack unless defending player controls an Island. When you control no Islands, sacrifice this creature.
island-sanctuary Enchantment 1W If you would draw a card during your draw step, instead you may skip that draw. If you do, until your next turn, you can't be attacked except by creatures with flying and/or islandwalk.
jump Instant U Target creature gains flying until end of turn.
karma Enchantment 2WW At the beginning of each player's upkeep, this enchantment deals damage to that player equal to the number of Swamps they control.
kismet Enchantment 3W Artifacts, creatures, and lands your opponents control enter tapped.
lance Aura W Enchant creature Enchanted creature has first strike.
land-tax Enchantment W At the beginning of your upkeep, if an opponent controls more lands than you, you may search your library for up to three basic land cards, reveal them, put them into your hand, then shuffle.
leviathan Creature 5UUUU Trample This creature enters tapped and doesn't untap during your untap step. At the beginning of your upkeep, you may sacrifice two Islands. If you do, untap this creature. This creature can't attack unless you sacrifice two Islands. u003ciu003e(This cost is paid as attackers are declared.)u003c/iu003e
lifetap Enchantment UU Whenever a Forest an opponent controls becomes tapped, you gain 1 life.
lord-of-atlantis Creature UU Other Merfolk get +1/+1 and have islandwalk. u003ciu003e(They can't be blocked as long as defending player controls an Island.)u003c/iu003e
magical-hack Instant U Change the text of target spell or permanent by replacing all instances of one basic land type with another. u003cIu003e(For example, you may change "swampwalk" to "plainswalk." This effect lasts indefinitely.)u003c/Iu003e
mahamoti-djinn Creature 4UU Flying u003ciu003e(This creature can't be blocked except by creatures with flying or reach.)u003c/iu003e
mana-short Instant 2U Tap all lands target player controls and that player loses all unspent mana.
merfolk-of-the-pearl-trident Creature U Oracle
mesa-pegasus Creature 1W Flying; banding u003ciu003e(Any creatures with banding, and up to one without, can attack in a band. Bands are blocked as a group. If any creatures with banding you control are blocking or being blocked by a creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)u003c/iu003e
mind-bomb Sorcery U Each player may discard up to three cards. Mind Bomb deals damage to each player equal to 3 minus the number of cards they discarded this way.
morale Instant 1WW Attacking creatures get +1/+1 until end of turn.
northern-paladin Creature 2WW {WW}, {T}: Destroy target black permanent.
osai-vultures Creature 1W Flying At the beginning of each end step, if a creature died this turn, put a carrion counter on this creature. Remove two carrion counters from this creature: This creature gets +1/+1 until end of turn.
pearled-unicorn Creature 2W Oracle
personal-incarnation Creature 3WWW {0}: The next 1 damage that would be dealt to this creature this turn is dealt to its owner instead. Only this creatures owner may activate this ability. When this creature dies, its owner loses half their life, rounded up.
phantasmal-forces Creature 3U Flying At the beginning of your upkeep, sacrifice this creature unless you pay {U}.
phantasmal-terrain Aura UU Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type.
phantom-monster Creature 3U Flying
piety Instant 2W Blocking creatures get +0/+3 until end of turn.
pikemen Creature 1W First strike; banding u003ciu003e(Any creatures with banding, and up to one without, can attack in a band. Bands are blocked as a group. If any creatures with banding you control are blocking or being blocked by a creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)u003c/iu003e
pirate-ship Creature 4U This creature can't attack unless defending player controls an Island. {T}: This creature deals 1 damage to any target. When you control no Islands, sacrifice this creature.
power-leak Aura 1U Enchant enchantment At the beginning of the upkeep of enchanted enchantment's controller, that player may pay any amount of mana. This Aura deals 2 damage to that player. Prevent X of that damage, where X is the amount of mana that player paid this way.
power-sink Instant XU Counter target spell unless its controller pays {X}. If that player doesn't, they tap all lands with mana abilities they control and lose all unspent mana.
prodigal-sorcerer Creature 2U {T}: This creature deals 1 damage to any target.
psionic-entity Creature 4U {T}: This creature deals 2 damage to any target and 3 damage to itself.
psychic-venom Aura 1U Enchant land Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller.
purelace Instant W Target spell or permanent becomes white. u003cIu003e(Mana symbols on that permanent remain unchanged.)u003c/Iu003e
reconstruction Sorcery U Return target artifact card from your graveyard to your hand.
red-ward Aura W Enchant creature Enchanted creature has protection from red. This effect doesn't remove this Aura.
relic-bind Aura 2U Enchant artifact an opponent controls Whenever enchanted artifact becomes tapped, choose one - * This Aura deals 1 damage to target player or planeswalker. * Target player gains 1 life.
resurrection Sorcery 2WW Return target creature card from your graveyard to the battlefield.
reverse-damage Instant 1WW The next time a source of your choice would deal damage to you this turn, prevent that damage. You gain life equal to the damage prevented this way.
reverse-polarity Instant WW You gain X life, where X is twice the damage dealt to you so far this turn by artifacts.
righteousness Instant W Target blocking creature gets +7/+7 until end of turn.
samite-healer Creature 1W {T}: Prevent the next 1 damage that would be dealt to any target this turn.
savannah-lions Creature W Oracle
sea-serpent Creature 5U This creature can't attack unless defending player controls an Island. When you control no Islands, sacrifice this creature.
seeker Aura 2WW Enchant creature Enchanted creature can't be blocked except by artifact creatures and/or white creatures.
segovian-leviathan Creature 4U Islandwalk u003ciu003e(This creature can't be blocked as long as defending player controls an Island.)u003c/iu003e
serendib-efreet Creature 2U Flying At the beginning of your upkeep, this creature deals 1 damage to you.
serra-angel Creature 3WW Flying Vigilance u003ciu003e(Attacking doesn't cause this creature to tap.)u003c/iu003e
sindbad Creature 1U {T}: Draw a card and reveal it. If it isn't a land card, discard it.
sirens-call Instant U Cast this spell only during an opponent's turn, before attackers are declared. Creatures the active player controls attack this turn if able. At the beginning of the next end step, destroy all non-Wall creatures that player controls that didn't attack this turn. Ignore this effect for each creature the player didn't control continuously since the beginning of the turn.
sleight-of-mind Instant U Change the text of target spell or permanent by replacing all instances of one color word with another. u003cIu003e(For example, you may change "target black spell" to "target blue spell." This effect lasts indefinitely.)u003c/Iu003e
spell-blast Instant XU Counter target spell with mana value X. u003ciu003e(For example, if that spell's mana cost is {3UU}, X is 5.)u003c/iu003e
spirit-link Aura W Enchant creature u003ciu003e(Target a creature as you cast this. This card enters attached to that creature.)u003c/iu003e Whenever enchanted creature deals damage, you gain that much life.
stasis Enchantment 1U Players skip their untap steps. At the beginning of your upkeep, sacrifice this enchantment unless you pay {U}.
steal-artifact Aura 2UU Enchant artifact You control enchanted artifact.
sunken-city Enchantment UU At the beginning of your upkeep, sacrifice this enchantment unless you pay {UU}. Blue creatures get +1/+1.
swords-to-plowshares Instant W Exile target creature. Its controller gains life equal to its power.
thoughtlace Instant U Target spell or permanent becomes blue. u003cIu003e(Mana symbols on that permanent remain unchanged.)u003c/Iu003e
time-elemental Creature 2U When this creature attacks or blocks, at end of combat, sacrifice it and it deals 5 damage to you. {2UU}, {T}: Return target permanent that isn't enchanted to its owner's hand.
tundra-wolves Creature W First strike u003ciu003e(This creature deals combat damage before creatures without first strike.)u003c/iu003e
twiddle Instant U You may tap or untap target artifact, creature, or land.
unstable-mutation Aura U Enchant creature Enchanted creature gets +3/+3. At the beginning of the upkeep of enchanted creature's controller, put a -1/-1 counter on that creature.
unsummon Instant U Return target creature to its owner's hand.
vesuvan-doppelganger Creature 3UU You may have this creature enter as a copy of any creature on the battlefield, except it doesn't copy that creature's color and it has "At the beginning of your upkeep, you may have this creature become a copy of target creature, except it doesn't copy that creature's color and it has this ability."
veteran-bodyguard Creature 3WW As long as this creature is untapped, all damage that would be dealt to you by unblocked creatures is dealt to this creature instead.
visions Sorcery W Look at the top five cards of target player's library. You may then have that player shuffle that library.
volcanic-eruption Sorcery XUUU Destroy X target Mountains. Volcanic Eruption deals damage to each creature and each player equal to the number of Mountains put into a graveyard this way.
wall-of-air Creature 1UU Defender, flying u003ciu003e(This creature can't attack, and it can block creatures with flying.)u003c/iu003e
wall-of-swords Creature 3W Defender u003ciu003e(This creature can't attack.)u003c/iu003e Flying
wall-of-water Creature 1UU Defender u003ciu003e(This creature can't attack.)u003c/iu003e {U}: This creature gets +1/+0 until end of turn.
water-elemental Creature 3UU Oracle
white-knight Creature WW First strike u003ciu003e(This creature deals combat damage before creatures without first strike.)u003c/iu003e Protection from black u003ciu003e(This creature can't be blocked, targeted, dealt damage, or enchanted by anything black.)u003c/iu003e
white-ward Aura W Enchant creature Enchanted creature has protection from white. This effect doesn't remove this Aura.
wrath-of-god Sorcery 2WW Destroy all creatures. They can't be regenerated.
zephyr-falcon Creature 1U Flying, vigilance
"""