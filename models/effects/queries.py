from __future__ import annotations

import math
from typing import TYPE_CHECKING

from models.modifiers import PTModifier, PTTemp, KWAModifier, TypeModifier, SubTypeModifier
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect


# --- CARD-SPECIFIC ---
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
        for my_creature in gs.card_filter.creatures().on_player_board(card.orig_owner_id).result():
            if 'W' not in my_creature.props.colors or 'C' not in my_creature.props.colors:
                return False
        return PTModifier(source, 1, 1)

class AngryMobPT(Effect):
    """During your turn, Angry Mob's power & toughness are each = 2 plus the number of Swamps your opponents control.
    During turns other than yours, Angry Mob's power and toughness are each 2."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        if gs.player_turn_idx != source.owner_id:
            return PTTemp(source, 2, 2)
        opp_swamp_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).swamps().result())
        return PTTemp(source, 2 + opp_swamp_cnt, 2 + opp_swamp_cnt)

class ArcadesSabbathAllCreaturePump(Effect):
    """... Each untapped creature you control gets +0/+2 as long as it's not attacking ..."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        attackers = gs.card_filter.attackers().result()
        your_untapped_creatures = gs.card_filter.creatures().on_player_board(card.orig_owner_id).tapped(False).result()
        for c in your_untapped_creatures:
            if c not in attackers:
                return PTModifier(source, 0, 2)

class ArtifactWardCanBeBlocked(Effect):
    """This creature can't be blocked by artifact creatures"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or not attacker.modifiers.is_enchanted_by('artifact-ward'):
            return None
        if 'Artifact' in card.card_types:
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
        if event != 'pt_mod' or card is not source.attached_to:
            return None
        your_forest_cnt = len(gs.card_filter.on_player_board(source.orig_owner_id).forests().result())
        p_adj = math.floor(your_forest_cnt / 2)
        t_adj = math.ceil(your_forest_cnt / 2)
        return PTModifier(source, p_adj, t_adj)

class BadMoon(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().black().creatures().result():
            return None
        return PTModifier(source, 1, 1)

class BeastsOfBogardan(Effect):
    """This creature gets +1/+1 as long as an opponent controls a nontoken white permanent"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card.props.slug != 'beasts-of-bogardan':
            return None
        opp_id = flip(card.owner_id)
        opp_non_token_white_perms = gs.card_filter.on_player_board(opp_id).non_token().white().permanents().result()
        if opp_non_token_white_perms:
            return PTModifier(source, 1, 1)

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
        if card not in gs.card_filter.creatures().on_player_board(card.orig_owner_id).tapped(False).white().result():
            return None
        return PTModifier(source, 0, 2)

class ConcordantCrossroads(Effect):
    """All creatures have haste"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return KWAModifier(source, 'add', 'Haste')

class Conversion(Effect):
    """All Mountains are Plains"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'sub_type_mod':
            return None
        return [SubTypeModifier(source, 'add', 'Plains'), SubTypeModifier(source, 'remove', 'Mountain')]

class Crusade(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().white().creatures().result():
            return None
        return PTModifier(source, 1, 1)

class DakkonBlackbladePT(Effect):
    """Dakkon Blackblade's power and toughness are each equal to the number of lands you control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        return PTModifier(source, your_land_cnt, your_land_cnt)

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

class Fear(Effect):
    """Enchanted creature has fear. (It can't be blocked except by artifact creatures and/or black creatures.)"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or not card or not attacker.attached_to or attacker.attached_to.props.slug != 'fear':
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
        opp_artifact_cnt = len(gs.card_filter.on_player_board(flip(source.orig_owner_id)).artifacts().result())
        return PTModifier(source, opp_artifact_cnt + 1, opp_artifact_cnt + 1)

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
        return PTModifier(source, cnt, cnt)

class GiantTortoisePT(Effect):
    """This creature gets +0/+3 as long as it's untapped"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        if not card.is_tapped:
            return PTModifier(source, 0, 3)

class GoblinCaves(Effect):
    """As long as enchanted land is a basic Mountain, Goblin creatures get +0/+2"""
    # WARNING: I don't yet have a way to validate that something is a basic land, since it lives in read-only props
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
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if source.attached_to.props.is_basic_land and source.attached_to.props.slug == 'mountain':
            if card in gs.card_filter.in_play().creatures().by_sub_type('Goblin').result():
                return PTModifier(source, 1, 0)

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
        return KWAModifier(source, 'remove', 'Flying')

class HiddenPath(Effect):
    """Green creatures have forestwalk"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().green().creatures().result():
            return None
        return KWAModifier(source, 'add', 'Forestwalk')

class Invisibility(Effect):
    """Enchanted creature can't be blocked except by Walls"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if (event != 'can_block' or not attacker.attached_to or
                attacker.attached_to.props.slug != 'invisibility' or not card):
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

class JacquesLeVert(Effect):
    """Green creatures you control get +0/+2"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.on_player_board(source.owner_id).green().creatures().result():
            return None
        return PTModifier(source, 0, 2)

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
        return PTModifier(source, your_non_wall_creature_cnt, your_non_wall_creature_cnt)

class KirdApePT(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod' or card.props.slug != 'kird-ape':
            return None

        if gs.card_filter.on_player_board(card.orig_owner_id).forests().result():
            return PTModifier(card, 1, 2)

class KormusBell(Effect):
    """All Swamps are 1/1 creatures that are still lands"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().by_sub_type('Swamp').result():
            return None
        if event == 'type_mod':
            return TypeModifier(source, 'add', 'Creature')
        if event == 'pt_mod':
            return PTModifier(source, 1, 1)
        return None

class LivingLands(Effect):
    """All Forests are 1/1 creatures that are still lands"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().by_sub_type('Forest').result():
            return None
        if event == 'type_mod':
            return TypeModifier(source, 'add', 'Creature')
        if event == 'pt_mod':
            return PTModifier(source, 1, 1)
        return None

class LivingPlane(Effect):
    """All lands are 1/1 creatures that are still lands"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().by_sub_type('Land').result():
            return None
        if event == 'type_mod':
            return TypeModifier(source, 'add', 'Creature')
        if event == 'pt_mod':
            return PTModifier(source, 1, 1)
        return None

class LivonyaSilone(Effect):
    """Legendary landwalk (This creature can't be blocked as long as defending player controls a legendary land.)"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker.props.slug != 'livonya-silone':
            return None
        if gs.card_filter.on_player_board(card.owner_id).legendary().lands().result():
            return False

class LordOfAtlantisPT(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return PTModifier(source, 1, 1)
            # card.modifiers.auras.append(KWAModifier(source, 'add', 'Islandwalk'))

class LordOfAtlantisWalk(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return KWAModifier(source, 'add', 'Islandwalk')

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
        return PTTemp(source, 1, 0)

class NightmarePT(Effect):
    """Nightmare's power and toughness are each equal to the number of Swamps you control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        your_swamp_cnt = len(gs.card_filter.on_player_board(card.owner_id).swamps().result())
        return PTModifier(source, your_swamp_cnt, your_swamp_cnt)

class Moat(Effect):
    """Creatures without flying can't attack"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'kwa_mod':
            return None
        if card not in gs.card_filter.in_play().has('Flying', False).creatures().result():
            return None
        return KWAModifier(source, 'remove', 'Attack')

class OrcishOriflamme(Effect):
    """Attacking creatures you control get +1/+0"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.on_player_board(source.orig_owner_id).attackers().result():
            return None
        return PTTemp(source, 1, 0)

class PeopleOfTheWoodsPT(Effect):
    """People of the Woods's toughness is equal to the number of Forests you control"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        your_forest_cnt = len(gs.card_filter.on_player_board(card.owner_id).forests().result())
        return PTModifier(source, 0, your_forest_cnt)

class PlagueRatsPT(Effect):
    """Plague Rats' power & toughness are each equal to the number of creatures named Plague Rats on the battlefield"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source:
            return None
        cnt = len(gs.card_filter.in_play().by_slug('plague-rats').result())
        return PTModifier(source, cnt, cnt)

class RabidWombat(Effect):
    """This creature gets +2/+2 for each Aura attached to it"""
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

class RohgahhOfKherKeepPump(Effect):
    """Creatures you control named Kobolds of Kher Keep get +2/+2"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod':
            return None
        s: GameCard = kwargs.get('source')
        if card not in gs.card_filter.on_player_board(s.owner_id).by_slug('kobolds-of-kher-keep').result():
            return None
        return PTModifier(s, 2, 2)

class Seeker(Effect):
    """Enchanted creature can't be blocked except by artifact creatures and/or white creatures"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: can_block, card = blocker, mandatory kwargs: attacker"""
        attacker: GameCard = kwargs.get('attacker')
        if event != "can_block" or not attacker.attached_to or attacker.attached_to.props.slug != 'seeker':
            return None
        if 'Artifact' not in card.card_types or 'U' not in card.colors:
            return False

class SunkenCity(Effect):
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().blue().creatures().result():
            return None
        return PTModifier(source, 1, 1)

class WallOfTombstonesPT(Effect):
    """At your upkeep, change this creature's base toughness to 1 + the number of creature cards in your graveyard."""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """kwarg 'source' is the source that is providing this effect"""
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod' or card is not source or gs.player_turn_idx != source.owner_id:
            return None
        cnt = len(gs.card_filter.in_player_graveyard(source.owner_id).creatures().result())
        return PTModifier(source, 0, 1 + cnt)

class WaterWurmPT(Effect):
    """This creature gets +0/+1 as long as an opponent controls an Island"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'pt_mod' or card.props.slug != 'water-wurm':
            return None

        if gs.card_filter.on_player_board(flip(card.orig_owner_id)).islands().result():
            return PTModifier(card, 0, 1)

class Weakstone(Effect):
    """Attacking creatures get -1/-0"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTTemp(source, -1, 0)
