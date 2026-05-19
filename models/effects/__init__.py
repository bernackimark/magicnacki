"""
There are (currently) three types of Effects:
 - resolvers
   - it can directly execute code the impacts gameplay
   - ex: Lightning Bolt deals damage to a target
   - implements .resolve(gs, source card, target)

 - listeners
   - when an event is raised, it checks each registered listener effect if it should execute code
   - ex: Ali From Cairo listens to LifeLossEvent and adjusts the life total if necessary
   - implements .on_event(gs, source card, event subclass)

 - queriers
   - can be called from a GameCard or ... (not sure if there's other callers)
   - ex: Lord of Atlantis boosts each other Merfolk's PT +1/+1 & grants them Islandwalk
   - returns a Mod for the GameCard that was inquired about

   - can be called from GameState to see if a card (for example) can block / be blocked
   - ex: Juggernaut cannot be blocked by walls
   - returns True, False, or None

   - can execute code
   - ex: Goblins Of The Flarg: When you control a Dwarf, sacrifice this creature
   - returns nothing

   - implements .on_query(gs, event, source card, **kwargs)
   - NOTE: the 'event' arg is a terrible name ... event means something else ... it should be renamed to 'query'

"""