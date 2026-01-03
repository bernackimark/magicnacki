import json

if __name__ == '__main__':
    FILE = "card_statuses.json"
    with open(FILE, "r", encoding="utf-8") as f:
        data: dict = json.load(f)

    for k, v in data.items():
        if v['status'] == '':
            print(k, v['type'], v['cc'], v['kwa'], v['rules'])

    # with open(FILE, "w", encoding="utf-8") as f:
    #     json.dump(data, f, indent=2)

"""
Remaining:
-   Identity changers:
        aisling-leprechaun Creature G [] Whenever this creature blocks or becomes blocked by a creature, that creature becomes green.  (This effect lasts indefinitely.)
        alchors-tomb Artifact 4 [] {2}, {T}: Target permanent you control becomes the color of your choice.  (This effect lasts indefinitely.)
        ashnods-transmogrant Artifact 1 [] {T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature. That creature becomes an artifact in addition to its other types.
        blood-moon Enchantment 2R [] Nonbasic lands are Mountains.
        chaoslace Instant R [] Target spell or permanent becomes red.  (Its mana symbols remain unchanged.)
        clone Creature 3U [] You may have this creature enter as a copy of any creature on the battlefield.
        conversion Enchantment 2WW [] At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}. All Mountains are Plains.
        copy-artifact Enchantment 1U [] You may have this enchantment enter as a copy of any artifact on the battlefield, except it's an enchantment in addition to its other types.
        dance-of-many Enchantment UU [] When this enchantment enters, create a token that's a copy of target nontoken creature. When this enchantment leaves the battlefield, exile the token. When the token leaves the battlefield, sacrifice this enchantment. At the beginning of your upkeep, sacrifice this enchantment unless you pay {UU}.
        deathlace Instant B [] Target spell or permanent becomes black.  (Mana symbols on that permanent remain unchanged.)
        deep-water Enchantment UU [] {U}: Until end of turn, if you tap a land you control for mana, it produces {U} instead of any other type.
        dream-coat Aura U [] Enchant creature {0}: Enchanted creature becomes the color or colors of your choice. Activate only once each turn.
        dwarven-song Instant R [] One or more target creatures become red until end of turn.
        evil-presence Aura B [] Enchant land Enchanted land is a Swamp.
        heavens-gate Instant W [] One or more target creatures become white until end of turn.

        phantasmal-terrain: Enchant land As Aura enters, choose a basic land type. Enchanted land is the chosen type
        purelace: Instant Target spell/permanent becomes white. (Mana symbols on that permanent remain unchanged.)
        magical-hack: Change the text of target spell or permanent by replacing all instances of one basic land type with another. u003cIu003e(For example, you may change "swampwalk" to "plainswalk." This effect lasts indefinitely.
        sleight-of-mind: Instant Change the text of target spell or permanent by replacing all instances of one color word with another. u003cIu003e(For example, you may change "target black spell" to "target blue spell." This effect lasts indefinitely.
        thoughtlace: Target spell/permanent becomes blue. u003cIu003e(Mana symbols on that permanent remain unchanged.
        vesuvan-doppelganger: Creature 'You may have this creature enter as a copy of any creature on the battlefield, except it doesn\'t copy that creature\'s color and it has "At the beginning of your upkeep, you may have this creature become a copy of target creature, except it doesn\'t copy that creature\'s color and it has this ability.

 -  Attacking/Blocking Mods:
        army-of-allah Instant 1WW [] Attacking creatures get +2/+0 until end of turn.
        morale: Instant, Attacking creatures get +1/+1 until end of turn  
        piety: Instant, Blocking creatures get +0/+3 until end of turn
        righteousness: Instant, Target blocking creature gets +7/+7 until end of turn
        crimson-manticore Creature 2RR [] Flying {R}, {T}: This creature deals 1 damage to target attacking or blocking creature.
        davenant-archer Creature 2W [] {T}: This creature deals 1 damage to target attacking or blocking creature.
        desert Land None [] {T}: Add {C}. {T}: This land deals 1 damage to target attacking creature. Activate only during the end of combat step.
        disharmony Instant 2R [] Cast this spell only during combat before blockers are declared. Untap target attacking creature and remove it from combat. Gain control of that creature until end of turn.
        ebony-horse Artifact 3 [] {2}, {T}: Untap target attacking creature you control. Prevent all combat damage that would be dealt to and dealt by that creature this turn.
        false-orders Instant R [] Cast this spell only during the declare blockers step. Remove target creature defending player controls from combat. Creatures it was blocking that had become blocked by only that creature this combat become unblocked. You may have it block an attacking creature of your choice.
        feint Instant R [] Tap all creatures blocking target attacking creature. Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it.
        fire-and-brimstone Instant 3WW [] Fire and Brimstone deals 4 damage to target player who attacked this turn and 4 damage to you.
        floral-spuzzem Creature 3G [] Whenever this creature attacks and isn't blocked, you may destroy target artifact defending player controls. If you do, this creature assigns no combat damage this turn.
        giant-shark Creature 5U [] Islandhome  Whenever this creature blocks or becomes blocked by a creature that has been dealt damage this turn, This creature gets +2/+0 and gains trample until end of turn.
        glyph-of-doom Instant B [] Choose target Wall creature. At this turn's next end of combat, destroy all creatures that were blocked by that creature this turn.
        glyph-of-life Instant W [] Choose target Wall creature. Whenever that creature is dealt damage by an attacking creature this turn, you gain that much life.
        glyph-of-reincarnation Instant G [] Cast this spell only after combat. Destroy all creatures that were blocked by target Wall this turn. They can't be regenerated. For each creature that died this way, put a creature card from the graveyard of the player who controlled that creature the last time it became blocked by that Wall onto the battlefield under its owner's control.
        hasran-ogress Creature BB [] Whenever this creature attacks, it deals 3 damage to you unless you pay {2}.
        infernal-medusa Creature 3BB [] Whenever this creature blocks a creature, destroy that creature at end of combat. Whenever this creature becomes blocked by a non-Wall creature, destroy that creature at end of combat.
        infinite-authority Aura WWW [] Enchant creature Whenever enchanted creature blocks or becomes blocked by a creature with toughness 3 or less, destroy the other creature at end of combat. At the beginning of the next end step, if that creature was destroyed this way, put a +1/+1 counter on the first creature.


-   Card Theft / Control:
        aladdin Creature 2RR [] {1RR}, {T}: Gain control of target artifact for as long as you control this creature.
        control-magic Aura 2UU [] Enchant creature You control enchanted creature.
        ghazbán-ogre Creature G [] At the beginning of your upkeep, if a player has more life than each other player, the player with the most life gains control of this creature.

-   Combat End:
        abomination Creature 3BB [] Whenever this creature blocks or becomes blocked by a green or white creature, destroy that creature at end of combat.
        abu-jafar Creature W [] When this creature dies, destroy all creatures blocking or blocked by it. They can't be regenerated.

-   Counter Magic:
        artifact-blast Instant R [] Counter target artifact spell.
        avoid-fate Instant G [] Counter target instant or Aura spell that targets a permanent you control.
        counterspell Instant UU [] Counter target spell.
        deathgrip Enchantment BB [] {BB}: Counter target green spell.
        flash-counter Instant 1U [] Counter target instant spell.
        force-spike Instant U [] Counter target spell unless its controller pays {1}.
        in-the-eye-of-chaos Enchantment 2U [] Whenever a player casts an instant spell, counter it unless that player pays {X}, where X is its mana value.


-   Counter Tokens:
        ashnods-transmogrant Artifact 1 [] {T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature. That creature becomes an artifact in addition to its other types.
        black-mana-battery Artifact 4 [] {2}, {T}: Put a charge counter on this artifact. {T}, Remove any number of charge counters from this artifact: Add {B}, then add an additional {B} for each charge counter removed this way.
        blue-mana-battery Artifact 4 [] {2}, {T}: Put a charge counter on this artifact. {T}, Remove any number of charge counters from this artifact: Add {U}, then add an additional {U} for each charge counter removed this way.
        citanul-druid Creature 1G [] Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature.
        city-of-shadows Land None [] {T}, Exile a creature you control: Put a storage counter on this land. {T}: Add {C} for each storage counter on this land.
        clockwork-avian Artifact 5 ['Flying'] Flying This creature enters with four +1/+0 counters on it. At end of combat, if this creature attacked or blocked this combat, remove a +1/+0 counter from it. {X}, {T}: Put up to X +1/+0 counters on this creature. This ability can't cause the total number of +1/+0 counters on this creature to be greater than four. Activate only during your upkeep.
        clockwork-beast Artifact 6 [] This creature enters with seven +1/+0 counters on it. At end of combat, if this creature attacked or blocked this combat, remove a +1/+0 counter from it. {X}, {T}: Put up to X +1/+0 counters on this creature. This ability can't cause the total number of +1/+0 counters on this creature to be greater than seven. Activate only during your upkeep.
        cocoon Aura G [] Enchant creature you control When this Aura enters, tap enchanted creature and put three pupa counters on this Aura. Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it. At the beginning of your upkeep, remove a pupa counter from this Aura. If you can't, sacrifice it, put a +1/+1 counter on enchanted creature, and that creature gains flying.
        cyclone Enchantment 2GG [] At the beginning of your upkeep, put a wind counter on this enchantment, then sacrifice this enchantment unless you pay {G} for each wind counter on it. If you pay, this enchantment deals damage equal to the number of wind counters on it to each creature and each player.
        cyclopean-tomb Artifact 4 [] {2}, {T}: Put a mire counter on target non-Swamp land. That land is a Swamp for as long as it has a mire counter on it. Activate only during your upkeep. When this artifact is put into a graveyard from the battlefield, at the beginning of each of your upkeeps for the rest of the game, remove all mire counters from a land that a mire counter was put onto with this artifact but that a mire counter has not been removed from with this artifact.
        fasting Enchantment W [] At the beginning of your upkeep, put a hunger counter on this enchantment. Then destroy this enchantment if it has five or more hunger counters on it. If you would begin your draw step, you may skip that step instead. If you do, you gain 2 life. When you draw a card, destroy this enchantment.
        fungusaur Creature 3G [] Whenever this creature is dealt damage, put a +1/+1 counter on it.
        green-mana-battery Artifact 4 [] {2}, {T}: Put a charge counter on this artifact. {T}, Remove any number of charge counters from this artifact: Add {G}, then add an additional {G} for each charge counter removed this way.

        unstable-mutation: Aura gets +3/+3. At the beginning of controller upkeep, put a -1/-1 counter on that creature

-   Deals Damage (combat damage is currently handled in a completely separate place):
        el-hajjâj Creature 1BB [] Whenever this creature deals damage, you gain that much life.
        spirit-link: Aura Whenever enchanted creature deals damage, you gain that much life
        fungusaur Creature 3G [] Whenever this creature is dealt damage, put a +1/+1 counter on it.
        hypnotic-specter Creature 1BB ['Flying'] Flying Whenever this creature deals damage to an opponent, that player discards a card at random.

-   Draw Variability:
        chains-of-mephistopheles Enchantment 1B [] If a player would draw a card except the first one they draw in each of their draw steps, that player discards a card instead. If the player discards a card this way, they draw a card. If the player doesn't discard a card this way, they mill a card.

-   Dual Land:
        badlands Land None [] ({T}: Add {B} or {R}.)
        bayou Land None [] ({T}: Add {B} or {G}.)

-   Global that I can't handle yet (castle & crusade only do PTMod and not even sure that works):
        bone-flute Artifact 3 [] {2}, {T}: All creatures get -1/-0 until end of turn.
        concordant-crossroads Enchantment G [] All creatures have haste.
        crevasse Enchantment 2R [] Creatures with mountainwalk can be blocked as though they didn't have mountainwalk.
        deadfall Enchantment 2G [] Creatures with forestwalk can be blocked as though they didn't have forestwalk.
        gloom Enchantment 2B [] White spells cost {3} more to cast. Activated abilities of white enchantments cost {3} more to activate.
        goblin-caves Aura 1RR [] Enchant land As long as enchanted land is a basic Mountain, Goblin creatures get +0/+2. [* a condition global that's not on_cast()/on_leave()]
        goblin-shrine Aura 1RR [] Enchant land As long as enchanted land is a basic Mountain, Goblin creatures get +1/+0. When this Aura leaves the battlefield, it deals 1 damage to each Goblin creature.
        gravity-sphere Enchantment 2R [] All creatures lose flying.
        great-wall Enchantment 2W [] Creatures with plainswalk can be blocked as though they didn't have plainswalk.
        hell-swarm Instant B [] All creatures get -1/-0 until end of turn.  [* global temp]
        holy-light Instant 2W [] Nonwhite creatures get -1/-1 until end of turn.
        hidden-path Enchantment 2GGGG [] Green creatures have forestwalk.
        ivory-cup Artifact 1 [] Whenever a player casts a white spell, you may pay {1}. If you do, you gain 1 life.


-   Graveyard to Exile:
        eater-of-the-dead Creature 4B [] {0}: If this creature is tapped, exile target creature card from a graveyard and untap this creature.
        frankensteins-monster Creature XBB [] As this creature enters, exile X creature cards from your graveyard. If you can't, put this creature into its owner's graveyard instead of onto the battlefield. ...
        grave-robbers Creature 1BB [] {B}, {T}: Exile target artifact card from a graveyard. You gain 2 life.


-   Hand Reveal:
        amnesia Sorcery 3UUU [] Target player reveals their hand and discards all nonland cards.
        inquisition Sorcery 2B [] Target player reveals their hand. Inquisition deals damage to that player equal to the number of white cards in their hand.


-   Hand Size:
        cursed-rack Artifact 4 [] As this artifact enters, choose an opponent. The chosen player's maximum hand size is four.

-   Hand to Battlefield:
        goblin-wizard Creature 2RR [] {T}: You may put a Goblin permanent card from your hand onto the battlefield. {R}: Target Goblin gains protection from white until end of turn.

-   Indestructible:
        consecrate-land Aura W [] Enchant land Enchanted land has indestructible and can't be enchanted by other Auras.
        guardian-beast Creature 3B [] As long as this creature is untapped, noncreature artifacts you control can't be enchanted, they have indestructible, and other players can't gain control of them. This effect doesn't remove Auras already attached to those artifacts.


-   Life Reduction:
        ali-from-cairo Creature 2RR [] Damage that would reduce your life total to less than 1 reduces it to 1 instead.

-   Next Damage Dealt:
        al-abaras-carpet Artifact 5 [] {5}, {T}: Prevent all damage that would be dealt to you this turn by attacking creatures without flying.
        amulet-of-kroog Artifact 2 [] {2}, {T}: Prevent the next 1 damage that would be dealt to any target this turn.
        argivian-blacksmith Creature 1WW [] {T}: Prevent the next 2 damage that would be dealt to target artifact creature this turn.
        argothian-pixies Creature 1G [] This creature can't be blocked by artifact creatures. Prevent all damage that would be dealt to this creature by artifact creatures.
        argothian-treefolk Creature 3GG [] Prevent all damage that would be dealt to this creature by artifact sources.
        artifact-ward Aura W [] Enchant creature Enchanted creature can't be blocked by artifact creatures. Prevent all damage that would be dealt to enchanted creature by artifact sources. Enchanted creature can't be the target of abilities from artifact sources.
        blood-of-the-martyr Instant WWW [] Until end of turn, if damage would be dealt to any creature, you may have that damage dealt to you instead.
        bronze-horse Artifact 7 [] Trample As long as you control another creature, prevent all damage that would be dealt to this creature by spells that target it.
        circle-of-protection-artifacts Enchantment 1W [] {2}: The next time an artifact source of your choice would deal damage to you this turn, prevent that damage.
        circle-of-protection-black Enchantment 1W [] {1}: The next time a black source of your choice would deal damage to you this turn, prevent that damage.
        circle-of-protection-blue Enchantment 1W [] {1}: The next time a blue source of your choice would deal damage to you this turn, prevent that damage.
        circle-of-protection-green Enchantment 1W [] {1}: The next time a green source of your choice would deal damage to you this turn, prevent that damage.
        circle-of-protection-red Enchantment 1W [] {1}: The next time a red source of your choice would deal damage to you this turn, prevent that damage.
        circle-of-protection-white Enchantment 1W [] {1}: The next time a white source of your choice would deal damage to you this turn, prevent that damage.
        conservator Artifact 4 [] {3}, {T}: Prevent the next 2 damage that would be dealt to you this turn.
        darkness Instant B [] Prevent all combat damage that would be dealt this turn.
        enchanted-being Creature 1WW [] Prevent all combat damage that would be dealt to this creature by enchanted creatures.
        eye-for-an-eye Instant WW [] The next time a source of your choice would deal damage to you this turn, instead that source deals that much damage to you and Eye for an Eye deals that much damage to that source's controller.
        feint Instant R [] Tap all creatures blocking target attacking creature. Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it.
        fog Instant G [] Prevent all combat damage that would be dealt this turn.
        forcefield Artifact 3 [] {1}: The next time an unblocked creature of your choice would deal combat damage to you this turn, prevent all but 1 of that damage.
        gaseous-form Aura 2U [] Enchant creature Prevent all combat damage that would be dealt to and dealt by enchanted creature.guardian-angel Instant Prevent the next X damage that would be dealt to any target this turn. Until end of turn, you may pay {1} any time you could cast an instant. If you do, prevent the next 1 damage that would be dealt to that permanent or player this turn
        greater-realm-of-preservation Enchantment 1W [] {1W}: The next time a black or red source of your choice would deal damage to you this turn, prevent that damage.
        guardian-angel Instant XW [] Prevent the next X damage that would be dealt to any target this turn. Until end of turn, you may pay {1} any time you could cast an instant. If you do, prevent the next 1 damage that would be dealt to that permanent or player this turn.
        healing-salve Instant W [] Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.
        holy-day Instant W [] Prevent all combat damage that would be dealt this turn.
        samite-healer: {T}: Prevent the next 1 damage that would be dealt to any target this turn
        horn-of-deafening Artifact 4 [] {2}, {T}: Prevent all combat damage that would be dealt by target creature this turn.
        indestructible-aura Instant W [] Prevent all damage that would be dealt to target creature this turn.

-   Non-basic Land:  (just need to validate I can only cast one, etc)
        bazaar-of-baghdad Land None [] {T}: Draw two cards, then discard three cards.

-   Protection from Color:
        beasts-of-bogardan Creature 4R [] Protection from red This creature gets +1/+1 as long as an opponent controls a nontoken white permanent.
        black-knight Creature BB ['First Strike', 'Protection from White'] First strike  Protection from white (This creature can't be blocked, targeted, dealt damage, or enchanted by anything white.)
        black-ward Aura W [] Enchant creature Enchanted creature has protection from black. This effect doesn't remove this Aura.
        blue-ward Aura W [] Enchant creature Enchanted creature has protection from blue. This effect doesn't remove this Aura.
        goblin-wizard Creature 2RR [] {T}: You may put a Goblin permanent card from your hand onto the battlefield. {R}: Target Goblin gains protection from white until end of turn.
        green-ward Aura W [] Enchant creature Enchanted creature has protection from green. This effect doesn't remove this Aura.
        ivory-guardians Creature 4WW ['Protection from Red'] Protection from red Creatures named Ivory Guardians get +1/+1 as long as an opponent controls a nontoken red permanent.


        red-ward
        white-knight
        
-   Rampage:
        aerathi-berserker Creature 2RRR [] Rampage 3  (Whenever this creature becomes blocked, it gets +3/+3 until end of turn for each creature blocking it beyond the first.)
        craw-giant Creature 3GGGG [] Trample Rampage 2 (Whenever this creature becomes blocked, it gets +2/+2 until end of turn for each creature blocking it beyond the first.)
        frost-giant Creature 3RRR [] Rampage 2  (Whenever this creature becomes blocked, it gets +2/+2 until end of turn for each creature blocking it beyond the first.)


-   Randomizer Simulation:
        bottle-of-suleiman Artifact 4 [] {1}, Sacrifice this artifact: Flip a coin. If you win the flip, create a 5/5 colorless Djinn artifact creature token with flying. If you lose the flip, this artifact deals 5 damage to you.
        chaos-orb Artifact 2 [] {1}, {T}: If this artifact is on the battlefield, flip it onto the battlefield from a height of at least one foot. If this artifact turns over completely at least once during the flip, destroy all nontoken permanents it touches. Then destroy this artifact.
        coral-helm Artifact 3 [] {3}, Discard a card at random: Target creature gets +2/+2 until end of turn.
        falling-star Sorcery 2R [] Flip Falling Star onto the playing area from a height of at least one foot. Falling Star deals 3 damage to each creature it lands on. Tap all creatures dealt damage by Falling Star. If Falling Star doesn't turn completely over at least once during the flip, it has no effect.
        goblin-artisans Creature R [] {T}: Flip a coin. If you win the flip, draw a card. If you lose the flip, counter target artifact spell you control that isn't the target of an ability from another creature named Goblin Artisans.


-   Reanimate:
        adun-oakenshield Creature BRG [] {BRG}, {T}: Return target creature card from your graveyard to your hand.
        animate-dead Aura 1B [] Enchant creature card in a graveyard When this Aura enters, if it's on the battlefield, it loses "enchant creature card in a graveyard" and gains "enchant creature put onto the battlefield with this Aura." Return enchanted creature card to the battlefield under your control and attach this Aura to it. When this Aura leaves the battlefield, that creature's controller sacrifices it. Enchanted creature gets -1/-0.
        argivian-archaeologist Creature 1WW [] {WW}, {T}: Return target artifact card from your graveyard to your hand.
        drafnas-restoration Sorcery U [] Put any number of target artifact cards from target player's graveyard on top of their library in any order.
        hells-caretaker Creature 3B [] {T}, Sacrifice a creature: Return target creature card from your graveyard to the battlefield. Activate only during your upkeep.


-   Regeneration:
        # Regeneration: does not send creature to graveyard, becomes tapped, all damage is remove from it, and removed from combat (if it was attacking or blocking)
        # Players must apply the regenerate effect BEFORE the permanent would die.
        # If it's a creature in combat, must be done @ declare blockers step (between attackers declared & damage).
        # Non-creature permanents may also sometimes have/get regeneration.
        # Creature doesn't lose its auras, because regeneration prevents creature from being destroyed.
        clay-statue Artifact 4 [] {2}: Regenerate this creature.
        death-ward Instant W [] Regenerate target creature.
        diabolic-machine Artifact 7 [] {3}: Regenerate this creature.
        drowned Creature 1U [] {B}: Regenerate this creature.
        drudge-skeletons Creature 1B [] {B}: Regenerate this creature. (The next time this creature would be destroyed this turn, instead tap it, remove it from combat, and heal all damage on it.)
        elephant-graveyard Land None [] {T}: Add {C}. {T}: Regenerate target Elephant.
        fissure Instant 3RR [] Destroy target creature or land. It can't be regenerated.  [* PREVENTS Re-gen]
        ghost-ship Creature 2UU ['Flying'] Flying {UUU}: Regenerate this creature.
        horror-of-horrors Enchantment 3BB [] Sacrifice a Swamp: Regenerate target black creature.
        hurr-jackal Creature R [] {T}: Target creature can't be regenerated this turn.

-   Sacrifice:
        ashnods-altar Artifact 3 [] Sacrifice a creature: Add {CC}.
        ashnods-transmogrant Artifact 1 [] {T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature. That creature becomes an artifact in addition to its other types.
        atog Creature 1R [] Sacrifice an artifact: This creature gets +2/+2 until end of turn.
        black-lotus Artifact 0 [] {T}, Sacrifice this artifact: Add three mana of any one color.
        coal-golem Artifact 5 [] {3}, Sacrifice this creature: Add {RRR}.
        dark-sphere Artifact 0 [] {T}, Sacrifice this artifact: The next time a source of your choice would deal damage to you this turn, prevent half that damage, rounded down.
        diamond-valley Land None [] {T}, Sacrifice a creature: You gain life equal to the sacrificed creature's toughness.
        dwarven-weaponsmith Creature 1R [] {T}, Sacrifice an artifact: Put a +1/+1 counter on target creature. Activate only during your upkeep.
        elder-spawn Creature 4UUU [] At the beginning of your upkeep, unless you sacrifice an Island, sacrifice this creature and it deals 6 damage to you. This creature can't be blocked by red creatures.
        energy-flux Enchantment 2U [] All artifacts have "At the beginning of your upkeep, sacrifice this artifact unless you pay {2}."
        fallen-angel Creature 3BB ['Flying'] Flying Sacrifice a creature: This creature gets +2/+1 until end of turn.
        feldons-cane Artifact 1 [] {T}, Exile this artifact: Shuffle your graveyard into your library.  [* This is an exile, not a standard sac.]
        gaeas-touch Enchantment GG [] {0}: You may put a basic Forest card from your hand onto the battlefield. Activate only as a sorcery and only once each turn. Sacrifice this enchantment: Add {GG}.
        gate-to-phyrexia Enchantment BB [] Sacrifice a creature: Destroy target artifact. Activate only during your upkeep and only once each turn.
        goblin-digging-team Creature R [] {T}, Sacrifice this creature: Destroy target Wall.
        hells-caretaker Creature 3B [] {T}, Sacrifice a creature: Return target creature card from your graveyard to the battlefield. Activate only during your upkeep.
        horror-of-horrors Enchantment 3BB [] Sacrifice a Swamp: Regenerate target black creature.


-   Search Library:
        demonic-tutor Sorcery 1B [] Search your library for a card, put that card into your hand, then shuffle.

-   Target Multiple Cards:
        ashes-to-ashes Sorcery 1BB [] Exile two target nonartifact creatures. Ashes to Ashes deals 5 damage to you.
        dust-to-dust Sorcery 1WW [] Exile two target artifacts.
        dwarven-song Instant R [] One or more target creatures become red until end of turn.
        fireball Sorcery XR [] This spell costs {1} more to cast for each target beyond the first. Fireball deals X damage divided evenly, rounded down, among any number of targets.


-   Trample:
        angry-mob
        ball-lightning Creature RRR [] Trample  Haste (This creature can attack and {T} as soon as it comes under your control.) At the beginning of the end step, sacrifice this creature.
        bronze-horse Artifact 7 [] Trample As long as you control another creature, prevent all damage that would be dealt to this creature by spells that target it.
        colossus-of-sardia Artifact 9 ['Trample'] Trample  This creature doesn't untap during your untap step. {9}: Untap this creature. Activate only during your upkeep.
        craw-giant Creature 3GGGG [] Trample Rampage 2 (Whenever this creature becomes blocked, it gets +2/+2 until end of turn for each creature blocking it beyond the first.)
        giant-shark Creature 5U [] Islandhome  Whenever this creature blocks or becomes blocked by a creature that has been dealt damage this turn, This creature gets +2/+0 and gains trample until end of turn.


-   Upkeep Conditional:
        conversion Enchantment 2WW [] At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}. All Mountains are Plains.
        cosmic-horror Creature 3BBB ['First Strike'] First strike At the beginning of your upkeep, destroy this creature unless you pay {3BBB}. If this creature is destroyed this way, it deals 7 damage to you.
        curse-artifact Aura 2BB [] Enchant artifact At the beginning of the upkeep of enchanted artifact's controller, this Aura deals 2 damage to that player unless they sacrifice that artifact.
        demonic-hordes Creature 3BBB [] {T}: Destroy target land. At the beginning of your upkeep, unless you pay {BBB}, tap this creature and sacrifice a land of an opponent's choice.
        elder-spawn Creature 4UUU [] At the beginning of your upkeep, unless you sacrifice an Island, sacrifice this creature and it deals 6 damage to you. This creature can't be blocked by red creatures.
        energy-flux Enchantment 2U [] All artifacts have "At the beginning of your upkeep, sacrifice this artifact unless you pay {2}."
        erosion Aura UUU [] Enchant land At the beginning of the upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life.
        force-of-nature Creature 2GGGG [] Trample  At the beginning of your upkeep, this creature deals 8 damage to you unless you pay {GGGG}.
        forethought-amulet Artifact 5 [] At the beginning of your upkeep, sacrifice this artifact unless you pay {3}. If an instant or sorcery source would deal 3 or more damage to you, it deals 2 damage to you instead.


-   Untap as Conditional:
        ashnods-battle-gear Artifact 2 [] You may choose not to untap this artifact during your untap step. {2}, {T}: Target creature you control gets +2/-2 for as long as this artifact remains tapped.
        barls-cage Artifact 4 [] {3}: Target creature doesn't untap during its controller's next untap step.
        basalt-monolith Artifact 3 [] This artifact doesn't untap during your untap step. {T}: Add {CCC}. {3}: Untap this artifact.
        brass-man Artifact 1 [] This creature doesn't untap during your untap step. At the beginning of your upkeep, you may pay {1}. If you do, untap this creature.
        colossus-of-sardia Artifact 9 ['Trample'] Trample  This creature doesn't untap during your untap step. {9}: Untap this creature. Activate only during your upkeep.
        island-fish-jasconius Creature 4UUU [] Islandhome. This creature doesn't untap during your untap step. At the beginning of your upkeep, you may pay {UUU}. If you do, untap this creature.


-   User choice:
        active-volcano Instant R [] Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand.
        alabaster-potion: Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.
        balance: (All users chose) Each player chooses a number of lands they control equal to the number of lands controlled by the player who controls the fewest, then sacrifices the rest. Players discard cards and sacrifice creatures the same way
        birds-of-paradise Creature G [] Flying {T}: Add one mana of any color.
        blue-elemental-blast Instant U [] Choose one - * Counter target red spell. * Destroy target red permanent.
        celestial-prism Artifact 3 [] {2}, {T}: Add one mana of any color.
        city-of-brass Land None [] Whenever this land becomes tapped, it deals 1 damage to you. {T}: Add one mana of any color.
        cuombajj-witches Creature BB [] {T}: This creature deals 1 damage to any target and 1 damage to any target of an opponent's choice.
        dream-coat Aura U [] Enchant creature {0}: Enchanted creature becomes the color or colors of your choice. Activate only once each turn.
        drop-of-honey Enchantment G [] At the beginning of your upkeep, destroy the creature with the least power. It can't be regenerated. If two or more creatures are tied for least power, you choose one of them. When there are no creatures on the battlefield, sacrifice this enchantment.
        dwarven-song Instant R [] One or more target creatures become red until end of turn.
        erhnam-djinn Creature 3G [] At the beginning of your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep. 
        erosion: Enchant land At begin of upkeep of controller, destroy that land unless that player pays {1} or 1 life
        flash-flood Instant U [] Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand.
        frankensteins-monster Creature XBB [] ... For each creature card exiled this way, this creature enters with a +2/+0, +1/+1, or +0/+2 counter on it.
        giant-slug Creature 1B [] {5}: At the beginning of your next upkeep, choose a basic land type. This creature gains landwalk of the chosen type until the end of that turn.
        healing-salve: Instant Choose one - * Target player gains 3 life. * Prevent the next 3 damage that would be dealt to any target this turn.
        ivory-cup Artifact 1 [] Whenever a player casts a white spell, you may pay {1}. If you do, you gain 1 life.
        phantasmal-forces: 'Creature', 'Flying' At begin of your upkeep, sac unless you pay {U}
        sunken-city: Enchantment', At the begin of your upkeep, sac unless you pay {UU}. Blue creatures get +1/+1
        

-   Variable Activation:
        aladdins-lamp Artifact 10 [] {X}, {T}: The next time you would draw a card this turn, instead look at the top X cards of your library, put all but one of them on the bottom of your library in a random order, then draw a card. X can't be 0.
        banshee Creature 2BB [] {X}, {T}: This creature deals half X damage, rounded down, to any target, and half X damage, rounded up, to you.
        candelabra-of-tawnos Artifact 1 [] {X}, {T}: Untap X target lands.

-   Variable cast:
        alabaster-potion: Choose one - * Target player gains X life. * Prevent the next X damage that would be dealt to any target this turn.
        braingeyser Sorcery XUU [] Target player draws X cards.
        detonate Sorcery XR [] Destroy target artifact with mana value X. It can't be regenerated. Detonate deals X damage to that artifact's controller.
        disintegrate Sorcery XR [] Disintegrate deals X damage to any target. If it's a creature, it can't be regenerated this turn, and if it would die this turn, exile it instead.
        drain-life Sorcery X1B [] Spend only black mana on X. Drain Life deals X damage to any target. You gain life equal to the damage dealt, but not more life than the player's life total before the damage was dealt, the planeswalker's loyalty before the damage was dealt, or the creature's toughness.
        earthquake Sorcery XR [] Earthquake deals X damage to each creature without flying and each player.
        howl-from-beyond Instant XB [] Target creature gets +X/+0 until end of turn.
        spell-blast: Instant Counter target spell with mana value X
        hurricane Sorcery XG [] Hurricane deals X damage to each creature with flying and each player.
        
        
-   Variable PT:
        angry-mob: During your turn, Angry Mob's power and toughness are each equal to 2 plus the number of Swamps your opponents control. During turns other than yours, Angry Mob's power and toughness are each 2.
        animate-artifact Aura 3U [] Enchant artifact As long as enchanted artifact isn't a creature, it's an artifact creature with power and toughness each equal to its mana value.   
        aspect-of-wolf Aura 1G [] Enchant creature Enchanted creature gets +X/+Y, where X is half the number of Forests you control, rounded down, and Y is half the number of Forests you control, rounded up.
        cave-people Creature 1RR [] Whenever this creature attacks, it gets +1/-2 until end of turn. {1RR}, {T}: Target creature gains mountainwalk until end of turn. (It can't be blocked as long as defending player controls a Mountain.)
        gaeas-avenger Creature 1GG [] Gaea's Avenger's power and toughness are each equal to 1 plus the number of artifacts your opponents control.
        gaeas-liege Creature 3GGG [] As long as Gaea's Liege isn't attacking, its power and toughness are each equal to the number of Forests you control. As long as Gaea's Liege is attacking, its power and toughness are each equal to the number of Forests defending player controls. {T}: Target land becomes a Forest until this creature leaves the battlefield.

        
-   Unclassified BS:
        all-hallows-eve Sorcery 2BB [] Exile All Hallow's Eve with two scream counters on it. At the beginning of your upkeep, if this card is exiled with a scream counter on it, remove a scream counter from it. If there are no more scream counters on it, put it into your graveyard and each player returns all creature cards from their graveyard to the battlefield.
        ankh-of-mishra Artifact 2 [] Whenever a land enters, this artifact deals 2 damage to that land's controller.
        anti-magic-aura Aura 2U [] Enchant creature Enchanted creature can't be the target of spells and can't be enchanted by other Auras.
        arboria Enchantment 2GG [] Creatures can't attack a player unless that player cast a spell or put a nontoken permanent onto the battlefield during their last turn.
        armageddon-clock Artifact 6 [] At the beginning of your upkeep, put a doom counter on this artifact. At the beginning of your draw step, this artifact deals damage equal to the number of doom counters on it to each player. {4}: Remove a doom counter from this artifact. Any player may activate this ability but only during any upkeep step.
        artifact-possession Aura 2B [] Enchant artifact Whenever enchanted artifact becomes tapped or a player activates an ability of enchanted artifact without {T} in its activation cost, this Aura deals 2 damage to that artifact's controller.
        backdraft Instant 1R [] Choose a player who cast one or more sorcery spells this turn. Backdraft deals damage to that player equal to half the damage dealt by one of those sorcery spells this turn, rounded down.
        balance Sorcery 1W [] Each player chooses a number of lands they control equal to the number of lands controlled by the player who controls the fewest, then sacrifices the rest. Players discard cards and sacrifice creatures the same way.
        berserk Instant G [] Cast this spell only before the combat damage step. Target creature gains trample and gets +X/+0 until end of turn, where X is its power. At the beginning of the next end step, destroy that creature if it attacked this turn.
        black-vise Artifact 1 [] As this artifact enters, choose an opponent. At the beginning of the chosen player's upkeep, this artifact deals X damage to that player, where X is the number of cards in their hand minus 4.
        blaze-of-glory Instant W [] Cast this spell only during combat before blockers are declared. Target creature defending player controls can block any number of creatures this turn. It blocks each attacking creature this turn if able.
        blazing-effigy Creature 1R [] When this creature dies, it deals X damage to target creature, where X is 3 plus the amount of damage dealt to this creature this turn by other sources named Blazing Effigy.
        blight Aura BB [] Enchant land When enchanted land becomes tapped, destroy it.
        brine-hag Creature 2UU [] When this creature dies, change the base power and toughness of all creatures that dealt damage to it this turn to 0/2. (This effect lasts indefinitely.)
        camouflage Instant G [] Cast this spell only during your declare attackers step. This turn, instead of declaring blockers, each defending player chooses any number of creatures they control and divides them into a number of piles equal to the number of attacking creatures for whom that player is the defending player. Creatures those players control that can block additional creatures may likewise be put into additional piles. Assign each pile to a different one of those attacking creatures at random. Each creature in a pile that can block the creature that pile is assigned to does so. (Piles can be empty.)
        caverns-of-despair Enchantment 2RR [] No more than two creatures can attack each combat. No more than two creatures can block each combat.
        chain-lightning Sorcery R [] Chain Lightning deals 3 damage to any target. Then that player or that permanent's controller may pay {RR}. If the player does, they may copy this spell and may choose a new target for that copy.
        channel Sorcery GG [] Until end of turn, any time you could activate a mana ability, you may pay 1 life. If you do, add {C}.  [A sorcery will persistent ability throughout entire turn.]
        city-in-a-bottle Artifact 2 [] Whenever one or more other nontoken permanents with a name originally printed in the Arabian Nights expansion are on the battlefield, their controllers sacrifice them. Players can't cast spells or play lands with a name originally printed in the Arabian Nights expansion.
        cleansing Sorcery WWW [] For each land, destroy that land unless any player pays 1 life.
        clergy-of-the-holy-nimbus Creature W [] If this creature would be destroyed, regenerate it. {1}: This creature can't be regenerated this turn. Only your opponents may activate this ability.
        cockatrice Creature 3GG [] Flying Whenever this creature blocks or becomes blocked by a non-Wall creature, destroy that creature at end of combat.
        crystal-rod Artifact 1 [] Whenever a player casts a blue spell, you may pay {1}. If you do, you gain 1 life.
        cyclopean-mummy Creature 1B [] When this creature dies, exile it.
        damping-field Enchantment 2W [] Players can't untap more than one artifact during their untap steps.
        desert-nomads Creature 2R [] Desertwalk Prevent all damage that would be dealt to this creature by Deserts.
        dingus-egg Artifact 4 [] Whenever a land is put into a graveyard from the battlefield, this artifact deals 2 damage to that land's controller.
        disrupting-scepter Artifact 3 [] {3}, {T}: Target player discards a card. Activate only during your turn.  [i may already have the framework for this]
        dragon-whelp Creature 2RR [] Flying {R}: This creature gets +1/+0 until end of turn. If this ability has been activated four or more times this turn, sacrifice this creature at the beginning of the next end step.
        dwarven-warriors Creature 2R [] {T}: Target creature with power 2 or less can't be blocked this turn.
        elder-land-wurm Creature 4WWW ['Defender', 'Trample'] Defender, trample When this creature blocks, it loses defender.
        enchantment-alteration Instant U [] Attach target Aura attached to a creature or land to another permanent of that type.
        equinox Aura W [] Enchant land Enchanted land has "{T}: Counter target spell if it would destroy a land you control."
        erg-raiders Creature 1B [] At the beginning of your end step, if this creature didn't attack this turn, it deals 2 damage to you unless it came under your control this turn.
        eureka Sorcery 2GG [] Both players may take any permanent in their hand and put it directly into play. Players take turns playing one card from their hand until neither wants to play more permanents. No other spells or effects of any kind may be used while Eureka is in effect. If a spell has an X in its casting cost, X is 0."
        fastbond Enchantment G [] You may play any number of lands on each of your turns. Whenever you play a land, if it wasn't the first land you played this turn, this enchantment deals 1 damage to you.
        fear Aura BB [] Enchant creature  Enchanted creature has fear. (It can't be blocked except by artifact creatures and/or black creatures.)
        fellwar-stone Artifact 2 [] {T}: Add one mana of any color that a land an opponent controls could produce.
        festival Instant W [] Cast this spell only during an opponent's upkeep. Creatures can't attack this turn.
        field-of-dreams Enchantment U [] Players play with the top card of their libraries revealed.
        firestorm-phoenix Creature 4RR [] Flying If this creature would die, return it to its owner's hand instead. Until that player's next turn, that player plays with that card revealed in their hand and can't play it.
        fork Instant RR [] Copy target instant or sorcery spell, except that the copy is red. You may choose new targets for the copy.
        gauntlet-of-might Artifact 4 [] Red creatures get +1/+1. Whenever a Mountain is tapped for mana, its controller adds an additional {R}.
        gauntlets-of-chaos Artifact 5 [] {5}, Sacrifice this artifact: Exchange control of target artifact, creature, or land you control and target permanent an opponent controls that shares one of those types with it. If those permanents are exchanged this way, destroy all Auras attached to them.
        glasses-of-urza Artifact 1 [] {T}: Look at target player's hand.
        giant-turtle Creature 1GG [] This creature can't attack if it attacked during your last turn.
        glyph-of-delusion Instant U [] Put X glyph counters on target creature that target Wall blocked this turn, where X is the power of that blocked creature. The creature gains "This creature doesn't untap during your untap step if it has a glyph counter on it" and "At the beginning of your upkeep, remove a glyph counter from this creature."
        glyph-of-destruction Instant R [] Target blocking Wall you control gets +10/+0 until end of combat. Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step.
        goblin-rock-sled Creature 1R [] Trample This creature doesn't untap during your untap step if it attacked during your last turn. This creature can't attack unless defending player controls a Mountain.
        goblins-of-the-flarg Creature R [] Mountainwalk (This creature can't be blocked as long as defending player controls a Mountain.) When you control a Dwarf, sacrifice this creature.
        golgothian-sylex Artifact 4 [] {1}, {T}: Each nontoken permanent with a name originally printed in the Antiquities expansion is sacrificed by its controller.
        haunting-wind Enchantment 3B [] Whenever an artifact becomes tapped or a player activates an artifact's ability without {T} in its activation cost, this enchantment deals 1 damage to that artifact's controller.
        hellfire Sorcery 2BBB [] Destroy all nonblack creatures. Hellfire deals X plus 3 damage to you, where X is the number of creatures that died this way.  [* The 2nd part needs to wait to see how many creatures actually died this way]
        howling-mine Artifact 2 [] At the beginning of each player's draw step, if this artifact is untapped, that player draws an additional card.
        hurkyls-recall Instant 1U [] Return all artifacts target player owns to their hand.  [cast.py resolve() can't accept a player, only a GameCard]
        ichneumon-druid Creature 1GG [] Whenever an opponent casts an instant spell other than the first instant spell that player casts each turn, this creature deals 4 damage to that player.
        ifh-bíff-efreet Creature 2GG [] Flying {G}: This creature deals 1 damage to each creature with flying and each player. Any player may activate this ability.
        illusionary-mask Artifact 2 [] {X}: You may choose a creature card in your hand whose mana cost could be paid by some amount of, or all of, the mana you spent on {X}. If you do, you may cast that card face down as a 2/2 creature spell without paying its mana cost. If the creature that spell becomes as it resolves has not been turned face up and would assign or deal damage, be dealt damage, or become tapped, instead it's turned face up and assigns or deals damage, is dealt damage, or becomes tapped. Activate only as a sorcery.
        imprison Aura B [] Enchant creature Whenever a player activates an ability of enchanted creature with {T} in its activation cost that isn't a mana ability, you may pay {1}. If you do, counter that ability. If you don't, destroy this Aura. Whenever enchanted creature attacks or blocks, you may pay {1}. If you do, tap the creature, remove it from combat, and creatures it was blocking that had become blocked by only that creature this combat become unblocked. If you don't, destroy this Aura.
        invisibility Aura UU [] Enchant creature Enchanted creature can't be blocked except by Walls.
        invoke-prejudice Enchantment UUUU [] Whenever an opponent casts a creature spell that doesn't share a color with a creature you control, counter that spell unless that player pays {X}, where X is its mana value.
        iron-star Artifact 1 [] Whenever a player casts a red spell, you may pay {1}. If you do, you gain 1 life.
        ironclaw-orcs Creature 1R [] This creature can't block creatures with power 2 or greater.  [* can_block.py actually = "can be blocked"]
        island-of-wak-wak Land None [] {T}: Target creature with flying has base power 0 until end of turn.  [* not actually a PTOffset, it's absolute value]
        island-sanctuary Enchantment 1W [] If you would draw a card during your draw step, instead you may skip that draw. If you do, until your next turn, you can't be attacked except by creatures with flying and/or islandwalk.

"""

"""
jade-monolith Artifact 4 [] {1}: The next time a source of your choice would deal damage to target creature this turn, that source deals that damage to you instead.
jade-statue Artifact 4 [] {2}: This artifact becomes a 3/6 Golem artifact creature until end of combat. Activate only during combat.
jalum-tome Artifact 3 [] {2}, {T}: Draw a card, then discard a card.
jandors-ring Artifact 6 [] {2}, {T}, Discard the last card you drew this turn: Draw a card.
jandors-saddlebags Artifact 2 [] {3}, {T}: Untap target creature.
jayemdae-tome Artifact 4 [] {4}, {T}: Draw a card.
jihad Enchantment WWW [] As this enchantment enters, choose a color and an opponent. White creatures get +2/+1 as long as the chosen player controls a nontoken permanent of the chosen color. When the chosen player controls no nontoken permanents of the chosen color, sacrifice this enchantment.
jovial-evil Sorcery 2B [] Jovial Evil deals X damage to target opponent, where X is twice the number of white creatures that player controls.
juggernaut Artifact 4 [] This creature attacks each combat if able. This creature can't be blocked by Walls.
junún-efreet Creature 1BB ['Flying'] Flying At the beginning of your upkeep, sacrifice this creature unless you pay {BB}.
juxtapose Sorcery 3U [] You and target player exchange control of the creature you each control with the greatest mana value. Then exchange control of artifacts the same way. If two or more permanents a player controls are tied for greatest, their controller chooses one of them.
juzám-djinn Creature 2BB [] At the beginning of your upkeep, this creature deals 1 damage to you.
karakas Land None [] {T}: Add {W}. {T}: Return target legendary creature to its owner's hand.
keldon-warlord Creature 2RR [] Keldon Warlord's power and toughness are each equal to the number of non-Wall creatures you control.
khabál-ghoul Creature 2B [] At the beginning of each end step, put a +1/+1 counter on this creature for each creature that died this turn.
killer-bees Creature 1GG [] Flying {G}: This creature gets +1/+1 until end of turn.
king-suleiman Creature 1W [] {T}: Destroy target Djinn or Efreet.
kird-ape Creature R [] This creature gets +1/+2 as long as you control a Forest.
kismet Enchantment 3W [] Artifacts, creatures, and lands your opponents control enter tapped.
knowledge-vault Artifact 4 [] {2}, {T}: Exile the top card of your library face down. {0}: Sacrifice this artifact. If you do, discard your hand, then put all cards exiled with this artifact into their owner's hand. When this artifact leaves the battlefield, put all cards exiled with it into their owner's graveyard.
kobold-drill-sergeant Creature 1R [] Other Kobold creatures you control get +0/+1 and have trample.
kobold-overlord Creature 1R [] First strike Other Kobold creatures you control have first strike.
kobold-taskmaster Creature 1R [] Other Kobold creatures you control get +1/+0.
kormus-bell Artifact 4 [] All Swamps are 1/1 black creatures that are still lands.
kry-shield Artifact 2 [] {2}, {T}: Prevent all damage that would be dealt this turn by target creature you control. That creature gets +0/+X until end of turn, where X is its mana value.
kudzu Aura 1GG [] Enchant land When enchanted land becomes tapped, destroy it. That land's controller may attach this Aura to a land of their choice.
land-equilibrium Enchantment 2UU [] If an opponent who controls at least as many lands as you do would put a land onto the battlefield, that player instead puts that land onto the battlefield then sacrifices a land of their choice.
land-leeches Creature 1GG [] First strike
land-tax Enchantment W [] At the beginning of your upkeep, if an opponent controls more lands than you, you may search your library for up to three basic land cards, reveal them, put them into your hand, then shuffle.
lands-edge Enchantment 1RR [] Discard a card: If the discarded card was a land card, this enchantment deals 2 damage to target player or planeswalker. Any player may activate this ability.
lesser-werewolf Creature 3B [] {B}: If this creature's power is 1 or more, it gets -1/-0 until end of turn and put a -0/-1 counter on target creature blocking or blocked by this creature. Activate only during the declare blockers step.
leviathan Creature 5UUUU ['Trample'] Trample This creature enters tapped and doesn't untap during your untap step. At the beginning of your upkeep, you may sacrifice two Islands. If you do, untap this creature. This creature can't attack unless you sacrifice two Islands. (This cost is paid as attackers are declared.)
ley-druid Creature 2G [] {T}: Untap target land.
library-of-alexandria Land None [] {T}: Add {C}. {T}: Draw a card. Activate only if you have exactly seven cards in hand.
library-of-leng Artifact 1 [] You have no maximum hand size. If an effect causes you to discard a card, discard it, but you may put it on top of your library instead of into your graveyard.
lich Enchantment BBBB [] As this enchantment enters, you lose life equal to your life total. You don't lose the game for having 0 or less life. If you would gain life, draw that many cards instead. Whenever you're dealt damage, sacrifice that many nontoken permanents. If you can't, you lose the game. When this enchantment is put into a graveyard from the battlefield, you lose the game.
life-chisel Artifact 4 [] Sacrifice a creature: You gain life equal to the sacrificed creature's toughness. Activate only during your upkeep.
life-matrix Artifact 4 [] {4}, {T}: Put a matrix counter on target creature and that creature gains "Remove a matrix counter from this creature: Regenerate this creature." Activate only during your upkeep.
lifeblood Enchantment 2WW [] Whenever a Mountain an opponent controls becomes tapped, you gain 1 life.
lifeforce Enchantment GG [] {GG}: Counter target black spell.
lifelace Instant G [] Target spell or permanent becomes green.  (Mana symbols on that permanent remain unchanged.)
lifetap Enchantment UU [] Whenever a Forest an opponent controls becomes tapped, you gain 1 life.
lightning-bolt Instant R [] Lightning Bolt deals 3 damage to any target.
living-armor Artifact 4 [] {T}, Sacrifice this artifact: Put X +0/+1 counters on target creature, where X is that creature's mana value.
living-artifact Aura G [] Enchant artifact Whenever you're dealt damage, put that many vitality counters on this Aura. At the beginning of your upkeep, you may remove a vitality counter from this Aura. If you do, you gain 1 life.
living-lands Enchantment 3G [] All Forests are 1/1 creatures that are still lands.
living-plane Enchantment 2GG [] All lands are 1/1 creatures that are still lands.
living-wall Artifact 4 ['Defender'] Defender  {1}: Regenerate this creature.
llanowar-elves Creature G [] {T}: Add {G}.
lord-of-the-pit Creature 4BBB ['Flying', 'Trample'] Flying, trample At the beginning of your upkeep, sacrifice a creature other than this creature. If you can't, this creature deals 7 damage to you.
lost-soul Creature 1BB ['Swampwalk'] Swampwalk 
lure Aura 1GG [] Enchant creature All creatures able to block enchanted creature do so.
lurker Creature 2G [] This creature can't be the target of spells unless it attacked or blocked this turn.
magical-hack Instant U [] Change the text of target spell or permanent by replacing all instances of one basic land type with another.  (For example, you may change "swampwalk" to "plainswalk." This effect lasts indefinitely.)
magnetic-mountain Enchantment 1RR [] Blue creatures don't untap during their controllers' untap steps. At the beginning of each player's upkeep, that player may choose any number of tapped blue creatures they control and pay {4} for each creature chosen this way. If the player does, untap those creatures.
mana-clash Sorcery R [] You and target opponent each flip a coin. Mana Clash deals 1 damage to each player whose coin comes up tails. Repeat this process until both players' coins come up heads on the same flip.
mana-drain Instant UU [] Counter target spell. At the beginning of your next main phase, add an amount of {C} equal to that spell's mana value.
mana-flare Enchantment 2R [] Whenever a player taps a land for mana, that player adds one mana of any type that land produced.
mana-matrix Artifact 6 [] Instant and enchantment spells you cast cost {2} less to cast.
mana-vault Artifact 1 [] This artifact doesn't untap during your untap step. At the beginning of your upkeep, you may pay {4}. If you do, untap this artifact. At the beginning of your draw step, if this artifact is tapped, it deals 1 damage to you. {T}: Add {CCC}.
mana-vortex Enchantment 1UU [] When you cast this spell, counter it unless you sacrifice a land. At the beginning of each player's upkeep, that player sacrifices a land of their choice. When there are no lands on the battlefield, sacrifice this enchantment.
manabarbs Enchantment 3R [] Whenever a player taps a land for mana, this enchantment deals 1 damage to that player.
marble-priest Artifact 5 [] All Walls able to block this creature do so. Prevent all combat damage that would be dealt to this creature by Walls.
marsh-gas Instant B [] All creatures get -2/-0 until end of turn.
marsh-viper Creature 3G [] Whenever this creature deals damage to a player, that player gets two poison counters. (A player with ten or more poison counters loses the game.)
martyrs-cry Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card.
martyrs-of-korlis Creature 3WW [] As long as this creature is untapped, all damage that would be dealt to you by artifacts is dealt to this creature instead.
master-of-the-hunt Creature 2GG [] {2GG}: Create a 1/1 green Wolf creature token named Wolves of the Hunt. It has "bands with other creatures named Wolves of the Hunt." (Any creatures named Wolves of the Hunt can attack in a band as long as at least one has "bands with other creatures named Wolves of the Hunt." Bands are blocked as a group. If at least two creatures named Wolves of the Hunt you control, one of which has "bands with other creatures named Wolves of the Hunt," are blocking or being blocked by the same creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)
maze-of-ith Land None [] {T}: Untap target attacking creature. Prevent all combat damage that would be dealt to and dealt by that creature this turn.
meekstone Artifact 1 [] Creatures with power 3 or greater don't untap during their controllers' untap steps.
merchant-ship Creature U [] This creature can't attack unless defending player controls an Island. Whenever this creature attacks and isn't blocked, you gain 2 life. When you control no Islands, sacrifice this creature.
merfolk-assassin Creature UU [] {T}: Destroy target creature with islandwalk.
metamorphosis Sorcery G [] As an additional cost to cast this spell, sacrifice a creature. Add X mana of any one color, where X is 1 plus the sacrificed creature's mana value. Spend this mana only to cast creature spells.
mightstone Artifact 4 [] Attacking creatures get +1/+0.
mijae-djinn Creature RRR [] Whenever this creature attacks, flip a coin. If you lose the flip, remove this creature from combat and tap it.
millstone Artifact 2 [] {2}, {T}: Target player mills two cards.
mind-bomb Sorcery U [] Each player may discard up to three cards. Mind Bomb deals damage to each player equal to 3 minus the number of cards they discarded this way.
mind-twist Sorcery XB [] Target player discards X cards at random.
miracle-worker Creature W [] {T}: Destroy target Aura attached to a creature you control.
mirror-universe Artifact 6 [] {T}, Sacrifice this artifact: Exchange life totals with target opponent. Activate only during your upkeep.
mishras-factory Land None [] {T}: Add {C}. {1}: This land becomes a 2/2 Assembly-Worker artifact creature until end of turn. It's still a land. {T}: Target Assembly-Worker creature gets +1/+1 until end of turn.
mishras-workshop Land None [] {T}: Add {CCC}. Spend this mana only to cast artifact spells.
moat Enchantment 2WW [] Creatures without flying can't attack.
mold-demon Creature 5BB [] When this creature enters, sacrifice it unless you sacrifice two Swamps.
moorish-cavalry Creature 2WW [] Trample
morale Instant 1WW [] Attacking creatures get +1/+1 until end of turn.
mountain-stronghold Land None [] Red legendary creatures you control have "bands with other legendary creatures." (Any legendary creatures can attack in a band as long as at least one has "bands with other legendary creatures." Bands are blocked as a group. If at least two legendary creatures you control, one of which has "bands with other legendary creatures," are blocking or being blocked by the same creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)
mountain-yeti Creature 2RR [] Mountainwalk (This creature can't be blocked as long as defending player controls a Mountain.) Protection from white
mox-emerald Artifact 0 [] {T}: Add {G}.
mox-jet Artifact 0 [] {T}: Add {B}.
mox-pearl Artifact 0 [] {T}: Add {W}.
mox-ruby Artifact 0 [] {T}: Add {R}.
mox-sapphire Artifact 0 [] {T}: Add {U}.
murk-dwellers Creature 3B [] Whenever this creature attacks and isn't blocked, it gets +2/+0 until end of combat.
nafs-asp Creature G [] Whenever this creature deals damage to a player, that player loses 1 life at the beginning of their next draw step unless they pay {1} before that draw step.
nameless-race Creature 3B [] Trample As this creature enters, pay any amount of life. The amount you pay can't be more than the total number of white nontoken permanents your opponents control plus the total number of white cards in their graveyards. Nameless Race's power and toughness are each equal to the life paid as it entered.
natural-selection Instant G [] Look at the top three cards of target player's library, then put them back in any order. You may have that player shuffle.
necropolis Artifact 5 [] Defender  Exile a creature card from your graveyard: Put X +0/+1 counters on this creature, where X is the exiled card's mana value.
nether-shadow Creature BB ['Haste'] Haste At the beginning of your upkeep, if this card is in your graveyard with three or more creature cards above it, you may put this card onto the battlefield.
nether-void Enchantment 3B [] Whenever a player casts a spell, counter it unless that player pays {3}.
nettling-imp Creature 2B [] {T}: Choose target non-Wall creature the active player has controlled continuously since the beginning of the turn. That creature attacks this turn if able. Destroy it at the beginning of the next end step if it didn't attack this turn. Activate only during an opponent's turn, before attackers are declared.
nevinyrrals-disk Artifact 4 [] This artifact enters tapped. {1}, {T}: Destroy all artifacts, creatures, and enchantments.
niall-silvain Creature GGG [] {GGGG}, {T}: Regenerate target creature.
nightmare Creature 5B ['Flying'] Flying  Nightmare's power and toughness are each equal to the number of Swamps you control.
north-star Artifact 4 [] {4}, {T}: For one spell this turn, you may spend mana as though it were mana of any type to pay that spell's mana cost. (Additional costs are still paid normally.)
northern-paladin Creature 2WW [] {WW}, {T}: Destroy target black permanent.
nova-pentacle Artifact 4 [] {3}, {T}: The next time a source of your choice would deal damage to you this turn, that damage is dealt to target creature of an opponent's choice instead.
oasis Land None [] {T}: Prevent the next 1 damage that would be dealt to target creature this turn.
obelisk-of-undoing Artifact 1 [] {6}, {T}: Return target permanent you both own and control to your hand.
obsianus-golem Artifact 6 [] 
old-man-of-the-sea Creature 1UU [] You may choose not to untap this creature during your untap step. {T}: Gain control of target creature with power less than or equal to this creature's power for as long as this creature remains tapped and that creature's power remains less than or equal to this creature's power.
onulet Artifact 3 [] When this creature dies, you gain 2 life.
orc-general Creature 2R [] {T}, Sacrifice another Orc or Goblin: Other Orc creatures get +1/+1 until end of turn.
orcish-artillery Creature 1RR [] {T}: This creature deals 2 damage to any target and 3 damage to you.
orcish-mechanics Creature 2R [] {T}, Sacrifice an artifact: This creature deals 2 damage to any target.
orcish-oriflamme Enchantment 3R [] Attacking creatures you control get +1/+0.
ornithopter Artifact 0 ['Flying'] Flying
osai-vultures Creature 1W ['Flying'] Flying At the beginning of each end step, if a creature died this turn, put a carrion counter on this creature. Remove two carrion counters from this creature: This creature gets +1/+1 until end of turn.
oubliette Enchantment 1BB [] When this enchantment enters, target creature phases out until this enchantment leaves the battlefield. Tap that creature as it phases in this way. (Auras and Equipment phase out with it. While permanents are phased out, they're treated as though they don't exist.)
paralyze Aura B [] Enchant creature When this Aura enters, tap enchanted creature. Enchanted creature doesn't untap during its controller's untap step. At the beginning of the upkeep of enchanted creature's controller, that player may pay {4}. If the player does, untap the creature.
part-water Sorcery XXU [] X target creatures gain islandwalk until end of turn. (They can't be blocked as long as defending player controls an Island.)
pendelhaven Land None [] {T}: Add {G}. {T}: Target 1/1 creature gets +1/+2 until end of turn.
people-of-the-woods Creature GG [] People of the Woods's toughness is equal to the number of Forests you control.
personal-incarnation Creature 3WWW [] {0}: The next 1 damage that would be dealt to this creature this turn is dealt to its owner instead. Only this creatures owner may activate this ability. When this creature dies, its owner loses half their life, rounded up.
pestilence Enchantment 2BB [] At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment. {B}: This enchantment deals 1 damage to each creature and each player.
petra-sphinx Creature 2WWW [] {T}: Target player chooses a card name, then reveals the top card of their library. If that card has the chosen name, that player puts it into their hand. If it doesn't, the player puts it into their graveyard.
phantasmal-forces Creature 3U ['Flying'] Flying At the beginning of your upkeep, sacrifice this creature unless you pay {U}.
phantasmal-terrain Aura UU [] Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type.
phantom-monster Creature 3U ['Flying'] Flying
phyrexian-gremlins Creature 2B [] You may choose not to untap this creature during your untap step. {T}: Tap target artifact. It doesn't untap during its controller's untap step for as long as this creature remains tapped.
piety Instant 2W [] Blocking creatures get +0/+3 until end of turn.
pit-scorpion Creature 2B [] Whenever this creature deals damage to a player, that player gets a poison counter.  (A player with ten or more poison counters loses the game.)
pixie-queen Creature 2GG [] Flying {GGG}, {T}: Target creature gains flying until end of turn.
plague-rats Creature 2B [] Plague Rats's power and toughness are each equal to the number of creatures named Plague Rats on the battlefield.
planar-gate Artifact 6 [] Creature spells you cast cost {2} less to cast.
plateau Land None [] ({T}: Add {R} or {W}.)
power-artifact Aura UU [] Enchant artifact Enchanted artifact's activated abilities cost {2} less to activate. This effect can't reduce the mana in that cost to less than one mana.
power-leak Aura 1U [] Enchant enchantment At the beginning of the upkeep of enchanted enchantment's controller, that player may pay any amount of mana. This Aura deals 2 damage to that player. Prevent X of that damage, where X is the amount of mana that player paid this way.
power-sink Instant XU [] Counter target spell unless its controller pays {X}. If that player doesn't, they tap all lands with mana abilities they control and lose all unspent mana.
power-surge Enchantment RR [] At the beginning of each player's upkeep, this enchantment deals X damage to that player, where X is the number of untapped lands they controlled at the beginning of this turn.
powerleech Enchantment GG [] Whenever an artifact an opponent controls becomes tapped or an opponent activates an artifact's ability without {T} in its activation cost, you gain 1 life.
pradesh-gypsies Creature 2G [] {1G}, {T}: Target creature gets -2/-0 until end of turn.
preacher Creature 1WW [] You may choose not to untap this creature during your untap step. {T}: For as long as this creature remains tapped, gain control of target creature of an opponent's choice they control.
presence-of-the-master Enchantment 3W [] Whenever a player casts an enchantment spell, counter it.
priest-of-yawgmoth Creature 1B [] {T}, Sacrifice an artifact: Add an amount of {B} equal to the sacrificed artifact's mana value.
primal-clay Artifact 4 [] As this creature enters, it becomes your choice of a 3/3 artifact creature, a 2/2 artifact creature with flying, or a 1/6 Wall artifact creature with defender in addition to its other types. (A creature with defender can't attack.)
primordial-ooze Creature R [] This creature attacks each combat if able. At the beginning of your upkeep, put a +1/+1 counter on this creature. Then you may pay {X}, where X is the number of +1/+1 counters on it. If you don't, tap this creature and it deals X damage to you.
psionic-blast Instant 2U [] Psionic Blast deals 4 damage to any target and 2 damage to you.
psychic-allergy Enchantment 3UU [] As this enchantment enters, choose a color. At the beginning of each opponent's upkeep, this enchantment deals X damage to that player, where X is the number of nontoken permanents of the chosen color they control. At the beginning of your upkeep, destroy this enchantment unless you sacrifice two Islands.
psychic-purge Sorcery U [] Psychic Purge deals 1 damage to any target. When a spell or ability an opponent controls causes you to discard this card, that player loses 5 life.
psychic-venom Aura 1U [] Enchant land Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller.
puppet-master Aura UUU [] Enchant creature When enchanted creature dies, return that card to its owner's hand. If that card is returned to its owner's hand this way, you may pay {UUU}. If you do, return this card to its owner's hand.
purelace Instant W [] Target spell or permanent becomes white.  (Mana symbols on that permanent remain unchanged.)
pyramids Artifact 6 [] {2}: Choose one - * Destroy target Aura attached to a land. * The next time target land would be destroyed this turn, remove all damage marked on it instead.
pyrotechnics Sorcery 4R [] Pyrotechnics deals 4 damage divided as you choose among any number of targets.
quagmire Enchantment 2B [] Creatures with swampwalk can be blocked as though they didn't have swampwalk.
quarum-trench-gnomes Creature 3R [] {T}: If target Plains is tapped for mana, it produces colorless mana instead of white mana.  (This effect lasts indefinitely.)
rabid-wombat Creature 2GG [] Vigilance This creature gets +2/+2 for each Aura attached to it.
radjan-spirit Creature 3G [] {T}: Target creature loses flying until end of turn.
rag-man Creature 2BB [] {BBB}, {T}: Target opponent reveals their hand and discards a creature card at random. Activate only during your turn.
raging-river Enchantment RR [] Whenever one or more creatures you control attack, each defending player divides all creatures without flying they control into a "left" pile and a "right" pile. Then, for each attacking creature you control, choose "left" or "right." That creature can't be blocked this combat except by creatures with flying and creatures in a pile with the chosen label.
raise-dead Sorcery B [] Return target creature card from your graveyard to your hand.
rakalite Artifact 6 [] {2}: Prevent the next 1 damage that would be dealt to any target this turn. Return this artifact to its owner's hand at the beginning of the next end step.
rapid-fire Instant 3W [] Cast this spell only before blockers are declared. Target creature gains first strike until end of turn. If it doesn't have rampage, that creature gains rampage 2 until end of turn. (Whenever the creature becomes blocked, it gets +2/+2 until end of turn for each creature blocking it beyond the first.)
recall Sorcery XXU [] 
reconstruction Sorcery U [] Return target artifact card from your graveyard to your hand.
red-elemental-blast Instant R [] Choose one - * Counter target blue spell. * Destroy target blue permanent.
red-mana-battery Artifact 4 [] {2}, {T}: Put a charge counter on this artifact. {T}, Remove any number of charge counters from this artifact: Add {R}, then add an additional {R} for each charge counter removed this way.
red-ward Aura W [] Enchant creature Enchanted creature has protection from red. This effect doesn't remove this Aura.
reflecting-mirror Artifact 4 [] {X}, {T}: Change the target of target spell with a single target if that target is you. The new target must be a player. X is twice the mana value of that spell.
regeneration Aura 1G [] Enchant creature  {G}: Regenerate enchanted creature. (The next time that creature would be destroyed this turn, instead tap it, remove it from combat, and heal all damage on it.)
regrowth Sorcery 1G [] Return target card from your graveyard to your hand.
reincarnation Instant 1GG [] Choose target creature. When that creature dies this turn, return a creature card from its owner's graveyard to the battlefield under the control of that creature's owner.
relic-barrier Artifact 2 [] {T}: Tap target artifact.
relic-bind Aura 2U [] Enchant artifact an opponent controls Whenever enchanted artifact becomes tapped, choose one - * This Aura deals 1 damage to target player or planeswalker. * Target player gains 1 life.
remove-enchantments Instant W [] Return to your hand all enchantments you both own and control, all Auras you own attached to permanents you control, and all Auras you own attached to attacking creatures your opponents control. Then destroy all other enchantments you control, all other Auras attached to permanents you control, and all other Auras attached to attacking creatures your opponents control.
remove-soul Instant 1U [] Counter target creature spell.
repentant-blacksmith Creature 1W ['Protection from Red'] Protection from red
reset Instant UU [] Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control.
resurrection Sorcery 2WW [] Return target creature card from your graveyard to the battlefield.
revelation Enchantment G [] Players play with their hands revealed.
reverberation Instant 2UU [] All damage that would be dealt this turn by target sorcery spell is dealt to that spell's controller instead.
reverse-damage Instant 1WW [] The next time a source of your choice would deal damage to you this turn, prevent that damage. You gain life equal to the damage prevented this way.
reverse-polarity Instant WW [] You gain X life, where X is twice the damage dealt to you so far this turn by artifacts.
righteous-avengers Creature 4W [] Plainswalk (This creature can't be blocked as long as defending player controls a Plains.)
righteousness Instant W [] Target blocking creature gets +7/+7 until end of turn.
ring-of-immortals Artifact 5 [] {3}, {T}: Counter target instant or Aura spell that targets a permanent you control.
ring-of-marûf Artifact 5 [] {5}, {T}, Exile this artifact: The next time you would draw a card this turn, instead put a card you own from outside the game into your hand.
riptide Instant U [] Tap all blue creatures.
roc-of-kher-ridges Creature 3R [] Flying
rock-hydra Creature XRR [] This creature enters with X +1/+1 counters on it. For each 1 damage that would be dealt to this creature, if it has a +1/+1 counter on it, remove a +1/+1 counter from it and prevent that 1 damage. {R}: Prevent the next 1 damage that would be dealt to this creature this turn. {RRR}: Put a +1/+1 counter on this creature. Activate only during your upkeep.
rocket-launcher Artifact 4 [] {2}: This artifact deals 1 damage to any target. Destroy this artifact at the beginning of the next end step. Activate only if you've controlled this artifact continuously since the beginning of your most recent turn.
rod-of-ruin Artifact 4 [] {3}, {T}: This artifact deals 1 damage to any target.
royal-assassin Creature 1BB [] {T}: Destroy target tapped creature.
rukh-egg Creature 3R [] When this creature dies, create a 4/4 red Bird creature token with flying at the beginning of the next end step.
runesword Artifact 6 [] {3}, {T}: Target attacking creature gets +2/+0 until end of turn. When that creature leaves the battlefield this turn, sacrifice this artifact. If the creature deals damage to a creature this turn, the creature dealt damage can't be regenerated this turn. If a creature dealt damage by the targeted creature would die this turn, exile that creature instead.
rust Instant G [] Counter target activated ability from an artifact source. (Mana abilities can't be targeted.)
sacrifice Instant B [] As an additional cost to cast this spell, sacrifice a creature. Add an amount of {B} equal to the sacrificed creature's mana value.
safe-haven Land None [] {2}, {T}: Exile target creature you control. At the beginning of your upkeep, you may sacrifice this land. If you do, return each card exiled with this land to the battlefield under its owner's control.
sage-of-lat-nam Creature 1U [] {T}, Sacrifice an artifact: Draw a card.
samite-healer Creature 1W [] {T}: Prevent the next 1 damage that would be dealt to any target this turn.
sandals-of-abdallah Artifact 4 [] {2}, {T}: Target creature gains islandwalk until end of turn. When that creature dies this turn, destroy this artifact. 
sandstorm Instant G [] Sandstorm deals 1 damage to each attacking creature.
savaen-elves Creature G [] {GG}, {T}: Destroy target Aura attached to a land.
savannah Land None [] ({T}: Add {G} or {W}.)
scarecrow Artifact 5 [] {6}, {T}: Prevent all damage that would be dealt to you this turn by creatures with flying.
scarwood-bandits Creature 2GG [] Forestwalk (This creature can't be blocked as long as defending player controls a Forest.) {2G}, {T}: Unless an opponent pays {2}, gain control of target artifact for as long as this creature remains on the battlefield.
scarwood-hag Creature 1G [] {GGGG}, {T}: Target creature gains forestwalk until end of turn.  {T}: Target creature loses forestwalk until end of turn.
scavenger-folk Creature G [] {G}, {T}, Sacrifice this creature: Destroy target artifact.
scavenging-ghoul Creature 3B [] At the beginning of each end step, put a corpse counter on this creature for each creature that died this turn. Remove a corpse counter from this creature: Regenerate this creature.
scrubland Land None [] ({T}: Add {W} or {B}.)
scryb-sprites Creature G [] Flying
sea-kings-blessing Instant U [] One or more target creatures become blue until end of turn.
seafarers-quay Land None [] Blue legendary creatures you control have "bands with other legendary creatures." (Any legendary creatures can attack in a band as long as at least one has "bands with other legendary creatures." Bands are blocked as a group. If at least two legendary creatures you control, one of which has "bands with other legendary creatures," are blocking or being blocked by the same creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)
season-of-the-witch Enchantment BBB [] At the beginning of your upkeep, sacrifice this enchantment unless you pay 2 life. At the beginning of the end step, destroy all untapped creatures that didn't attack this turn, except for creatures that couldn't attack.
sedge-troll Creature 2R [] This creature gets +1/+1 as long as you control a Swamp. {B}: Regenerate this creature.
sengir-vampire Creature 3BB ['Flying'] Flying  Whenever a creature dealt damage by this creature this turn dies, put a +1/+1 counter on this creature.
sentinel Artifact 4 [] {0}: Change this creature's base toughness to 1 plus the power of target creature blocking or blocked by this creature. (This effect lasts indefinitely.)
serendib-djinn Creature 2UU [] Flying At the beginning of your upkeep, sacrifice a land. If you sacrifice an Island this way, this creature deals 3 damage to you. When you control no lands, sacrifice this creature.
serpent-generator Artifact 6 [] {4}, {T}: Create a 1/1 colorless Snake artifact creature token. It has "Whenever this creature deals damage to a player, that player gets a poison counter." (A player with ten or more poison counters loses the game.)
shanodin-dryads Creature G [] Forestwalk (This creature can't be blocked as long as defending player controls a Forest.)
shapeshifter Artifact 6 [] As this creature enters, choose a number between 0 and 7. At the beginning of your upkeep, you may choose a number between 0 and 7. Shapeshifter's power is equal to the last chosen number and its toughness is equal to 7 minus that number.
shatter Instant 1R [] Destroy target artifact.
shatterstorm Sorcery 2RR [] Destroy all artifacts. They can't be regenerated.
shelkin-brownie Creature 1G [] {T}: Target creature loses all "bands with other" abilities until end of turn.
shield-wall Instant 1W [] Creatures you control get +0/+2 until end of turn.
shimian-night-stalker Creature 3BB [] {B}, {T}: All damage that would be dealt to you this turn by target attacking creature is dealt to this creature instead.
shivan-dragon Creature 4RR [] Flying {R}: This creature gets +1/+0 until end of turn.
silhouette Instant 1U [] Choose target creature. If a spell or ability that targets that creature would cause a source to deal damage to that creature this turn, prevent that damage.
simulacrum Instant 1B [] You gain life equal to the damage dealt to you this turn. Simulacrum deals damage to target creature you control equal to the damage dealt to you this turn.
sindbad Creature 1U [] {T}: Draw a card and reveal it. If it isn't a land card, discard it.
singing-tree Creature 3G [] {T}: Target attacking creature has base power 0 until end of turn.
sinkhole Sorcery BB [] Destroy target land.
sirens-call Instant U [] Cast this spell only during an opponent's turn, before attackers are declared. Creatures the active player controls attack this turn if able. At the beginning of the next end step, destroy all non-Wall creatures that player controls that didn't attack this turn. Ignore this effect for each creature the player didn't control continuously since the beginning of the turn.
sisters-of-the-flame Creature 1RR [] {T}: Add {R}.
skull-of-orm Artifact 3 [] {5}, {T}: Return target enchantment card from your graveyard to your hand.
sleight-of-mind Instant U [] Change the text of target spell or permanent by replacing all instances of one color word with another.  (For example, you may change "target black spell" to "target blue spell." This effect lasts indefinitely.)
smoke Enchantment RR [] Players can't untap more than one creature during their untap steps.
sol-ring Artifact 1 [] {T}: Add {CC}.
sorceress-queen Creature 1BB [] {T}: Target creature other than this creature has base power and toughness 0/2 until end of turn.
sorrows-path Land None [] {T}: Choose two target blocking creatures controlled by the same opponent. If each of those creatures could block all creatures that the other is blocking, remove both of them from combat. Each one then blocks all creatures the other was blocking. Whenever this land becomes tapped, it deals 2 damage to you and each creature you control.
soul-net Artifact 1 [] Whenever a creature dies, you may pay {1}. If you do, you gain 1 life.
spectral-cloak Aura UU [] Enchant creature Enchanted creature has shroud as long as it's untapped. (It can't be the target of spells or abilities.)
spell-blast Instant XU [] Counter target spell with mana value X. (For example, if that spell's mana cost is {3UU}, X is 5.)
spinal-villain Creature 2R [] {T}: Destroy target blue creature.
spirit-link Aura W [] Enchant creature  Whenever enchanted creature deals damage, you gain that much life.
spirit-shackle Aura BB [] Enchant creature Whenever enchanted creature becomes tapped, put a -0/-2 counter on it.
spiritual-sanctuary Enchantment 2WW [] At the beginning of each player's upkeep, if that player controls a Plains, they gain 1 life.
spitting-slug Creature 1GG [] Whenever this creature blocks or becomes blocked, you may pay {1G}. If you do, this creature gains first strike until end of turn. Otherwise, each creature blocking or blocked by this creature gains first strike until end of turn.
staff-of-zegon Artifact 4 [] {3}, {T}: Target creature gets -2/-0 until end of turn.
standing-stones Artifact 3 [] {1}, {T}, Pay 1 life: Add one mana of any color.
stasis Enchantment 1U [] Players skip their untap steps. At the beginning of your upkeep, sacrifice this enchantment unless you pay {U}.
steal-artifact Aura 2UU [] Enchant artifact You control enchanted artifact.
stone-calendar Artifact 5 [] Spells you cast cost {1} less to cast.
stone-giant Creature 2RR [] {T}: Target creature you control with toughness less than this creature's power gains flying until end of turn. Destroy that creature at the beginning of the next end step.
stone-rain Sorcery 2R [] Destroy target land.
stone-throwing-devils Creature B [] First strike
storm-seeker Instant 3G [] Storm Seeker deals damage to target player equal to the number of cards in that player's hand.
storm-world Enchantment R [] At the beginning of each player's upkeep, this enchantment deals X damage to that player, where X is 4 minus the number of cards in their hand.
stream-of-life Sorcery XG [] Target player gains X life.
strip-mine Land None [] {T}: Add {C}. {T}, Sacrifice this land: Destroy target land.
su-chi Artifact 4 [] When this creature dies, add {CCCC}.
subdue Instant G [] Prevent all combat damage that would be dealt by target creature this turn. That creature gets +0/+X until end of turn, where X is its mana value.
sunglasses-of-urza Artifact 3 [] You may spend white mana as though it were red mana.
sunken-city Enchantment UU [] At the beginning of your upkeep, sacrifice this enchantment unless you pay {UU}. Blue creatures get +1/+1.
sword-of-the-ages Artifact 6 [] This artifact enters tapped. {T}, Sacrifice this artifact and any number of creatures you control: This artifact deals X damage to any target, where X is the total power of the creatures sacrificed this way, then exile this artifact and those creature cards.
sylvan-library Enchantment 1G [] At the beginning of your draw step, you may draw two additional cards. If you do, choose two cards in your hand drawn this turn. For each of those cards, pay 4 life or put the card on top of your library.
sylvan-paradise Instant G [] One or more target creatures become green until end of turn.
syphon-soul Sorcery 2B [] Syphon Soul deals 2 damage to each other player. You gain life equal to the damage dealt this way.
tablet-of-epityr Artifact 1 [] Whenever an artifact you control is put into a graveyard from the battlefield, you may pay {1}. If you do, you gain 1 life.
taiga Land None [] ({T}: Add {R} or {G}.)
takklemaggot Aura 2BB [] Enchant creature At the beginning of the upkeep of enchanted creature's controller, put a -0/-1 counter on that creature. When enchanted creature dies, that creature's controller chooses a creature that this card could enchant. If the player does, return this card to the battlefield under your control attached to that creature. If they don't, return this card to the battlefield under your control as a non-Aura enchantment. It loses "enchant creature" and gains "At the beginning of that player's upkeep, this enchantment deals 1 damage to that player."
tangle-kelp Aura U [] Enchant creature When this Aura enters, tap enchanted creature. Enchanted creature doesn't untap during its controller's untap step if it attacked during its controller's last turn.
tawnoss-coffin Artifact 4 [] You may choose not to untap this artifact during your untap step. {3}, {T}: Exile target creature and all Auras attached to it. Note the number and kind of counters that were on that creature. When this artifact leaves the battlefield or becomes untapped, return that exiled card to the battlefield under its owner's control tapped with the noted number and kind of counters on it. If you do, return the other exiled cards to the battlefield under their owner's control attached to that permanent.
tawnoss-wand Artifact 4 [] {2}, {T}: Target creature with power 2 or less can't be blocked this turn.
tawnoss-weaponry Artifact 2 [] You may choose not to untap this artifact during your untap step. {2}, {T}: Target creature gets +1/+1 for as long as this artifact remains tapped.
telekinesis Instant UU [] Tap target creature. Prevent all combat damage that would be dealt by that creature this turn. It doesn't untap during its controller's next two untap steps.
teleport Instant UUU [] Cast this spell only during the declare attackers step. Target creature can't be blocked this turn.
terror Instant 1B [] Destroy target nonartifact, nonblack creature. It can't be regenerated.
tetravus Artifact 6 ['Flying'] Flying This creature enters with three +1/+1 counters on it. At the beginning of your upkeep, you may remove any number of +1/+1 counters from this creature. If you do, create that many 1/1 colorless Tetravite artifact creature tokens. They each have flying and "This token can't be enchanted." At the beginning of your upkeep, you may exile any number of tokens created with this creature. If you do, put that many +1/+1 counters on this creature.
the-abyss Enchantment 3B [] At the beginning of each player's upkeep, destroy target nonartifact creature that player controls of their choice. It can't be regenerated.
the-brute Aura 1R [] Enchant creature Enchanted creature gets +1/+0. {RRR}: Regenerate enchanted creature.
the-fallen Creature 1BBB [] At the beginning of your upkeep, this creature deals 1 damage to each opponent and planeswalker it has dealt damage to this game.
the-hive Artifact 5 [] {5}, {T}: Create a 1/1 colorless Insect artifact creature token with flying named Wasp. (It can't be blocked except by creatures with flying or reach.)
the-rack Artifact 1 [] As this artifact enters, choose an opponent. At the beginning of the chosen player's upkeep, this artifact deals X damage to that player, where X is 3 minus the number of cards in their hand.
the-tabernacle-at-pendrell-vale Land None [] All creatures have "At the beginning of your upkeep, destroy this creature unless you pay {1}."
the-wretched Creature 3BB [] At end of combat, gain control of all creatures blocking this creature for as long as you control this creature.
thicket-basilisk Creature 3GG [] Whenever this creature blocks or becomes blocked by a non-Wall creature, destroy that creature at end of combat.
thoughtlace Instant U [] Target spell or permanent becomes blue. (Mana symbols on that permanent remain unchanged.)
throne-of-bone Artifact 1 [] Whenever a player casts a black spell, you may pay {1}. If you do, you gain 1 life.
thunder-spirit Creature 1WW [] Flying, first strike
time-elemental Creature 2U [] When this creature attacks or blocks, at end of combat, sacrifice it and it deals 5 damage to you. {2UU}, {T}: Return target permanent that isn't enchanted to its owner's hand.
time-vault Artifact 2 [] This artifact enters tapped. This artifact doesn't untap during your untap step. If you would begin your turn while this artifact is tapped, you may skip that turn instead. If you do, untap this artifact. {T}: Take an extra turn after this one.
time-walk Sorcery 1U [] Take an extra turn after this one.
timetwister Sorcery 2U [] Each player shuffles their hand and graveyard into their library, then draws seven cards. (Then put Timetwister into its owner's graveyard.)
titanias-song Enchantment 3G [] Each noncreature artifact loses all abilities and becomes an artifact creature with power and toughness each equal to its mana value. If this enchantment leaves the battlefield, this effect continues until end of turn.
tivadars-crusade Sorcery 1WW [] Destroy all Goblins.
tormods-crypt Artifact 0 [] {T}, Sacrifice this artifact: Exile target player's graveyard.
touch-of-darkness Instant B [] One or more target creatures become black until end of turn.
tower-of-coireall Artifact 2 [] {T}: Target creature can't be blocked by Walls this turn.
tracker Creature 2G [] {GG}, {T}: This creature deals damage equal to its power to target creature. That creature deals damage equal to its power to this creature.
tranquility Sorcery 2G [] Destroy all enchantments.
transmutation Instant 1B [] Switch target creature's power and toughness until end of turn.
transmute-artifact Sorcery UU [] Sacrifice an artifact. If you do, search your library for an artifact card. If that card's mana value is less than or equal to the sacrificed artifact's mana value, put it onto the battlefield. If it's greater, you may pay {X}, where X is the difference. If you do, put it onto the battlefield. If you don't, put it into its owner's graveyard. Then shuffle.
triassic-egg Artifact 4 [] {3}, {T}: Put a hatchling counter on this artifact. Sacrifice this artifact: Choose one. Activate only if there are two or more hatchling counters on this artifact. * You may put a creature card from your hand onto the battlefield. * Return target creature card from your graveyard to the battlefield.
triskelion Artifact 6 [] This creature enters with three +1/+1 counters on it. Remove a +1/+1 counter from this creature: It deals 1 damage to any target.
tropical-island Land None [] ({T}: Add {G} or {U}.)
tsunami Sorcery 3G [] Destroy all Islands.
tundra Land None [] ({T}: Add {W} or {U}.)
tunnel Instant R [] Destroy target Wall. It can't be regenerated.
two-headed-giant-of-foriys Creature 4R [] Trample This creature can block an additional creature each combat.
typhoon Sorcery 2G [] Typhoon deals damage to each opponent equal to the number of Islands that player controls.
uncle-istvan Creature 1BBB [] Prevent all damage that would be dealt to this creature by creatures.
underground-sea Land None [] ({T}: Add {U} or {B}.)
undertow Enchantment 2U [] Creatures with islandwalk can be blocked as though they didn't have islandwalk.
underworld-dreams Enchantment BBB [] Whenever an opponent draws a card, this enchantment deals 1 damage to that player.
unholy-citadel Land None [] Black legendary creatures you control have "bands with other legendary creatures." (Any legendary creatures can attack in a band as long as at least one has "bands with other legendary creatures." Bands are blocked as a group. If at least two legendary creatures you control, one of which has "bands with other legendary creatures," are blocking or being blocked by the same creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking.)
unholy-strength Aura B [] Enchant creature Enchanted creature gets +2/+1.
unstable-mutation Aura U [] Enchant creature Enchanted creature gets +3/+3. At the beginning of the upkeep of enchanted creature's controller, put a -1/-1 counter on that creature.
untamed-wilds Sorcery 2G [] Search your library for a basic land card, put that card onto the battlefield, then shuffle.
urborg Land None [] {T}: Add {B}. {T}: Target creature loses first strike or swampwalk until end of turn.
urzas-avenger Artifact 6 [] {0}: This creature gets -1/-1 and gains your choice of banding, flying, first strike, or trample until end of turn. 
urzas-chalice Artifact 1 [] Whenever a player casts an artifact spell, you may pay {1}. If you do, you gain 1 life.
urzas-mine Land None [] {T}: Add {C}. If you control an Urza's Power-Plant and an Urza's Tower, add {CC} instead.
urzas-miter Artifact 3 [] Whenever an artifact you control is put into a graveyard from the battlefield, if it wasn't sacrificed, you may pay {3}. If you do, draw a card.
urzas-power-plant Land None [] {T}: Add {C}. If you control an Urza's Mine and an Urza's Tower, add {CC} instead.
urzas-tower Land None [] {T}: Add {C}. If you control an Urza's Mine and an Urza's Power-Plant, add {CCC} instead.
uthden-troll Creature 2R [] {R}: Regenerate this creature.
vampire-bats Creature B ['Flying'] Flying  {B}: This creature gets +1/+0 until end of turn. Activate no more than twice each turn.
venarian-gold Aura XUU [] Enchant creature When this Aura enters, tap enchanted creature and put X sleep counters on it. Enchanted creature doesn't untap during its controller's untap step if it has a sleep counter on it. At the beginning of the upkeep of enchanted creature's controller, remove a sleep counter from that creature.
venom Aura 1GG [] Enchant creature Whenever enchanted creature blocks or becomes blocked by a non-Wall creature, destroy the other creature at end of combat.
verduran-enchantress Creature 1GG [] Whenever you cast an enchantment spell, you may draw a card.
vesuvan-doppelganger Creature 3UU [] You may have this creature enter as a copy of any creature on the battlefield, except it doesn't copy that creature's color and it has "At the beginning of your upkeep, you may have this creature become a copy of target creature, except it doesn't copy that creature's color and it has this ability."
veteran-bodyguard Creature 3WW [] As long as this creature is untapped, all damage that would be dealt to you by unblocked creatures is dealt to this creature instead.
visions Sorcery W [] Look at the top five cards of target player's library. You may then have that player shuffle that library.
volcanic-eruption Sorcery XUUU [] Destroy X target Mountains. Volcanic Eruption deals damage to each creature and each player equal to the number of Mountains put into a graveyard this way.
volcanic-island Land None [] ({T}: Add {U} or {R}.)
voodoo-doll Artifact 6 [] At the beginning of your upkeep, put a pin counter on this artifact. At the beginning of your end step, if this artifact is untapped, destroy this artifact and it deals damage to you equal to the number of pin counters on it. {XX}, {T}: This artifact deals damage equal to the number of pin counters on it to any target. X is the number of pin counters on this artifact.
walking-dead Creature 1B [] {B}: Regenerate this creature.
wall-of-bone Creature 2B ['Defender'] Defender  {B}: Regenerate this creature. (The next time this creature would be destroyed this turn, instead tap it, remove it from combat, and heal all damage on it.)
wall-of-brambles Creature 2G [] Defender  {G}: Regenerate this creature.
wall-of-dust Creature 2R [] Defender  Whenever this creature blocks a creature, that creature can't attack during its controller's next turn.
wall-of-earth Creature 1R [] Defender 
wall-of-fire Creature 1RR [] Defender  {R}: This creature gets +1/+0 until end of turn.
wall-of-heat Creature 2R [] Defender 
wall-of-ice Creature 2G [] Defender 
wall-of-light Creature 2W [] Defender  Protection from black
wall-of-opposition Creature 3RR [] Defender  {1}: This creature gets +1/+0 until end of turn.
wall-of-putrid-flesh Creature 2B [] Defender  Protection from white Prevent all damage that would be dealt to this creature by enchanted creatures.
wall-of-shadows Creature 1BB [] Defender  Prevent all damage that would be dealt to this creature by creatures it's blocking. This creature can't be the target of spells that can target only Walls or of abilities that can target only Walls.
wall-of-spears Artifact 3 ['Defender'] Defender  First strike
wall-of-stone Creature 1RR [] Defender 
wall-of-tombstones Creature 1B [] Defender  At the beginning of your upkeep, change this creature's base toughness to 1 plus the number of creature cards in your graveyard.  (This effect lasts indefinitely.)
wall-of-vapor Creature 3U [] Defender  Prevent all damage that would be dealt to this creature by creatures it's blocking.
wall-of-wonder Creature 2UU [] Defender  {2UU}: This creature gets +4/-4 until end of turn and can attack this turn as though it didn't have defender.
wall-of-wood Creature G [] Defender 
wand-of-ith Artifact 4 [] {3}, {T}: Target player reveals a card at random from their hand. If it's a land card, that player discards it unless they pay 1 life. If it isn't a land card, the player discards it unless they pay life equal to its mana value. Activate only during your turn.
wanderlust Aura 2G [] Enchant creature At the beginning of the upkeep of enchanted creature's controller, this Aura deals 1 damage to that player.
war-barge Artifact 4 [] {3}: Target creature gains islandwalk until end of turn. When this artifact leaves the battlefield this turn, destroy that creature. A creature destroyed this way can't be regenerated. 
war-mammoth Creature 3G [] Trample
warp-artifact Aura BB [] Enchant artifact At the beginning of the upkeep of enchanted artifact's controller, this Aura deals 1 damage to that player.
water-wurm Creature U [] This creature gets +0/+1 as long as an opponent controls an Island.
weakness Aura B [] Enchant creature Enchanted creature gets -2/-1.
weakstone Artifact 4 [] Attacking creatures get -1/-0.
web Aura G [] Enchant creature  Enchanted creature gets +0/+2 and has reach. (It can block creatures with flying.)
wheel-of-fortune Sorcery 2R [] Each player discards their hand, then draws seven cards.
whippoorwill Creature G [] {GG}, {T}: Target creature can't be regenerated this turn. Damage that would be dealt to that creature this turn can't be prevented or dealt instead to another permanent or player. When the creature dies this turn, exile the creature.
whirling-dervish Creature GG [] Protection from black At the beginning of each end step, if this creature dealt damage to an opponent this turn, put a +1/+1 counter on it.
white-knight Creature WW ['First Strike', 'Protection from Black'] First strike  Protection from black (This creature can't be blocked, targeted, dealt damage, or enchanted by anything black.)
white-mana-battery Artifact 4 [] {2}, {T}: Put a charge counter on this artifact. {T}, Remove any number of charge counters from this artifact: Add {W}, then add an additional {W} for each charge counter removed this way.
white-ward Aura W [] Enchant creature Enchanted creature has protection from white. This effect doesn't remove this Aura.
wild-growth Aura G [] Enchant land Whenever enchanted land is tapped for mana, its controller adds an additional {G}.
will-o-the-wisp Creature B ['Flying'] Flying  {B}: Regenerate this creature. (The next time this creature would be destroyed this turn, instead tap it, remove it from combat, and heal all damage on it.)
willow-satyr Creature 2GG [] You may choose not to untap this creature during your untap step. {T}: Gain control of target legendary creature for as long as you control this creature and this creature remains tapped.
winds-of-change Sorcery R [] Each player shuffles the cards from their hand into their library, then draws that many cards.
winter-blast Sorcery XG [] Tap X target creatures. Winter Blast deals 2 damage to each of those creatures with flying.
winter-orb Artifact 2 [] As long as this artifact is untapped, players can't untap more than one land during their untap steps.
witch-hunter Creature 2WW [] {T}: This creature deals 1 damage to target player or planeswalker. {1WW}, {T}: Return target creature an opponent controls to its owner's hand.
wolverine-pack Creature 2GG [] Rampage 2  (Whenever this creature becomes blocked, it gets +2/+2 until end of turn for each creature blocking it beyond the first.)
wood-elemental Creature 3G [] As this creature enters, sacrifice any number of untapped Forests. Wood Elemental's power and toughness are each equal to the number of Forests sacrificed as it entered.
wooden-sphere Artifact 1 [] Whenever a player casts a green spell, you may pay {1}. If you do, you gain 1 life.
word-of-binding Sorcery XBB [] Tap X target creatures.
word-of-command Instant BB [] Look at target opponent's hand and choose a card from it. You control that player until Word of Command finishes resolving. The player plays that card if able. While doing so, the player can activate mana abilities only if they're from lands that player controls and only if mana they produce is spent to activate other mana abilities of lands the player controls and/or to play that card. If the chosen card is cast as a spell, you control the player while that spell is resolving.
worms-of-the-earth Enchantment 2BBB [] Players can't play lands. Lands can't enter the battlefield. At the beginning of each upkeep, any player may sacrifice two lands of their choice or have this enchantment deal 5 damage to that player. If a player does either, destroy this enchantment.
wormwood-treefolk Creature 3GG [] {GG}: This creature gains forestwalk until end of turn and deals 2 damage to you.  {BB}: This creature gains swampwalk until end of turn and deals 2 damage to you. (It can't be blocked as long as defending player controls a Swamp.)
wyluli-wolf Creature 1G [] {T}: Target creature gets +1/+1 until end of turn.
xenic-poltergeist Creature 1BB [] {T}: Until your next upkeep, target noncreature artifact becomes an artifact creature with power and toughness each equal to its mana value.
yawgmoth-demon Creature 4BB [] Flying  First strike  At the beginning of your upkeep, you may sacrifice an artifact. If you don't, tap this creature and it deals 2 damage to you.
ydwen-efreet Creature RRR [] Whenever this creature blocks, flip a coin. If you lose the flip, remove this creature from combat and it can't block this turn. Creatures it was blocking that had become blocked by only this creature this combat become unblocked.
zombie-master Creature 1BB [] Other Zombie creatures have swampwalk.  Other Zombies have "{B}: Regenerate this permanent."
"""