class CardFilter:
    """Filters a list of cards based on chained predicates; does not modify the original list.
    ex usage: card_filter.in_play().creatures().result(); .result() must always be at end of chain to return cards.
    in_play(), on_player_board(p_id), in_graveyards(), in_player_graveyard(p_id), by_slug(slug),
    creatures(), by_type(type_: str | list), by_sub_type(type_: str | list), by_color(color: str | list),
    is_tapped(is_tapped: bool = True), has(kwa: str, bool_: bool = True)"""
    def __init__(self, gs: "GameState"):
        self._gs = gs
        self._cards = self._gs.all_cards

    # --- in what pile, card is located ---
    def in_play(self):
        self._cards = [c for b in self._gs.boards for c in b.cards]
        return self

    def on_player_board(self, p_id: int):
        self._cards = [c for c in self._gs.boards[p_id].cards]
        return self

    def in_graveyards(self):
        self._cards = [c for g in self._gs.graveyards for c in g]
        return self

    def in_player_graveyard(self, p_id: int):
        self._cards = [_ for _ in self._gs.graveyards[p_id]]
        return self

    # --- by slug ---
    def by_slug(self, slug: str):
        self._cards = [c for c in self._cards if c.props.slug == slug]
        return self

    # --- by type/sub-type ---
    def creatures(self):
        self._cards = [c for c in self._cards if 'Creature' in c.props.card_types]
        return self

    def lands(self):
        self._cards = [c for c in self._cards if 'Land' in c.props.card_types]
        return self

    def walls(self):
        self._cards = [c for c in self._cards if 'Wall' in c.props.card_sub_types]
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

    # --- by color ---
    def by_color(self, color: str | list):
        if isinstance(color, list):
            self._cards = [c for c in self._cards for col in color if col in c.props.colors]
        else:
            self._cards = [c for c in self._cards if color in c.props.colors]
        return self

    def white(self):
        self._cards = [c for c in self._cards if 'W' in c.props.colors]
        return self

    def black(self):
        self._cards = [c for c in self._cards if 'B' in c.props.colors]
        return self

    def blue(self):
        self._cards = [c for c in self._cards if 'U' in c.props.colors]
        return self

    def red(self):
        self._cards = [c for c in self._cards if 'R' in c.props.colors]
        return self

    def green(self):
        self._cards = [c for c in self._cards if 'G' in c.props.colors]
        return self

    def is_tapped(self, is_tapped: bool = True):
        self._cards = [c for c in self._cards if c.is_tapped == is_tapped]
        return self

    def has(self, kwa: str, bool_: bool = True):
        if bool_:
            self._cards = [c for c in self._cards if kwa in c.keyword_abilities]
        else:
            self._cards = [c for c in self._cards if kwa not in c.keyword_abilities]
        return self

    def result(self) -> list["GameCard"]:
        cards_to_return = self._cards
        self._cards = self._gs.all_cards  # since self._cards continuously filters, must reset it for subsequent use
        return cards_to_return


"""
Just added, needs testing:
    animate-wall  # this didn't work
    castle
    feedback: Enchant enchantment. Begin of upkeep, enchanted controller, this Aura deals 1 damage to that player
    holy-strength: Aura +1/+2
    karma: Enchantment. Begin of each player's upkeep, deal damage to that player = number of Swamps they control
    lance: Aura Enchanted creature has first strike
    mahamoti-djinn
    psychic-venom: Enchant land Whenever enchanted land becomes tapped, deal 2 damage to that land's controller
    serendib-efreet Flying At the beginning of your upkeep, this creature deals 1 damage to you
    wall-of-swords

Remaining:
-   Target player:
        'braingeyser': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Target player draws X cards.'},
        'mana-short: 'Instant', 'Tap all lands target player controls and that player loses all unspent mana
 
 -  Upkeep cost:
        phantasmal-forces: 'Creature', 'Flying' At begin of your upkeep, sac unless you pay {U}
        sunken-city: Enchantment', At the begin of your upkeep, sac unless you pay {UU}. Blue creatures get +1/+1
 
-   Variable cast:
        alabaster-potion: Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.
        spell-blast: Instant Counter target spell with mana value X

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

-   User choice:
        alabaster-potion: Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.
        balance: (All users chose) Each player chooses a number of lands they control equal to the number of lands controlled by the player who controls the fewest, then sacrifices the rest. Players discard cards and sacrifice creatures the same way
        erosion: Enchant land At begin of upkeep of controller, destroy that land unless that player pays {1} or 1 life
        healing-salve: Instant Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.

-   Variable PT:
        angry-mob: During your turn, Angry Mob's power and toughness are each equal to 2 plus the number of Swamps your opponents control. During turns other than yours, Angry Mob's power and toughness are each 2.

-   Trample:
        angry-mob

-   Conditional Counter:
        brainwash: {'card_type': 'Aura', "Enchanted creature can't attack unless its controller pays {3}."}

-   Regeneration:
        death-ward: Instant: Regenerate target creature

-   Home:
        sea-serpent: Islandhome
        pirate-ship: Islandhome

-   Activated Ability:
        apprentice-wizard: 'Creature', {U}, {T}: Add {CCC}.
        blessing: 'Aura', '{W}: Enchanted creature gets +1/+1 until end of turn.'}
        
        
        flood: 'Enchantment', '{UU}: Tap target creature without flying.'},
        
        will try "Activated Ability" with flood first
        
        
        ghost-ship: ['Flying'], {UUU}: Regenerate this creature.
        northern-paladin: 'creature', {WW}, {T}: Destroy target black permanent
        prodigal-sorcerer: Creature {T}: This creature deals 1 damage to any target
        psionic-entity: 'Creature' {T}: This creature deals 2 damage to any target and 3 damage to itself
        wall-of-water: Defender {U}: This creature gets +1/+0 until end of turn
        farmstead: Enchanted land has "At the beginning of your upkeep, {WW}: you gain 1 life
        holy-armor: Enchant creature gets +0/+2. {W}: Enchanted creature gets +0/+1 until end of turn
        pirate-ship: Creature {T}: This creature deals 1 damage to any target. 
        samite-healer: Creature {T}: Prevent the next 1 damage that would be dealt to any target this turn

-   The next damage dealt:
        COP-black, blue, white: {1}: The next time a _ source of your choice would deal damage to you this turn, prevent
        eye-for-an-eye: Instant The next time a source of your choice would deal damage to you this turn, instead that source deals that much damage to you and Eye for an Eye deals that much damage to that source's controller
        guardian-angel Instant Prevent the next X damage that would be dealt to any target this turn. Until end of turn, you may pay {1} any time you could cast an instant. If you do, prevent the next 1 damage that would be dealt to that permanent or player this turn
        healing-salve: Instant Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.
        samite-healer: {T}: Prevent the next 1 damage that would be dealt to any target this turn

-   Prevent damage:
        gaseous-form: Enchant creature Prevent all combat damage that would be dealt to and dealt by enchanted creature

-   Walk:
        segovian-leviathan: Creature "Islandwalk (can't be blocked as long as defending player controls an Island.)

-   Ward:
        blue-ward, black-ward, white-ward: Enchanted creature has protection from _ color

-   Mana mod:
        energy-tap: 'Sorcery', "Tap target untapped creature you control; add an amount of {C} = its mana value.
 
 -  Missing Phase:
        morale: Instant, Attacking creatures get +1/+1 until end of turn  (There's no casting period after FinishDeclaringAttacker & FinishDeclaringBlockers)
        piety: Instant, Blocking creatures get +0/+3 until end of turn
        righteousness: Instant, Target blocking creature gets +7/+7 until end of turn

-   When damage is dealt:
        spirit-link: Aura Whenever enchanted creature deals damage, you gain that much life.

-   Various:
        add protection-from-black to white-knight
        add vigilance to serra-angel
        LOA: merfolk +1/+1 & islandwalk

-   Intentionally Excluding:
        artifact reliant: animate-artifact, energy-flux, hurkyls-recall, relic-bind, steal-artifact
        banding: benalish-bero, pikemen, fortified-area, mesa-pegasus
        color reliant: blue-elemental-blast, COPs, copy-artifact, green/red ward, conversion, life-tap, volcanic-eruption
"""

"""
{
'drain-power                   ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Target player activates a mana ability of each land they control. Then that player loses all unspent mana and you add the mana lost this way.'},
 'elder-land-wurm               ': {'card_type': 'Creature', 'kwa': ['Defender', 'Trample'], 'rules': 'Defender, trample When this creature blocks, it loses defender.'},
'island-fish-jasconius         ': {'card_type': 'Creature', 'kwa': [], 'rules': "This creature doesn't untap during your untap step. At the beginning of your upkeep, you may pay {UUU}. If you do, untap this creature. This creature can't attack unless defending player controls an Island. When you control no Islands, sacrifice this creature."},
 'island-sanctuary              ': {'card_type': 'Enchantment', 'kwa': [], 'rules': "If you would draw a card during your draw step, instead you may skip that draw. If you do, until your next turn, you can't be attacked except by creatures with flying and/or islandwalk."},
 'kismet                        ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'Artifacts, creatures, and lands your opponents control enter tapped.'},
 'land-tax                      ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'At the beginning of your upkeep, if an opponent controls more lands than you, you may search your library for up to three basic land cards, reveal them, put them into your hand, then shuffle.'},
 'leviathan                     ': {'card_type': 'Creature', 'kwa': ['Trample'], 'rules': "Trample This creature enters tapped and doesn't untap during your untap step. At the beginning of your upkeep, sac 2 islands to untap This creature can't attack unless you sacrifice two Islands. u003ciu003e(This cost is paid as attackers are declared.)u003c/iu003e"},
'mind-bomb                     ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Each player may discard up to three cards. Mind Bomb deals damage to each player equal to 3 minus the number of cards they discarded this way.'},
'osai-vultures                 ': {'card_type': 'Creature', 'kwa': ['Flying'], 'rules': 'Flying At the beginning of each end step, if a creature died this turn, put a carrion counter on this creature. Remove two carrion counters from this creature: This creature gets +1/+1 until end of turn.'},
 'personal-incarnation          ': {'card_type': 'Creature', 'kwa': [], 'rules': '{0}: The next 1 damage that would be dealt to this creature this turn is dealt to its owner instead. Only this creatures owner may activate this ability. When this creature dies, its owner loses half their life, rounded up.'},
'power-leak                    ': {'card_type': 'Aura', 'kwa': [], 'rules': "Enchant enchantment At the beginning of the upkeep of enchanted enchantment's controller, that player may pay any amount of mana. This Aura deals 2 damage to that player. Prevent X of that damage, where X is the amount of mana that player paid this way."},
 'power-sink                    ': {'card_type': 'Instant', 'kwa': [], 'rules': "Counter target spell unless its controller pays {X}. If that player doesn't, they tap all lands with mana abilities they control and lose all unspent mana."},
'resurrection                  ': {'card_type': 'Sorcery', 'kwa': [], 'rules': 'Return target creature card from your graveyard to the battlefield.'},
 'reverse-damage                ': {'card_type': 'Instant', 'kwa': [], 'rules': 'The next time a source of your choice would deal damage to you this turn, prevent that damage. You gain life equal to the damage prevented this way.'},
'sindbad                       ': {'card_type': 'Creature', 'kwa': [], 'rules': "{T}: Draw a card and reveal it. If it isn't a land card, discard it."},
 'sirens-call                   ': {'card_type': 'Instant', 'kwa': [], 'rules': "Cast this spell only during an opponent's turn, before attackers are declared. Creatures the active player controls attack this turn if able. At the beginning of the next end step, destroy all non-Wall creatures that player controls that didn't attack this turn. Ignore this effect for each creature the player didn't control continuously since the beginning of the turn."},
'stasis                        ': {'card_type': 'Enchantment', 'kwa': [], 'rules': 'Players skip their untap steps. At the beginning of your upkeep, sacrifice this enchantment unless you pay {U}.'},
'time-elemental                ': {'card_type': 'Creature', 'kwa': [], 'rules': "When this creature attacks or blocks, at end of combat, sacrifice it and it deals 5 damage to you. {2UU}, {T}: Return target permanent that isn't enchanted to its owner's hand."},
'veteran-bodyguard             ': {'card_type': 'Creature', 'kwa': [], 'rules': 'As long as this creature is untapped, all damage that would be dealt to you by unblocked creatures is dealt to this creature instead.'},
 'visions                       ': {'card_type': 'Sorcery', 'kwa': [], 'rules': "Look at the top five cards of target player's library. You may then have that player shuffle that library."},
}
"""
