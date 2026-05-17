from __future__ import annotations

import math
from typing import TYPE_CHECKING

from models.modifiers import PTMod, KWAMod, TypeMod, SubTypeMod
from models.utils import flip
from phase_fsm import Phase

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect

# --- GENERICS ---
class CantBeTargetedByAuras(Effect):
    """Card can't host an aura"""
    event = 'can_target'

    def on_query(self, gs: GameState, event: str, **kwargs):
        if event != 'can_target':
            return
        source: GameCard = kwargs.get('source')
        target: GameCard = kwargs.get('card')
        if not source or not target or 'Aura' not in source.card_sub_types:
            return
        return False

class HostCantAttack(Effect):
    def on_query(self, gs: GameState, event: str, **kwargs):
        if event != 'can_attack':
            return None
        card = kwargs.get('card')
        source = kwargs.get('source')
        if source.attached_to is card:
            return False

class HostCantBeTargetedByAuras(Effect):
    """Host can't host an aura"""
    event = 'can_target'

    def on_query(self, gs: GameState, event: str, **kwargs):
        if event != 'can_target':
            return
        source: GameCard = kwargs.get('source')
        target: GameCard = kwargs.get('card')
        host: GameCard = kwargs.get('target_host')
        if host is not target or 'Aura' not in source.card_sub_types:
            return
        return False

# --- CARD-SPECIFIC ---
class AkronLegionnaire(Effect):
    """Except for creatures named Akron Legionnaire and artifact creatures, creatures you control can't attack"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_attack, card = the subject card"""
        if event != 'can_attack':
            return None
        if card not in gs.card_filter.creatures().on_player_board(card.owner_id).result():
            return None
        artifact_creatures = gs.card_filter.on_player_board(card.owner_id).creatures().artifacts().result()
        akron_legionnaires = gs.card_filter.on_player_board(card.owner_id).by_slug('akron-legionnaire').result()
        if card not in artifact_creatures + akron_legionnaires:
            return False

class AmrouKithkin(Effect):
    """This creature can't be blocked by creatures with power 3 or greater"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker.props.slug != 'amrou-kithkin':
            return None
        if card.power >= 3:
            return False

class AngelicVoices(Effect):
    """Creatures you control get +1/+1 as long as you control no nonartifact, nonwhite creatures."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        for my_creature in gs.card_filter.creatures().on_player_board(card.owner_id).result():
            if 'W' not in my_creature.props.colors or 'C' not in my_creature.props.colors:
                return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class AngryMobPT(Effect):
    """During your turn, Angry Mob's power & toughness are each = 2 plus the number of Swamps your opponents control.
    During turns other than yours, Angry Mob's power and toughness are each 2."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return PTMod(s=source, p_adj=2, t_adj=2, expires='EOT')
        opp_swamp_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).swamps().result())
        return PTMod(s=source, p_adj=2 + opp_swamp_cnt, t_adj=2 + opp_swamp_cnt, expires='EOT')

class ArcadesSabbathAllCreaturePump(Effect):
    """... Each untapped creature you control gets +0/+2 as long as it's not attacking ..."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        attackers = gs.card_filter.attackers().result()
        your_untapped_creatures = gs.card_filter.creatures().on_player_board(card.owner_id).tapped(False).result()
        for c in your_untapped_creatures:
            if c not in attackers:
                return PTMod(s=source, t_adj=2)

class ArtifactWardCanBeBlocked(Effect):
    """This creature can't be blocked by artifact creatures"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or 'artifact-ward' not in {a.props.slug for a in attacker.auras}:
            return None
        if 'Artifact' in card.card_types:
            return False

class ArtifactWardCanBeTargeted(Effect):
    """Enchanted creature can't be the target of abilities from artifact sources"""
    event = 'can_target'

    def on_query(self, gs: GameState, event: str, **kwargs):
        if event != 'can_target':
            return
        source: GameCard = kwargs.get('source')
        target: GameCard = kwargs.get('card')
        if not source or not target or 'artifact-ward' not in {a.props.slug for a in target.auras}:
            return
        if 'Artifact' in source.card_types:
            return False

class ArgothianPixiesCanBeBlocked(Effect):
    """This creature can't be blocked by artifact creatures"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker.props.slug != 'argothian-pixies':
            return None
        if 'Artifact' in card.props.card_types:
            return False

class AspectOfWolfPT(Effect):
    """Enchant creature Enchanted creature gets +X/+Y, where X is half the number of Forests you control, rounded down,
    and Y is half the number of Forests you control, rounded up."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source.host:
            return None
        your_forest_cnt = len(gs.card_filter.on_player_board(source.owner_id).forests().result())
        p_adj = math.floor(your_forest_cnt / 2)
        t_adj = math.ceil(your_forest_cnt / 2)
        return PTMod(s=source, p_adj=p_adj, t_adj=t_adj)

class BadMoon(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().black().creatures().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class BeastsOfBogardan(Effect):
    """This creature gets +1/+1 as long as an opponent controls a nontoken white permanent"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card.props.slug != 'beasts-of-bogardan':
            return None
        opp_id = flip(card.owner_id)
        opp_non_token_white_perms = gs.card_filter.on_player_board(opp_id).non_token().white().permanents().result()
        if opp_non_token_white_perms:
            return PTMod(s=source, p_adj=1, t_adj=1)

class BogRats(Effect):
    """This creature can't be blocked by Walls"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker.props.slug != 'bog-rats':
            return None
        if 'Wall' in card.card_sub_types:
            return False

class Castle(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.creatures().on_player_board(card.owner_id).tapped(False).white().result():
            return None
        return PTMod(s=source, t_adj=2)

class CityInABottle(Effect):
    """Players can't cast spells or play lands with a name originally printed in the Arabian Nights expansion"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'can_cast':
            return None
        if card in gs.card_filter.by_set_code('AN').result():
            return False

class ConcordantCrossroads(Effect):
    """All creatures have haste"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return KWAMod(s=source, add_or_remove='add', kwa='Haste')

class Conversion(Effect):
    """All Mountains are Plains"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        s: GameCard = kwargs.get('source')
        if event != 'sub_type_mod':
            return None
        return [SubTypeMod(s=s, add_or_remove='add', card_sub_type='Plains'),
                SubTypeMod(s=s, add_or_remove='remove', card_sub_type='Mountain')]

class Crusade(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().white().creatures().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class DakkonBlackbladePT(Effect):
    """Dakkon Blackblade's power and toughness are each equal to the number of lands you control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        return PTMod(s=source, p_adj=your_land_cnt, t_adj=your_land_cnt)

class ElderSpawnCanBeBlocked(Effect):
    """This creature can't be blocked by red creatures"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker.props.slug != 'elder-spawn':
            return None
        if 'R' in card.props.colors:
            return False

class ElvenRidersCanBeBlocked(Effect):
    """This creature can't be blocked except by Walls and/or creatures with flying"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker.props.slug != 'elven-riders':
            return None
        if 'Wall' not in card.card_sub_types or 'Flying' not in card.keyword_abilities:
            return False

class EvilEyeOfOrmsByGoreCanBeBlocked(Effect):
    """Can only be blocked by walls"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker.props.slug != 'evil-eye-of-orms-by-gore':
            return None
        if 'Wall' not in card.card_sub_types:
            return False

class EvilEyeOfOrmsByGoreMyNonEyeNoAttack(Effect):
    """Non-Eye creatures you control can't attack."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'can_attack':
            return None
        if card not in gs.card_filter.on_player_board(card.owner_id).creatures().by_sub_type('Eye').result():
            return False

class Fear(Effect):
    """Enchanted creature has fear. (It can't be blocked except by artifact creatures and/or black creatures.)"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or not card or not attacker.host or attacker.host.props.slug != 'fear':
            return None
        artifact_creatures = gs.card_filter.on_player_board(flip(card.owner_id)).artifacts().creatures().result()
        black_creatures = gs.card_filter.on_player_board(flip(card.owner_id)).black().creatures().result()
        if card not in artifact_creatures + black_creatures:
            return False

class GaeasAvengerPT(Effect):
    """Gaea's Avenger's power and toughness are each equal to 1 plus the number of artifacts your opponents control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        opp_artifact_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).artifacts().result())
        return PTMod(s=source, p_adj=opp_artifact_cnt + 1, t_adj=opp_artifact_cnt + 1)

class GaeasLiegePT(Effect):
    """As long as Gaea's Liege isn't attacking, its power & toughness are each = the number of Forests you control.
    If Gaea's Liege is attacking, its power & toughness are each = the # of Forests defending player controls."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        is_attacking = card in gs.card_filter.attackers().result()
        if is_attacking:
            cnt = len(gs.card_filter.on_player_board(flip(card.owner_id)).forests().result())
        else:
            cnt = len(gs.card_filter.on_player_board(card.owner_id).forests().result())
        return PTMod(s=source, p_adj=cnt, t_adj=cnt)

class GiantTortoisePT(Effect):
    """This creature gets +0/+3 as long as it's untapped"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        if not card.is_tapped:
            return PTMod(s=source, t_adj=3)

class GoblinCaves(Effect):
    """As long as enchanted land is a basic Mountain, Goblin creatures get +0/+2"""
    # WARNING: I don't yet have a way to validate that something is a basic land, since it lives in read-only props
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if source.host.props.is_basic_land and source.host.props.slug == 'mountain':
            if card in gs.card_filter.in_play().creatures().by_sub_type('Goblin').result():
                return PTMod(s=source, t_adj=2)

class GoblinShrinePump(Effect):
    """As long as enchanted land is a basic Mountain, Goblin creatures get +1/+0 ..."""
    # WARNING: I don't yet have a way to validate that something is a basic land, since it lives in read-only props
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if source.host.props.is_basic_land and source.host.props.slug == 'mountain':
            if card in gs.card_filter.in_play().creatures().by_sub_type('Goblin').result():
                return PTMod(s=source, p_adj=1)

class GoblinsOfTheFlarg(Effect):
    """When you control a Dwarf, sacrifice this creature"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if source.props.slug != 'goblins-of-the-flarg':
            return None

        if gs.card_filter.on_player_board(card.owner_id).by_sub_type('Dwarf').result():
            gs.destroy(source)

class GravitySphere(Effect):
    """All creatures lose flying"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return KWAMod(s=source, add_or_remove='remove', kwa='Flying')

class HiddenPath(Effect):
    """Green creatures have forestwalk"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().green().creatures().result():
            return None
        return KWAMod(s=source, add_or_remove='add', kwa='Forestwalk')

class Invisibility(Effect):
    """Enchanted creature can't be blocked except by Walls"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if (event != 'can_block' or not attacker.host or
                attacker.host.props.slug != 'invisibility' or not card):
            return None
        if 'Wall' not in card.card_sub_types:
            return False

class IronclawOrcs(Effect):
    """This creature can't block creatures with power 2 or greater"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = 'ironclaw-orcs', mandatory kwargs: blocker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or card.props.slug != 'ironclaw-orcs' or not attacker:
            return None
        if attacker.power >= 2:
            return False

class IvoryGuardians(Effect):
    """Creatures named Ivory Guardians get +1/+1 as long as an opponent controls a nontoken red permanent; the pumps are
    cumulative. Ex: if there's two Ivory Guardians & opponent has a nontoken red permanent, each gets +2/+2"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod' or card.props.slug != 'ivory-guardians':
            return None

        ivory_guardians_cnt = len(gs.card_filter.in_play().by_slug('ivory-guardians').result())

        if gs.card_filter.on_player_board(flip(card.owner_id)).non_token().red().permanents().result():
            return PTMod(s=card, p_adj=ivory_guardians_cnt, t_adj=ivory_guardians_cnt)

class JacquesLeVert(Effect):
    """Green creatures you control get +0/+2"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.on_player_board(source.owner_id).green().creatures().result():
            return None
        return PTMod(s=source, t_adj=2)

class JuggernautUnblockableByWalls(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get("attacker")
        if event != 'can_block' or attacker.props.slug != 'juggernaut':
            return None
        if card in gs.card_filter.walls().result():
            return False

class KeldonWarlordPT(Effect):
    """Keldon Warlord's power and toughness are each equal to the number of non-Wall creatures you control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        your_non_wall_creature_cnt = len(gs.card_filter.on_player_board(card.owner_id).non_wall_creatures().result())
        return PTMod(s=source, p_adj=your_non_wall_creature_cnt, t_adj=your_non_wall_creature_cnt)

class KirdApePT(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod' or card.props.slug != 'kird-ape':
            return None

        if gs.card_filter.on_player_board(card.owner_id).forests().result():
            return PTMod(s=card, p_adj=1, t_adj=2)

class KoboldOverlord(Effect):
    """Other Kobold creatures you control have first strike"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'kwa_mod':
            return None
        source: GameCard = kwargs.get('source')
        if source.props.slug != 'kobold-overlord' or card is source:
            return
        if card in gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Kobold').result():
            return KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT')

class KoboldTaskmaster(Effect):
    """Other Kobold creatures you control get +1/+0"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod':
            return None
        source: GameCard = kwargs.get('source')
        if source.props.slug != 'kobold-taskmaster' or card is source:
            return
        if card in gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Kobold').result():
            return PTMod(s=source, p_adj=1)

class KormusBell(Effect):
    """All Swamps are 1/1 creatures that are still lands"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().by_sub_type('Swamp').result():
            return None
        if event == 'type_mod':
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if event == 'pt_mod':
            return PTMod(s=source, p_adj=1, t_adj=1)
        return None

class LivingLands(Effect):
    """All Forests are 1/1 creatures that are still lands"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().by_sub_type('Forest').result():
            return None
        if event == 'type_mod':
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if event == 'pt_mod':
            return PTMod(s=source, p_adj=1, t_adj=1)
        return None

class LivingPlane(Effect):
    """All lands are 1/1 creatures that are still lands"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().by_sub_type('Land').result():
            return None
        if event == 'type_mod':
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if event == 'pt_mod':
            return PTMod(s=source, p_adj=1, t_adj=1)
        return None

class LivonyaSilone(Effect):
    """Legendary landwalk (This creature can't be blocked as long as defending player controls a legendary land.)"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        if event != 'can_block':
            return
        attacker: GameCard = kwargs.get('attacker')
        if attacker.props.slug != 'livonya-silone':
            return None
        if gs.card_filter.on_player_board(card.owner_id).legendary().lands().result():
            return False

class LordOfAtlantisPT(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk (presuming that Islandwalk is being handled elsewhere)"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return PTMod(s=source, p_adj=1, t_adj=1)

class LordOfAtlantisWalk(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return KWAMod(s=source, add_or_remove='add', kwa='Islandwalk')

class Meekstone(Effect):
    """Creatures with power 3 or greater don't untap during their controllers' untap steps."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'can_untap':
            return None
        if card.props.is_creature and card.power >= 3:
            return False
        return None

class Mightstone(Effect):
    """Attacking creatures get +1/+0"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.attackers().result():
            return None
        return PTMod(s=source, p_adj=1, expires='EOT')

class NightmarePT(Effect):
    """Nightmare's power and toughness are each equal to the number of Swamps you control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        your_swamp_cnt = len(gs.card_filter.on_player_board(card.owner_id).swamps().result())
        return PTMod(s=source, p_adj=your_swamp_cnt, t_adj=your_swamp_cnt)

class Moat(Effect):
    """Creatures without flying can't attack"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'can_attack':
            return None
        if card not in gs.card_filter.in_play().has('Flying', False).creatures().result():
            return None
        return False

class OrcishOriflamme(Effect):
    """Attacking creatures you control get +1/+0"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.on_player_board(source.owner_id).attackers().result():
            return None
        return PTMod(s=source, p_adj=1, expires='EOT')

class PeopleOfTheWoodsPT(Effect):
    """People of the Woods's toughness is equal to the number of Forests you control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        your_forest_cnt = len(gs.card_filter.on_player_board(card.owner_id).forests().result())
        return PTMod(s=source, t_adj=your_forest_cnt)

class PlagueRatsPT(Effect):
    """Plague Rats' power & toughness are each equal to the number of creatures named Plague Rats on the battlefield"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        cnt = len(gs.card_filter.in_play().by_slug('plague-rats').result())
        return PTMod(s=source, p_adj=cnt, t_adj=cnt)

class RabidWombat(Effect):
    """This creature gets +2/+2 for each Aura attached to it"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card is not source:
            return None
        aura_cnt = len(source.auras)
        if not aura_cnt:
            return None
        return PTMod(s=source, p_adj=2 * aura_cnt, t_adj=2 * aura_cnt, expires='EOT')

class RohgahhOfKherKeepPump(Effect):
    """Creatures you control named Kobolds of Kher Keep get +2/+2"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod':
            return None
        s: GameCard = kwargs.get('source')
        if card not in gs.card_filter.on_player_board(s.owner_id).by_slug('kobolds-of-kher-keep').result():
            return None
        return PTMod(s=s, p_adj=2, t_adj=2)

class SedgeTrollPT(Effect):
    """Gains +1/+1 if you control a swamp"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod' or card.props.slug != 'sedge-troll':
            return None
        if gs.card_filter.on_player_board(card.owner_id).swamps().result():
            return PTMod(s=card, p_adj=1, t_adj=1)

class Seeker(Effect):
    """Enchanted creature can't be blocked except by artifact creatures and/or white creatures"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != "can_block" or not attacker.host or attacker.host.props.slug != 'seeker':
            return None
        if 'Artifact' not in card.card_types or 'U' not in card.colors:
            return False

class SirensCallCanCast(Effect):
    """Cast this spell only during an opponent's turn, before attackers are declared ..."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'can_cast' or gs.turn_mgr.player_turn_idx == card.owner_id:
            return None
        if gs.phase_mgr.phase >= Phase.DECLARE_ATTACKERS:
            return False

class SpectralCloak(Effect):
    """Enchanted creature has shroud as long as it's untapped. (It can't be the target of spells or abilities.)"""
    event = 'can_target'

    def on_query(self, gs: GameState, event: str, **kwargs):
        if event != 'can_target':
            return
        target: GameCard = kwargs.get('card')
        host: GameCard = kwargs.get('target_host')
        if host is not target or host.is_tapped:
            return
        return False

class SunkenCity(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().blue().creatures().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class WallOfTombstonesPT(Effect):
    """At your upkeep, change this creature's base toughness to 1 + the number of creature cards in your graveyard."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source or gs.turn_mgr.player_turn_idx != source.owner_id:
            return None
        cnt = len(gs.card_filter.in_player_graveyard(source.owner_id).creatures().result())
        return PTMod(s=source, t_adj=1 + cnt)

class WaterWurmPT(Effect):
    """This creature gets +0/+1 as long as an opponent controls an Island"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod' or card.props.slug != 'water-wurm':
            return None

        if gs.card_filter.on_player_board(flip(card.owner_id)).islands().result():
            return PTMod(s=card, t_adj=1)

class Weakstone(Effect):
    """Attacking creatures get -1/-0"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTMod(s=source, p_adj=-1, expires='EOT')

class ZombieMasterWalk(Effect):
    """Other Zombie creatures gain Swampwalk"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card in gs.card_filter.in_play().creatures().by_sub_type('Zombie').result() and card is not source:
            return KWAMod(s=source, add_or_remove='add', kwa='Swampwalk')
