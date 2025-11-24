from typing import Optional

from models.effects.base import Effect
from models.modifiers import KWAModifier, KWATemp, PTModifier, PTTemp
from card_filter import CardFilter


def giant_tortoise_on_untap():
    class E(Effect):
        event = 'untap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.modifiers.auras.append(PTModifier(source, 0, 3))
    return E()
