from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Effect
from models.utils import flip
from models.phase_manager import Phase

"""
These query-style effects must have a class-level attribute 'query', implement on_query(), and return a bool.
These all ask for permission to do something.
"""


# --- GENERICS ---
class CantBeTargetedByAuras(Effect):
    """Card can't host an aura"""
    query = 'can_target'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        target = card
        if not source or not target or 'Aura' not in source.card_sub_types:
            return
        return False

class HostCantAttack(Effect):
    query = 'can_attack'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if source.attached_to is card:
            return False

class HostCantBeTargetedByAuras(Effect):
    """Host can't host an aura"""
    query = 'can_target'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        target = card
        host: GameCard = kwargs.get('target_host')
        if host is not target or 'Aura' not in source.card_sub_types:
            return
        return False

class NoAttacksAllowedEOT(Effect):
    query = 'can_attack'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        return False

class UnblockableEOT(Effect):
    """Stored in GameState & cleared EOT; target creature can't be blocked this turn"""
    query = 'can_block'

    def __init__(self, target: GameCard):
        self.target = target

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        attacker: GameCard = kwargs.get('attacker')
        if attacker is not self.target:
            return None
        return False

class WalkRuleRemoved(Effect):
    """Creatures with a landwalk can be blocked as though they didn't have that landwalk."""
    query = 'can_block'

    def __init__(self, walk_type: str):
        self.walk_type = walk_type

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        attacker = kwargs.get('attacker')
        if not attacker:
            return None
        if self.walk_type not in attacker.keyword_abilities:
            return None
        return True  # a hard-confirm that the block is allowed

# --- CARD-SPECIFIC ---
class AkronLegionnaire(Effect):
    """Except for creatures named Akron Legionnaire and artifact creatures, creatures you control can't attack"""
    query = 'can_attack'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_attack, card = the subject card"""
        if card not in gs.card_filter.creatures().on_player_board(card.owner_id).result():
            return None
        artifact_creatures = gs.card_filter.on_player_board(card.owner_id).creatures().artifacts().result()
        akron_legionnaires = gs.card_filter.on_player_board(card.owner_id).by_slug('akron-legionnaire').result()
        if card not in artifact_creatures + akron_legionnaires:
            return False

class AmrouKithkin(Effect):
    """This creature can't be blocked by creatures with power 3 or greater"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'amrou-kithkin':
            return None
        if card.power >= 3:
            return False

class ArtifactWardCanBeBlocked(Effect):
    """This creature can't be blocked by artifact creatures"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if 'artifact-ward' not in {a.props.slug for a in attacker.auras}:
            return None
        if 'Artifact' in card.card_types:
            return False

class ArtifactWardCanBeTargeted(Effect):
    """Enchanted creature can't be the target of abilities from artifact sources"""
    query = 'can_target'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        target = card
        if not source or not target or 'artifact-ward' not in {a.props.slug for a in target.auras}:
            return
        if 'Artifact' in source.card_types:
            return False

class ArgothianPixiesCanBeBlocked(Effect):
    """This creature can't be blocked by artifact creatures"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'argothian-pixies':
            return None
        if 'Artifact' in card.props.card_types:
            return False

class BogRats(Effect):
    """This creature can't be blocked by Walls"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'bog-rats':
            return None
        if 'Wall' in card.card_sub_types:
            return False

class CityInABottle(Effect):
    """Players can't cast spells or play lands with a name originally printed in the Arabian Nights expansion"""
    query = 'can_cast'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        if card in gs.card_filter.by_set_code('AN').result():
            return False

class ElderSpawnCanBeBlocked(Effect):
    """This creature can't be blocked by red creatures"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'elder-spawn':
            return None
        if 'R' in card.props.colors:
            return False

class ElvenRidersCanBeBlocked(Effect):
    """This creature can't be blocked except by Walls and/or creatures with flying"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'elven-riders':
            return None
        if 'Wall' not in card.card_sub_types or 'Flying' not in card.keyword_abilities:
            return False

class EvilEyeOfOrmsByGoreCanBeBlocked(Effect):
    """Can only be blocked by walls"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'evil-eye-of-orms-by-gore':
            return None
        if 'Wall' not in card.card_sub_types:
            return False

class EvilEyeOfOrmsByGoreMyNonEyeNoAttack(Effect):
    """Non-Eye creatures you control can't attack."""
    query = 'can_attack'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        if card not in gs.card_filter.on_player_board(card.owner_id).creatures().by_sub_type('Eye').result():
            return False

class Fear(Effect):
    """Enchanted creature has fear. (It can't be blocked except by artifact creatures and/or black creatures.)"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if not card or not attacker.host or attacker.host.props.slug != 'fear':
            return None
        artifact_creatures = gs.card_filter.on_player_board(flip(card.owner_id)).artifacts().creatures().result()
        black_creatures = gs.card_filter.on_player_board(flip(card.owner_id)).black().creatures().result()
        if card not in artifact_creatures + black_creatures:
            return False

class Invisibility(Effect):
    """Enchanted creature can't be blocked except by Walls"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if not attacker.host or attacker.host.props.slug != 'invisibility' or not card:
            return None
        if 'Wall' not in card.card_sub_types:
            return False

class IronclawOrcs(Effect):
    """This creature can't block creatures with power 2 or greater"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = 'ironclaw-orcs', mandatory kwargs: blocker"""
        attacker: GameCard = kwargs.get('attacker')
        if card.props.slug != 'ironclaw-orcs' or not attacker:
            return None
        if attacker.power >= 2:
            return False

class JuggernautUnblockableByWalls(Effect):
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'juggernaut':
            return None
        if card in gs.card_filter.walls().result():
            return False

class LivonyaSilone(Effect):
    """Legendary landwalk (This creature can't be blocked as long as defending player controls a legendary land.)"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'livonya-silone':
            return None
        if gs.card_filter.on_player_board(card.owner_id).legendary().lands().result():
            return False

class Meekstone(Effect):
    """Creatures with power 3 or greater don't untap during their controllers' untap steps."""
    query = 'can_untap'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        if card.props.is_creature and card.power >= 3:
            return False
        return None

class Moat(Effect):
    """Creatures without flying can't attack"""
    query = 'can_attack'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        if card not in gs.card_filter.in_play().has('Flying', False).creatures().result():
            return None
        return False

class Seeker(Effect):
    """Enchanted creature can't be blocked except by artifact creatures and/or white creatures"""
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if not attacker.host or attacker.host.props.slug != 'seeker':
            return None
        if 'Artifact' not in card.card_types or 'U' not in card.colors:
            return False

class SirensCallCanCast(Effect):
    """Cast this spell only during an opponent's turn, before attackers are declared ..."""
    query = 'can_cast'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        if gs.turn_mgr.player_turn_idx == card.owner_id:
            return None
        if gs.phase_mgr.phase >= Phase.DECLARE_ATTACKERS:
            return False

class SpectralCloak(Effect):
    """Enchanted creature has shroud as long as it's untapped. (It can't be the target of spells or abilities.)"""
    query = 'can_target'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        target = card
        host: GameCard = kwargs.get('target_host')
        if host is not target or host.is_tapped:
            return
        return False

class TowerOfCoireallEOT(Effect):
    """Stored in GameState & cleared EOT; target creature can't be blocked by Walls this turn"""
    query = 'can_block'

    def __init__(self, target: GameCard):
        self.target = target

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        attacker: GameCard = kwargs.get('attacker')
        if attacker is not self.target or card not in gs.card_filter.walls().result():
            return None
        return False
