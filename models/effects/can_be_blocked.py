from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

def amrou_kithkin_can_be_blocked():
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card = 'amrou-kithkin', mandatory kwargs: blocker"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or card.props.slug != 'amrou-kithkin' or not blocker:
                return None
            if blocker.power > 3:
                return False
    return E()

def artifact_ward_can_be_blocked():
    """This creature can't be blocked by artifact creatures"""
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card = the enchanted card, mandatory kwargs: blocker"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or not blocker or not card.modifiers.is_enchanted_by('artifact-ward'):
                return None
            if 'Artifact' in blocker.props.card_types:
                return False
    return E()

def argothian_pixies_can_be_blocked():
    """This creature can't be blocked by artifact creatures"""
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card = 'argothian-pixies', mandatory kwargs: blocker"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or card.props.slug != 'argothian-pixies' or not blocker:
                return None
            if 'Artifact' in blocker.props.card_types:
                return False
    return E()

def bog_rats_can_be_blocked():
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card = 'bog-rats', mandatory kwargs: blocker"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or card.props.slug != 'bog-rats' or not blocker:
                return None
            if 'Wall' in blocker.props.card_sub_types:
                return False
    return E()

def elder_spawn_can_be_blocked():
    """This creature can't be blocked by red creatures"""
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card = 'elder-spawn', mandatory kwargs: blocker"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or card.props.slug != 'elder-spawn' or not blocker:
                return None
            if 'R' in blocker.props.colors:
                return False
    return E()

def elven_riders_can_be_blocked():
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card = 'elven-riders', mandatory kwargs: blocker"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or card.props.slug != 'elven-riders' or not blocker:
                return None
            if 'Wall' not in blocker.props.card_sub_types or 'Flying' not in blocker.keyword_abilities:
                return False
    return E()

def evil_eye_of_orms_by_gore_can_be_blocked():
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card = 'EEOOBG', req'd kwargs: blocker. This creature can only be blocked by Walls"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or card.props.slug != 'evil-eye-of-orms-by-gore' or not blocker:
                return None
            if 'Wall' not in blocker.props.card_sub_types:
                return False
    return E()

def seeker_enchanted_creature_can_be_blocked():
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: can_block, card should be "seeker's" host, mandatory kwarg: blocker"""
            blocker: GameCard = kwargs.get("blocker")
            if event != "can_be_blocked" or card.attached_to.props.slug != 'seeker' or not blocker:
                return None
            if 'Artifact' not in blocker.props.card_types or 'U' not in blocker.props.colors:
                return False
    return E()
