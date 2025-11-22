from typing import Optional

from models.effects.base import Effect
from models.modifiers import KWAModifier, KWATemp, PTModifier, PTTemp
from card_filter import CardFilter

def castle_on_untap():
    class E(Effect):
        event = 'untap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            # add castle PT modifiers for each castle the controller has
            castles = CardFilter(gs).on_player_board(source.orig_owner_id).by_slug('castle').result()
            count = len(castles)
            if 'W' in getattr(source.props, "colors", []):
                for _ in range(count):
                    source.pt_modifiers.append(PTModifier(source, 0, 2))
    return E()


def giant_tortoise_on_untap():
    class E(Effect):
        event = 'untap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.pt_modifiers.append(PTModifier(source, 0, 3))
    return E()
