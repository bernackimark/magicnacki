from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from constants import BASIC_LANDS
from models.damage import PreventNextDamage
from models.effects.base import Effect
from models.modifiers import PTModifier
from phase_fsm import Phase
from utils import flip


def forest_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            for c in gs.card_filter.on_player_board(s).by_slug('kird-ape').result():
                if len(gs.card_filter.on_player_board(s).by_slug('forest').result()) == 1:  # should this be 0 or 1?
                    for mod in c.modifiers.auras:
                        if mod == PTModifier(c, 1, 2):
                            c.modifiers.remove_aura(mod)
    return E()

def giant_tortoise_on_untap():
    class E(Effect):
        event = 'untap'

        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.modifiers.auras.append(PTModifier(source, 0, 3))
    return E()


# --- COMBAT EFFECTS ---

def islandhome_can_attack_effect():
    class E(Effect):
        event = 'query'   # this aligns with your new "query" dispatch

        def on_query(self, gs: GameState, event: str, **kwargs):
            """event = query name, like 'can_attack', kwargs = includes 'card' when checking if a card can attack"""
            if event != 'can_attack' and not kwargs.get('card'):
                return None

            card = kwargs.get("card")
            if not card or 'Islandhome' not in card.props.keyword_abilities:
                return None

            opp_islands = (gs.card_filter.on_player_board(flip(card.orig_owner_id)).by_slug('island').result())
            return True if opp_islands else False
    return E()


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


def can_block_base_rule():
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: card = blocker, mandatory kwarg: attacker"""
            if event != "can_block":
                return None
            attacker: GameCard = kwargs.get("attacker")
            if not attacker or not card:
                return None

            # Global land walk rule
            defender_idx = card.orig_owner_id
            for walk, basic_land in zip([land.capitalize() + 'walk' for land in BASIC_LANDS], BASIC_LANDS):
                if walk in attacker.keyword_abilities and gs.card_filter.on_player_board(defender_idx).by_slug(basic_land).result():
                    return False

            # Global Flying/Reach rule
            if ('Flying' in attacker.keyword_abilities and
                    not any(kwa for kwa in card.keyword_abilities if kwa in ('Flying', 'Reach'))):
                return False

            return None  # no opinion if can_block ... might need this in case there are other rules added in elsewhere?
    return E()


def gaseous_form_on_cast():
    # TODO: THIS IS ALL DAMAGE ALWAYS.  DO I HANDLE THIS SOMEWHERE IN DAMAGE PREVENTION?
    """Prevent all combat damage that would be dealt this turn by enchanted creature and each creature blocking it."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = the enchanted attacker"""
            the_combat = [com for com in gs.combats if com.attacker == target]
            if not the_combat:
                return
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
            for b in the_combat[0].blockers:
                gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
    return E()


def reset_on_cast():
    """Cast timing restriction"""
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if gs.phase == Phase.UPKEEP or gs.player_turn_idx == source.orig_owner_id:
                raise ValueError("Reset must be played on opponent's turn after their upkeep phase")
            for land in gs.card_filter.on_player_board(source.orig_owner_id).lands().untapped().result():
                land.untap(gs)
    return E()
