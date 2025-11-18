from models.game_card import GameCard

class CardFilter:
    def __init__(self, gs: "GameState"):
        self._gs = gs
        self._cards = self._gs.all_cards

    def in_play(self):
        self._cards = [c for b in self._gs.boards for c in b.cards]
        return self

    def in_graveyards(self):
        self._cards = [c for g in self._gs.graveyards for c in g]
        return self

    def by_type(self, type_: str | list):
        if isinstance(type_, list):
            self._cards = [c for c in self._cards for t in type_ if t in c.props.card_types]
        else:
            self._cards = [c for c in self._cards if type_ in c.props.card_types]
        return self

    def by_sub_type(self, type_: str | list):
        if isinstance(type_, list):
            self._cards = [c for c in self._cards for t in type_ if t in c.props.card_sub_types]
        else:
            self._cards = [c for c in self._cards if type_ in c.props.card_sub_types]
        return self

    def by_color(self, color: str | list):
        if isinstance(color, list):
            self._cards = [c for c in self._cards for col in color if col in c.props.colors]
        else:
            self._cards = [c for c in self._cards if color in c.props.colors]
        return self

    def result(self) -> list["GameCard"]:
        return self._cards


"""
Just added, needs testing:
    amrou-kithkin
    animate-wall
    crusade: {'card_type': 'Enchantment', 'kwa': [], 'rules': 'White creatures get +1/+1.'},

Remaining:
-   Target player:
        'braingeyser': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Target player draws X cards.'},
 
-   Variable cast:
        alabaster-potion

-   Variable PT:
        angry-mob

-   Trample:
        angry-mob

-   Conditional Counter:
        brainwash: {'card_type': 'Aura', "Enchanted creature can't attack unless its controller pays {3}."}

-   Activated Ability:
        apprentice-wizard
        blessing: {'card_type': 'Aura', '{W}: Enchanted creature gets +1/+1 until end of turn.'}

-   Various:
        add protection-from-black to white-knight

-   Intentionally Excluding:
        artifact reliant: animate-artifact
        banding: benalish-bero
        color reliant: blue-elemental-blast, COPs, 
"""

"""
{
'alabaster-potion              ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.'},
'angry-mob                     ': {'card_type': 'Creature', 'kwa': ['Trample'], 'rules': "Trample During your turn, Angry Mob's power and toughness are each equal to 2 plus the number of Swamps your opponents control. During turns other than yours, Angry Mob's power and toughness are each 2."},
'apprentice-wizard             ': {'card_type': 'Creature', 'kwa': [], 'rules': '{U}, {T}: Add {CCC}.'},
'backfire                      ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Whenever enchanted creature deals damage to you, this Aura deals that much damage to that creature's controller."},
 'balance                       ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Each player chooses a number of lands they control equal to the number of lands controlled by the player who controls the fewest, then sacrifices the rest. Players discard cards and sacrifice creatures the same way.'},
'black-ward                    ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Enchanted creature has protection from black. This effect doesn't remove this Aura."},
'blue-ward                     ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Enchanted creature has protection from blue. This effect doesn't remove this Aura."},
'castle                        ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'Untapped creatures you control get +0/+2.'},
'circle-of-protection-black    ': {'card_type': 'Enchantment', 'kwa': [], 'rules': '{1}: The next time a black source of your choice would deal damage to you this turn, prevent that damage.'},
'circle-of-protection-blue     ': {'card_type': 'Enchantment', 'kwa': [], 'rules': '{1}: The next time a blue source of your choice would deal damage to you this turn, prevent that damage.'},
'circle-of-protection-white    ': {'card_type': 'Enchantment', 'kwa': [], 'rules': '{1}: The next time a white source of your choice would deal damage to you this turn, prevent that damage.'},
 'clone                         ': {'card_type': 'Creature', 'kwa': [], 'rules': 'You may have this creature enter as a copy of any creature on the battlefield.'},
 'control-magic                 ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature You control enchanted creature.'},
 'conversion                    ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}. All Mountains are Plains.'},
 'copy-artifact                 ': {'card_type': 'Enchantment', 'kwa': [], 'rules': "You may have this enchantment enter as a copy of any artifact on the battlefield, except it's an enchantment in addition to its other types."},
 'death-ward                    ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Regenerate target creature.'},
 'disenchant                    ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Destroy target artifact or enchantment.'},
 'divine-transformation         ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature Enchanted creature gets +3/+3.'},
 'drain-power                   ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Target player activates a mana ability of each land they control. Then that player loses all unspent mana and you add the mana lost this way.'},
 'elder-land-wurm               ': {'card_type': 'Creature', 'kwa': ['Defender', 'Trample'], 'rules': 'Defender, trample When this creature blocks, it loses defender.'},
 'energy-flux                   ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'All artifacts have "At the beginning of your upkeep, sacrifice this artifact unless you pay {2}."'},
 'energy-tap                    ': {'card_type': 'Sorcery', 'kwa': [], 'rules': "Tap target untapped creature you control. If you do, add an amount of {C} equal to that creature's mana value."},
 'erosion                       ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant land At the beginning of the upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life."},
 'eye-for-an-eye                ': {'card_type': 'Instant', 'kwa': [], 'rules': "The next time a source of your choice would deal damage to you this turn, instead that source deals that much damage to you and Eye for an Eye deals that much damage to that source's controller."},
 'farmstead                     ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant land Enchanted land has "At the beginning of your upkeep, you may pay {WW}. If you do, you gain 1 life."'},
 'feedback                      ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant enchantment At the beginning of the upkeep of enchanted enchantment's controller, this Aura deals 1 damage to that player."},
 'flight                        ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature Enchanted creature has flying.'},
 'flood                         ': {'card_type': 'Enchantment', 'kwa': [], 'rules': '{UU}: Tap target creature without flying.'},
 'fortified-area                ': {'card_type': 'Enchantment', 'kwa': [], 'rules': "Wall creatures you control get +1/+0 and have banding. u003ciu003e(Any creatures with banding, and up to one without, can attack in a band. Bands are blocked as a group. If any creatures with banding you control are blocking or being blocked by a creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)u003c/iu003e"},
 'gaseous-form                  ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature Prevent all combat damage that would be dealt to and dealt by enchanted creature.'},
 'ghost-ship                    ': {'card_type': 'Creature', 'kwa': ['Flying'], 'rules': 'Flying {UUU}: Regenerate this creature.'},
 'giant-tortoise                ': {'card_type': 'Creature', 'kwa': [], 'rules': "This creature gets +0/+3 as long as it's untapped."},
 'green-ward                    ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Enchanted creature has protection from green. This effect doesn't remove this Aura."},
 'guardian-angel                ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Prevent the next X damage that would be dealt to any target this turn. Until end of turn, you may pay {1} any time you could cast an instant. If you do, prevent the next 1 damage that would be dealt to that permanent or player this turn.'},
 'healing-salve                 ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.'},
 'holy-armor                    ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature Enchanted creature gets +0/+2. {W}: Enchanted creature gets +0/+1 until end of turn.'},
 'holy-strength                 ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature Enchanted creature gets +1/+2.'},
 'hurkyls-recall                ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Return all artifacts target player owns to their hand.'},
 'island-fish-jasconius         ': {'card_type': 'Creature', 'kwa': [], 'rules': "This creature doesn't untap during your untap step. At the beginning of your upkeep, you may pay {UUU}. If you do, untap this creature. This creature can't attack unless defending player controls an Island. When you control no Islands, sacrifice this creature."},
 'island-sanctuary              ': {'card_type': 'Enchantment', 'kwa': [], 'rules': "If you would draw a card during your draw step, instead you may skip that draw. If you do, until your next turn, you can't be attacked except by creatures with flying and/or islandwalk."},
 'jump                          ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Target creature gains flying until end of turn.'},
 'karma                         ': {'card_type': 'Enchantment', 'kwa': [], 'rules': "At the beginning of each player's upkeep, this enchantment deals damage to that player equal to the number of Swamps they control."},
 'kismet                        ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'Artifacts, creatures, and lands your opponents control enter tapped.'},
 'lance                         ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature Enchanted creature has first strike.'},
 'land-tax                      ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'At the beginning of your upkeep, if an opponent controls more lands than you, you may search your library for up to three basic land cards, reveal them, put them into your hand, then shuffle.'},
 'leviathan                     ': {'card_type': 'Creature', 'kwa': ['Trample'], 'rules': "Trample This creature enters tapped and doesn't untap during your untap step. At the beginning of your upkeep, you may sacrifice two Islands. If you do, untap this creature. This creature can't attack unless you sacrifice two Islands. u003ciu003e(This cost is paid as attackers are declared.)u003c/iu003e"},
 'lifetap                       ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'Whenever a Forest an opponent controls becomes tapped, you gain 1 life.'},
 'lord-of-atlantis              ': {'card_type': 'Creature', 'kwa': [], 'rules': "Other Merfolk get +1/+1 and have islandwalk. u003ciu003e(They can't be blocked as long as defending player controls an Island.)u003c/iu003e"},
 'magical-hack                  ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Change the text of target spell or permanent by replacing all instances of one basic land type with another. u003cIu003e(For example, you may change "swampwalk" to "plainswalk." This effect lasts indefinitely.)u003c/Iu003e'},
 'mahamoti-djinn                ': {'card_type': 'Creature', 'kwa': ['Flying'], 'rules': "Flying u003ciu003e(This creature can't be blocked except by creatures with flying or reach.)u003c/iu003e"},
 'mana-short                    ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Tap all lands target player controls and that player loses all unspent mana.'},
 'merfolk-of-the-pearl-trident  ': {'card_type': 'Creature', 'kwa': [], 'rules': 'Oracle'},
 'mesa-pegasus                  ': {'card_type': 'Creature', 'kwa': ['Flying', 'Banding'], 'rules': "Flying; banding u003ciu003e(Any creatures with banding, and up to one without, can attack in a band. Bands are blocked as a group. If any creatures with banding you control are blocking or being blocked by a creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)u003c/iu003e"},
 'mind-bomb                     ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Each player may discard up to three cards. Mind Bomb deals damage to each player equal to 3 minus the number of cards they discarded this way.'},
 'morale                        ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Attacking creatures get +1/+1 until end of turn.'},
 'northern-paladin              ': {'card_type': 'Creature', 'kwa': [], 'rules': '{WW}, {T}: Destroy target black permanent.'},
 'osai-vultures                 ': {'card_type': 'Creature', 'kwa': ['Flying'], 'rules': 'Flying At the beginning of each end step, if a creature died this turn, put a carrion counter on this creature. Remove two carrion counters from this creature: This creature gets +1/+1 until end of turn.'},
 'pearled-unicorn               ': {'card_type': 'Creature', 'kwa': [], 'rules': 'Oracle'},
 'personal-incarnation          ': {'card_type': 'Creature', 'kwa': [], 'rules': '{0}: The next 1 damage that would be dealt to this creature this turn is dealt to its owner instead. Only this creatures owner may activate this ability. When this creature dies, its owner loses half their life, rounded up.'},
 'phantasmal-forces             ': {'card_type': 'Creature', 'kwa': ['Flying'], 'rules': 'Flying At the beginning of your upkeep, sacrifice this creature unless you pay {U}.'},
 'phantasmal-terrain            ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type.'},
 'phantom-monster               ': {'card_type': 'Creature', 'kwa': ['Flying'], 'rules': 'Flying'},
 'piety                         ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Blocking creatures get +0/+3 until end of turn.'},
 'pikemen                       ': {'card_type': 'Creature', 'kwa': ['First Strike', 'Banding'], 'rules': "First strike; banding u003ciu003e(Any creatures with banding, and up to one without, can attack in a band. Bands are blocked as a group. If any creatures with banding you control are blocking or being blocked by a creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)u003c/iu003e"},
 'pirate-ship                   ': {'card_type': 'Creature', 'kwa': ['Islandhome'], 'rules': "This creature can't attack unless defending player controls an Island. {T}: This creature deals 1 damage to any target. When you control no Islands, sacrifice this creature."},
 'power-leak                    ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant enchantment At the beginning of the upkeep of enchanted enchantment's controller, that player may pay any amount of mana. This Aura deals 2 damage to that player. Prevent X of that damage, where X is the amount of mana that player paid this way."},
 'power-sink                    ': {'card_type': 'Instant', 'kwa': [], 'rules': "Counter target spell unless its controller pays {X}. If that player doesn't, they tap all lands with mana abilities they control and lose all unspent mana."},
 'prodigal-sorcerer             ': {'card_type': 'Creature', 'kwa': [], 'rules': '{T}: This creature deals 1 damage to any target.'},
 'psionic-entity                ': {'card_type': 'Creature', 'kwa': [], 'rules': '{T}: This creature deals 2 damage to any target and 3 damage to itself.'},
 'psychic-venom                 ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant land Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller."},
 'purelace                      ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Target spell or permanent becomes white. u003cIu003e(Mana symbols on that permanent remain unchanged.)u003c/Iu003e'},
 'reconstruction                ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Return target artifact card from your graveyard to your hand.'},
 'red-ward                      ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Enchanted creature has protection from red. This effect doesn't remove this Aura."},
 'relic-bind                    ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant artifact an opponent controls Whenever enchanted artifact becomes tapped, choose one - * This Aura deals 1 damage to target player or planeswalker. * Target player gains 1 life.'},
 'resurrection                  ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Return target creature card from your graveyard to the battlefield.'},
 'reverse-damage                ': {'card_type': 'Instant', 'kwa': [], 'rules': 'The next time a source of your choice would deal damage to you this turn, prevent that damage. You gain life equal to the damage prevented this way.'},
 'reverse-polarity              ': {'card_type': 'Instant', 'kwa': [], 'rules': 'You gain X life, where X is twice the damage dealt to you so far this turn by artifacts.'},
 'righteousness                 ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Target blocking creature gets +7/+7 until end of turn.'},
 'samite-healer                 ': {'card_type': 'Creature', 'kwa': [], 'rules': '{T}: Prevent the next 1 damage that would be dealt to any target this turn.'},
 'savannah-lions                ': {'card_type': 'Creature', 'kwa': [], 'rules': 'Oracle'},
 'sea-serpent                   ': {'card_type': 'Creature', 'kwa': ['Islandhome'], 'rules': "This creature can't attack unless defending player controls an Island. When you control no Islands, sacrifice this creature."},
 'seeker                        ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Enchanted creature can't be blocked except by artifact creatures and/or white creatures."},
 'segovian-leviathan            ': {'card_type': 'Creature', 'kwa': ['Islandwalk'], 'rules': "Islandwalk u003ciu003e(This creature can't be blocked as long as defending player controls an Island.)u003c/iu003e"},
 'serendib-efreet               ': {'card_type': 'Creature', 'kwa': ['Flying'], 'rules': 'Flying At the beginning of your upkeep, this creature deals 1 damage to you.'},
 'serra-angel                   ': {'card_type': 'Creature', 'kwa': ['Flying', 'Vigilance'], 'rules': "Flying Vigilance u003ciu003e(Attacking doesn't cause this creature to tap.)u003c/iu003e"},
 'sindbad                       ': {'card_type': 'Creature', 'kwa': [], 'rules': "{T}: Draw a card and reveal it. If it isn't a land card, discard it."},
 'sirens-call                   ': {'card_type': 'Instant', 'kwa': [], 'rules': "Cast this spell only during an opponent's turn, before attackers are declared. Creatures the active player controls attack this turn if able. At the beginning of the next end step, destroy all non-Wall creatures that player controls that didn't attack this turn. Ignore this effect for each creature the player didn't control continuously since the beginning of the turn."},
 'sleight-of-mind               ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Change the text of target spell or permanent by replacing all instances of one color word with another. u003cIu003e(For example, you may change "target black spell" to "target blue spell." This effect lasts indefinitely.)u003c/Iu003e'},
 'spell-blast                   ': {'card_type': 'Instant', 'kwa': [], 'rules': "Counter target spell with mana value X. u003ciu003e(For example, if that spell's mana cost is {3UU}, X is 5.)u003c/iu003e"},
 'spirit-link                   ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant creature u003ciu003e(Target a creature as you cast this. This card enters attached to that creature.)u003c/iu003e Whenever enchanted creature deals damage, you gain that much life.'},
 'stasis                        ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'Players skip their untap steps. At the beginning of your upkeep, sacrifice this enchantment unless you pay {U}.'},
 'steal-artifact                ': {'card_type': 'Aura', 'kwa': [], 'rules': 'Enchant artifact You control enchanted artifact.'},
 'sunken-city                   ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'At the beginning of your upkeep, sacrifice this enchantment unless you pay {UU}. Blue creatures get +1/+1.'},
 'swords-to-plowshares          ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Exile target creature. Its controller gains life equal to its power.'},
 'thoughtlace                   ': {'card_type': 'Instant', 'kwa': [], 'rules': 'Target spell or permanent becomes blue. u003cIu003e(Mana symbols on that permanent remain unchanged.)u003c/Iu003e'},
 'time-elemental                ': {'card_type': 'Creature', 'kwa': [], 'rules': "When this creature attacks or blocks, at end of combat, sacrifice it and it deals 5 damage to you. {2UU}, {T}: Return target permanent that isn't enchanted to its owner's hand."},
 'tundra-wolves                 ': {'card_type': 'Creature', 'kwa': ['First Strike'], 'rules': 'First strike u003ciu003e(This creature deals combat damage before creatures without first strike.)u003c/iu003e'},
 'twiddle                       ': {'card_type': 'Instant', 'kwa': [], 'rules': 'You may tap or untap target artifact, creature, or land.'},
 'unstable-mutation             ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Enchanted creature gets +3/+3. At the beginning of the upkeep of enchanted creature's controller, put a -1/-1 counter on that creature."},
 'unsummon                      ': {'card_type': 'Instant', 'kwa': [], 'rules': "Return target creature to its owner's hand."},
 'vesuvan-doppelganger          ': {'card_type': 'Creature', 'kwa': [], 'rules': 'You may have this creature enter as a copy of any creature on the battlefield, except it doesn\'t copy that creature\'s color and it has "At the beginning of your upkeep, you may have this creature become a copy of target creature, except it doesn\'t copy that creature\'s color and it has this ability."'},
 'veteran-bodyguard             ': {'card_type': 'Creature', 'kwa': [], 'rules': 'As long as this creature is untapped, all damage that would be dealt to you by unblocked creatures is dealt to this creature instead.'},
 'visions                       ': {'card_type': 'Sorcery', 'kwa': [], 'rules': "Look at the top five cards of target player's library. You may then have that player shuffle that library."},
 'volcanic-eruption             ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Destroy X target Mountains. Volcanic Eruption deals damage to each creature and each player equal to the number of Mountains put into a graveyard this way.'},
 'wall-of-air                   ': {'card_type': 'Creature', 'kwa': ['Defender'], 'rules': "Defender, flying u003ciu003e(This creature can't attack, and it can block creatures with flying.)u003c/iu003e"},
 'wall-of-swords                ': {'card_type': 'Creature', 'kwa': ['Defender'], 'rules': "Defender u003ciu003e(This creature can't attack.)u003c/iu003e Flying"},
 'wall-of-water                 ': {'card_type': 'Creature', 'kwa': ['Defender'], 'rules': "Defender u003ciu003e(This creature can't attack.)u003c/iu003e {U}: This creature gets +1/+0 until end of turn."},
 'water-elemental               ': {'card_type': 'Creature', 'kwa': [], 'rules': 'Oracle'},
 'white-knight                  ': {'card_type': 'Creature', 'kwa': ['First Strike', 'Protection from Black'], 'rules': "First strike u003ciu003e(This creature deals combat damage before creatures without first strike.)u003c/iu003e Protection from black u003ciu003e(This creature can't be blocked, targeted, dealt damage, or enchanted by anything black.)u003c/iu003e"},
 'white-ward                    ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant creature Enchanted creature has protection from white. This effect doesn't remove this Aura."},
 'wrath-of-god                  ': {'card_type': 'Sorcery', 'kwa': [], 'rules': "Destroy all creatures. They can't be regenerated."},
 'zephyr-falcon                 ': {'card_type': 'Creature', 'kwa': ['Flying', 'Vigilance'], 'rules': 'Flying, vigilance'}
 }
"""
