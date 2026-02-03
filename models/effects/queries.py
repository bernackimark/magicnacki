from __future__ import annotations
from typing import TYPE_CHECKING

from models.modifiers import PTModifier, PTTemp, KWAModifier

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect


# --- CARD-SPECIFIC ---
class AmrouKithkin(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = 'amrou-kithkin', mandatory kwargs: blocker"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or card.props.slug != 'amrou-kithkin' or not blocker:
            return None
        if blocker.power > 3:
            return False

class AngelicVoices(Effect):
    """Creatures you control get +1/+1 as long as you control no nonartifact, nonwhite creatures."""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        for my_creature in gs.card_filter.creatures().on_player_board(card.orig_owner_id).result():
            if 'W' not in my_creature.props.colors or 'C' not in my_creature.props.colors:
                return False
        return PTModifier(source, 1, 1)

class ArtifactWardCanBeBlocked(Effect):
    """This creature can't be blocked by artifact creatures"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = the enchanted card, mandatory kwargs: blocker"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or not blocker or not card.modifiers.is_enchanted_by('artifact-ward'):
            return None
        if 'Artifact' in blocker.props.card_types:
            return False

class ArgothianPixiesCanBeBlocked(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = 'argothian-pixies', mandatory kwargs: blocker"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or card.props.slug != 'argothian-pixies' or not blocker:
            return None
        if 'Artifact' in blocker.props.card_types:
            return False

class BadMoon(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().black().creatures().result():
            return None
        return PTModifier(source, 1, 1)

class BogRats(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = 'bog-rats', mandatory kwargs: blocker"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or card.props.slug != 'bog-rats' or not blocker:
            return None
        if 'Wall' in blocker.props.card_sub_types:
            return False

class Castle(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.creatures().on_player_board(card.orig_owner_id).tapped(False).white().result():
            return None
        return PTModifier(source, 0, 2)

class ConcordantCrossroads(Effect):
    """All creatures have haste"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return KWAModifier(source, 'add', 'Haste')

class Crusade(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().white().creatures().result():
            return None
        return PTModifier(source, 1, 1)

class ElderSpawnCanBeBlocked(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = 'elder-spawn', mandatory kwargs: blocker"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or card.props.slug != 'elder-spawn' or not blocker:
            return None
        if 'R' in blocker.props.colors:
            return False

class ElvenRidersCanBeBlocked(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = 'elven-riders', mandatory kwargs: blocker"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or card.props.slug != 'elven-riders' or not blocker:
            return None
        if 'Wall' not in blocker.props.card_sub_types or 'Flying' not in blocker.keyword_abilities:
            return False

class EvilEyeOfOrmsByGoreCanBeBlocked(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = 'EEOOBG', req'd kwargs: blocker. This creature can only be blocked by Walls"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or card.props.slug != 'evil-eye-of-orms-by-gore' or not blocker:
            return None
        if 'Wall' not in blocker.props.card_sub_types:
            return False

class GoblinCaves(Effect):
    """As long as enchanted land is a basic Mountain, Goblin creatures get +0/+2"""
    # WARNING: I don't yet have a way to validate that something is a basic land, since it lives in read-only props
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if source.attached_to.props.is_basic_land and source.attached_to.props.slug == 'mountain':
            if card in gs.card_filter.in_play().creatures().by_sub_type('Goblin').result():
                return PTModifier(source, 0, 2)

class GoblinShrinePump(Effect):
    """As long as enchanted land is a basic Mountain, Goblin creatures get +1/+0 ..."""
    # WARNING: I don't yet have a way to validate that something is a basic land, since it lives in read-only props
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if source.attached_to.props.is_basic_land and source.attached_to.props.slug == 'mountain':
            if card in gs.card_filter.in_play().creatures().by_sub_type('Goblin').result():
                return PTModifier(source, 1, 0)

class GravitySphere(Effect):
    """All creatures lose flying"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return KWAModifier(source, 'remove', 'Flying')

class HiddenPath(Effect):
    """Green creatures have forestwalk"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().green().creatures().result():
            return None
        return KWAModifier(source, 'add', 'Forestwalk')

class KirdApePT(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod' or card.props.slug != 'kird-ape':
            return None

        if gs.card_filter.on_player_board(card.orig_owner_id).by_slug('forest').result():
            return PTModifier(card, 1, 2)

class LordOfAtlantisPT(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return PTModifier(source, 1, 1)
            # card.modifiers.auras.append(KWAModifier(source, 'add', 'Islandwalk'))

class LordOfAtlantisWalk(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return KWAModifier(source, 'add', 'Islandwalk')

class Meekstone(Effect):
    """Creatures with power 3 or greater don't untap during their controllers' untap steps."""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'can_untap':
            return None
        if card.props.is_creature and card.power >= 3:
            return False
        return None


class Mightstone(Effect):
    """Attacking creatures get +1/+0"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.attackers().result():
            return None
        return PTTemp(source, 1, 0)

class Moat(Effect):
    """Creatures without flying can't attack"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().has('Flying', False).creatures().result():
            return None
        return KWAModifier(source, 'remove', 'Attack')

class OrcishOriflamme(Effect):
    """Attacking creatures you control get +1/+0"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.on_player_board(source.orig_owner_id).attackers().result():
            return None
        return PTTemp(source, 1, 0)

class RabidWombat(Effect):
    """This creature gets +2/+2 for each Aura attached to it"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card is not source:
            return None
        aura_cnt = len([a for a in source.modifiers.auras if isinstance(a, GameCard)])
        if not aura_cnt:
            return None
        return PTTemp(source, 2 * aura_cnt, 2 * aura_cnt)

class Seeker(Effect):
    """Enchanted creature can't be blocked except by artifact creatures and/or white creatures"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card should be "seeker's" host, mandatory kwarg: blocker"""
        blocker: GameCard = kwargs.get("blocker")
        if event != "can_be_blocked" or card.attached_to.props.slug != 'seeker' or not blocker:
            return None
        if 'Artifact' not in blocker.props.card_types or 'U' not in blocker.props.colors:
            return False

class SunkenCity(Effect):
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().blue().creatures().result():
            return None
        return PTModifier(source, 1, 1)

class Weakstone(Effect):
    """Attacking creatures get -1/-0"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTTemp(source, -1, 0)
