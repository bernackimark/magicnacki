from typing import Optional

class Effect:
    """
    Base class for all card effects.
    Subclasses must set `event` to one of:
      - 'cast'   : when a card is successfully cast (resolve time)
      - 'upkeep' : at upkeep (permanent's upkeep)
      - 'tap'    : when a card becomes tapped
      - 'untap'  : when a card becomes untapped
      - 'leave'  : when the card leaves the battlefield (sent to graveyard/exile)
    And implement resolve(gs, source, target)
    """
    event: str = 'generic'

    def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
        raise NotImplementedError()

