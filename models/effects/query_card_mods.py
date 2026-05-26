from __future__ import annotations
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard
    from models.modifiers import ModType, PTMod

from models.effects.base import Effect
from models.modifiers import TypeMod, SubTypeMod, PTMod, KWAMod
from models.utils import flip

"""
(I think) these are all called from GameCard who is asking about its attributes/modifications.
Their get_mods() method may return: ModType, list[ModType], None
They exist because not all modifications are stored on the GameCard itself (ex: Crusade)
"""

# --- GENERICS ---
class AddCreatureType(Effect):
    """Turns the card into a creature"""
    modifies = ('type_mod', 'sub_type_mod', 'pt_mod')

    def __init__(self, power: int, toughness: int, sub_type: str = None):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card is not source:
            return None
        if 'type_mod' in AddCreatureType.query:
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if 'sub_type_mod' in AddCreatureType.query:
            return SubTypeMod(s=source, add_or_remove='add', card_sub_type=self.sub_type)
        if 'pt_mod' in AddCreatureType.query:
            return PTMod(s=source, p_adj=self.power, t_adj=self.toughness)

class AddCreatureTypePTManaValue(Effect):
    """Turns card into a creature with power and toughness each equal to its mana value"""
    modifies = ('type_mod', 'pt_mod')

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card is not source:
            return None
        if query == 'type_mod':
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if query == 'pt_mod':
            return PTMod(s=source, p_adj=card.props.mana_value, t_adj=card.props.mana_value)


# --- CARD-SPECIFIC ---
class AngelicVoices(Effect):
    """Creatures you control get +1/+1 as long as you control no nonartifact, nonwhite creatures."""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        for my_creature in gs.card_filter.creatures().on_player_board(card.owner_id).result():
            if 'W' not in my_creature.props.colors or 'C' not in my_creature.props.colors:
                return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class AngryMobPT(Effect):
    """During your turn, Angry Mob's power & toughness are each = 2 plus the number of Swamps your opponents control.
    During turns other than yours, Angry Mob's power and toughness are each 2."""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return PTMod(s=source, p_adj=2, t_adj=2, expires='EOT')
        opp_swamp_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).swamps().result())
        return PTMod(s=source, p_adj=2 + opp_swamp_cnt, t_adj=2 + opp_swamp_cnt, expires='EOT')

class ArcadesSabbathAllCreaturePump(Effect):
    """... Each untapped creature you control gets +0/+2 as long as it's not attacking ..."""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        attackers = gs.card_filter.attackers().result()
        your_untapped_creatures = gs.card_filter.creatures().on_player_board(card.owner_id).tapped(False).result()
        for c in your_untapped_creatures:
            if c not in attackers:
                return PTMod(s=source, t_adj=2)

class ArmyOfAllahEOT(Effect):
    """This will be called only by ArmyOfAllah(); this effect is stored in GameState and cleared at EOT;
    Attacking creatures get +2/+0 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTMod(s=source, p_adj=2, expires='EOT')

class AspectOfWolfPT(Effect):
    """Enchant creature Enchanted creature gets +X/+Y, where X is half the number of Forests you control, rounded down,
    and Y is half the number of Forests you control, rounded up."""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source.host:
            return None
        your_forest_cnt = len(gs.card_filter.on_player_board(source.owner_id).forests().result())
        p_adj = math.floor(your_forest_cnt / 2)
        t_adj = math.ceil(your_forest_cnt / 2)
        return PTMod(s=source, p_adj=p_adj, t_adj=t_adj)

class BadMoon(Effect):
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().black().creatures().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class BeastsOfBogardan(Effect):
    """This creature gets +1/+1 as long as an opponent controls a nontoken white permanent"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card.props.slug != 'beasts-of-bogardan':
            return None
        opp_id = flip(card.owner_id)
        opp_non_token_white_perms = gs.card_filter.on_player_board(opp_id).non_token().white().permanents().result()
        if opp_non_token_white_perms:
            return PTMod(s=source, p_adj=1, t_adj=1)

class BoneFluteEOT(Effect):
    """This will be called only by BoneFlute(); this effect is stored in GameState and cleared at EOT;
    All creatures get -1/-0 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTMod(s=source, p_adj=-1, expires='EOT')

class Castle(Effect):
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.creatures().on_player_board(card.owner_id).tapped(False).white().result():
            return None
        return PTMod(s=source, t_adj=2)

class ConcordantCrossroads(Effect):
    """All creatures have haste"""
    modifies = 'kwa_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return KWAMod(s=source, add_or_remove='add', kwa='Haste')

class Conversion(Effect):
    """All Mountains are Plains"""
    modifies = 'sub_type_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        return [SubTypeMod(s=source, add_or_remove='add', card_sub_type='Plains'),
                SubTypeMod(s=source, add_or_remove='remove', card_sub_type='Mountain')]

class Crusade(Effect):
    """All white creatures get +1/+1"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().white().creatures().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class DakkonBlackbladePT(Effect):
    """Dakkon Blackblade's power and toughness are each equal to the number of lands you control"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        return PTMod(s=source, p_adj=your_land_cnt, t_adj=your_land_cnt)

class GaeasAvengerPT(Effect):
    """Gaea's Avenger's power and toughness are each equal to 1 plus the number of artifacts your opponents control"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        opp_artifact_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).artifacts().result())
        return PTMod(s=source, p_adj=opp_artifact_cnt + 1, t_adj=opp_artifact_cnt + 1)

class GaeasLiegePT(Effect):
    """As long as Gaea's Liege isn't attacking, its power & toughness are each = the number of Forests you control.
    If Gaea's Liege is attacking, its power & toughness are each = the # of Forests defending player controls."""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        is_attacking = card in gs.card_filter.attackers().result()
        if is_attacking:
            cnt = len(gs.card_filter.on_player_board(flip(card.owner_id)).forests().result())
        else:
            cnt = len(gs.card_filter.on_player_board(card.owner_id).forests().result())
        return PTMod(s=source, p_adj=cnt, t_adj=cnt)

class GiantTortoisePT(Effect):
    """This creature gets +0/+3 as long as it's untapped"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        if not card.is_tapped:
            return PTMod(s=source, t_adj=3)

class GoblinCaves(Effect):
    """As long as enchanted land is a basic Mountain, Goblin creatures get +0/+2"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        basic_lands = gs.card_filter.basic_lands().in_play().result()
        if source.host in basic_lands and source.host.props.slug == 'mountain':
            if card in gs.card_filter.in_play().creatures().by_sub_type('Goblin').result():
                return PTMod(s=source, t_adj=2)

class GoblinShrinePump(Effect):
    """As long as enchanted land is a basic Mountain, Goblin creatures get +1/+0 ..."""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        basic_lands = gs.card_filter.basic_lands().in_play().result()
        if source.host is basic_lands and source.host.props.slug == 'mountain':
            if card in gs.card_filter.in_play().creatures().by_sub_type('Goblin').result():
                return PTMod(s=source, p_adj=1)

class GravitySphere(Effect):
    """All creatures lose flying"""
    modifies = 'kwa_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return KWAMod(s=source, add_or_remove='remove', kwa='Flying')

class HellSwarmEOT(Effect):
    """This will be called only by HellSwarm(); this effect is stored in GameState and cleared at EOT;
    All creatures get -1/-0 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTMod(s=source, p_adj=-1, expires='EOT')

class HiddenPath(Effect):
    """Green creatures have forestwalk"""
    modifies = 'kwa_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().green().creatures().result():
            return None
        return KWAMod(s=source, add_or_remove='add', kwa='Forestwalk')

class HolyLightEOT(Effect):
    """This will be called only by HolyLight(); this effect is stored in GameState and cleared at EOT
    Nonwhite creatures get -1/-1 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        creatures = gs.card_filter.in_play().creatures().result()
        white_creatures = gs.card_filter.in_play().creatures().white().result()
        non_white_creatures = [c for c in creatures if c not in white_creatures]
        if card not in non_white_creatures:
            return None
        return PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT')

class IvoryGuardians(Effect):
    """Creatures named Ivory Guardians get +1/+1 as long as an opponent controls a nontoken red permanent; the pumps are
    cumulative. Ex: if there's two Ivory Guardians & opponent has a nontoken red permanent, each gets +2/+2"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card.props.slug != 'ivory-guardians':
            return None

        ivory_guardians_cnt = len(gs.card_filter.in_play().by_slug('ivory-guardians').result())

        if gs.card_filter.on_player_board(flip(card.owner_id)).non_token().red().permanents().result():
            return PTMod(s=card, p_adj=ivory_guardians_cnt, t_adj=ivory_guardians_cnt)

class JacquesLeVert(Effect):
    """Green creatures you control get +0/+2"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.on_player_board(source.owner_id).green().creatures().result():
            return None
        return PTMod(s=source, t_adj=2)

class KeldonWarlordPT(Effect):
    """Keldon Warlord's power and toughness are each equal to the number of non-Wall creatures you control"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        your_non_wall_creature_cnt = len(gs.card_filter.on_player_board(card.owner_id).non_wall_creatures().result())
        return PTMod(s=source, p_adj=your_non_wall_creature_cnt, t_adj=your_non_wall_creature_cnt)

class KirdApePT(Effect):
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card.props.slug != 'kird-ape':
            return None

        if gs.card_filter.on_player_board(card.owner_id).forests().result():
            return PTMod(s=card, p_adj=1, t_adj=2)

class KoboldOverlord(Effect):
    """Other Kobold creatures you control have first strike"""
    modifies = 'kwa_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if source.props.slug != 'kobold-overlord' or card is source:
            return
        if card in gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Kobold').result():
            return KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT')

class KoboldTaskmaster(Effect):
    """Other Kobold creatures you control get +1/+0"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if source.props.slug != 'kobold-taskmaster' or card is source:
            return
        if card in gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Kobold').result():
            return PTMod(s=source, p_adj=1)

class KormusBell(Effect):
    """All Swamps are 1/1 creatures that are still lands"""
    modifies = ('type_mod', 'pt_mod')

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().by_sub_type('Swamp').result():
            return None
        if query == 'type_mod':
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if query == 'pt_mod':
            return PTMod(s=source, p_adj=1, t_adj=1)
        return None

class LivingLands(Effect):
    """All Forests are 1/1 creatures that are still lands"""
    modifies = ('type_mod', 'pt_mod')

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().by_sub_type('Forest').result():
            return None
        if query == 'type_mod':
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if query == 'pt_mod':
            return PTMod(s=source, p_adj=1, t_adj=1)
        return None

class LivingPlane(Effect):
    """All lands are 1/1 creatures that are still lands"""
    modifies = ('type_mod', 'pt_mod')

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().by_sub_type('Land').result():
            return None
        if query == 'type_mod':
            return TypeMod(s=source, add_or_remove='add', card_type='Creature')
        if query == 'pt_mod':
            return PTMod(s=source, p_adj=1, t_adj=1)
        return None

class LordOfAtlantisPT(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk (presuming that Islandwalk is being handled elsewhere)"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return PTMod(s=source, p_adj=1, t_adj=1)

class LordOfAtlantisWalk(Effect):
    """All other Merfolk gain +1/+1 and Islandwalk"""
    modifies = 'kwa_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result() and card is not source:
            return KWAMod(s=source, add_or_remove='add', kwa='Islandwalk')

class MarshGasEOT(Effect):
    """This will be called only by MarshGas(); this effect is stored in GameState and cleared at EOT;
    All creatures get -2/-0 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTMod(s=source, p_adj=-2, expires='EOT')

class Mightstone(Effect):
    """Attacking creatures get +1/+0"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.attackers().result():
            return None
        return PTMod(s=source, p_adj=1, expires='EOT')

class MoraleEOT(Effect):
    """This will be called only by Morale(); this effect is stored in GameState and cleared at EOT;
    Attacking creatures get +1/+1 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1, expires='EOT')

class NightmarePT(Effect):
    """Nightmare's power and toughness are each equal to the number of Swamps you control"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        your_swamp_cnt = len(gs.card_filter.on_player_board(card.owner_id).swamps().result())
        return PTMod(s=source, p_adj=your_swamp_cnt, t_adj=your_swamp_cnt)

class OrcishOriflamme(Effect):
    """Attacking creatures you control get +1/+0"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card not in gs.card_filter.on_player_board(source.owner_id).attackers().result():
            return None
        return PTMod(s=source, p_adj=1, expires='EOT')

class PeopleOfTheWoodsPT(Effect):
    """People of the Woods's toughness is equal to the number of Forests you control"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        your_forest_cnt = len(gs.card_filter.on_player_board(card.owner_id).forests().result())
        return PTMod(s=source, t_adj=your_forest_cnt)

class PietyEOT(Effect):
    """This will be called only by Piety(); this effect is stored in GameState and cleared at EOT;
    Blocking creatures get 0/+3 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().blockers().result():
            return None
        return PTMod(s=source, t_adj=3, expires='EOT')

class PlagueRatsPT(Effect):
    """Plague Rats' power & toughness are each equal to the number of creatures named Plague Rats on the battlefield"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        cnt = len(gs.card_filter.in_play().by_slug('plague-rats').result())
        return PTMod(s=source, p_adj=cnt, t_adj=cnt)

class RabidWombat(Effect):
    """This creature gets +2/+2 for each Aura attached to it"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source:
            return None
        aura_cnt = len(source.auras)
        if not aura_cnt:
            return None
        return PTMod(s=source, p_adj=2 * aura_cnt, t_adj=2 * aura_cnt, expires='EOT')

class RohgahhOfKherKeepPump(Effect):
    """Creatures you control named Kobolds of Kher Keep get +2/+2"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.on_player_board(source.owner_id).by_slug('kobolds-of-kher-keep').result():
            return None
        return PTMod(s=source, p_adj=2, t_adj=2)

class SedgeTrollPT(Effect):
    """Gains +1/+1 if you control a swamp"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card.props.slug != 'sedge-troll':
            return None
        if gs.card_filter.on_player_board(card.owner_id).swamps().result():
            return PTMod(s=card, p_adj=1, t_adj=1)

class ShieldWallEOT(Effect):
    """This will be called only by ShieldWall(); this effect is stored in GameState and cleared at EOT;
    Creatures you control get +0/+2 until end of turn"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        if card not in gs.card_filter.in_play().on_player_board(source.owner_id).creatures().result():
            return None
        return PTMod(s=source, t_adj=2, expires='EOT')

class SunkenCity(Effect):
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().blue().creatures().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1)

class TransmutationEOT(Effect):
    """Stored in GameState & cleared EOT; how does this class know who the target is?"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        source: GameCard = kwargs.get('source')
        power_delta = card.toughness - card.power
        toughness_delta = card.power - card.toughness
        return PTMod(s=source, p_adj=power_delta, t_adj=toughness_delta, expires='EOT')

class WallOfTombstonesPT(Effect):
    """At your upkeep, change this creature's base toughness to 1 + the number of creature cards in your graveyard."""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        """kwarg 'source' is the source that is providing this effect"""
        if card is not source or gs.turn_mgr.player_turn_idx != source.owner_id:
            return None
        cnt = len(gs.card_filter.in_player_graveyard(source.owner_id).creatures().result())
        return PTMod(s=source, t_adj=1 + cnt)

class WaterWurmPT(Effect):
    """This creature gets +0/+1 as long as an opponent controls an Island"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card.props.slug != 'water-wurm':
            return None

        if gs.card_filter.on_player_board(flip(card.owner_id)).islands().result():
            return PTMod(s=card, t_adj=1)

class Weakstone(Effect):
    """Attacking creatures get -1/-0"""
    modifies = 'pt_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTMod(s=source, p_adj=-1, expires='EOT')

class ZombieMasterWalk(Effect):
    """Other Zombie creatures gain Swampwalk"""
    modifies = 'kwa_mod'

    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> ModType | list[ModType] | None:
        if card in gs.card_filter.in_play().creatures().by_sub_type('Zombie').result() and card is not source:
            return KWAMod(s=source, add_or_remove='add', kwa='Swampwalk')
