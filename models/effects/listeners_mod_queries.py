from __future__ import annotations
import math
from typing import TYPE_CHECKING, Callable, Any

from models.events_all import ModQueryEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Listener
from models.modifiers import TypeMod, SubTypeMod, PTMod, KWAMod
from models.utils import flip

"""
(I think) these are all called from GameCard who is asking about its attributes/modifications.
Their get_mods() method may return: ModType, list[ModType], None
They exist because not all modifications are stored on the GameCard itself (ex: Crusade)
"""

# --- GENERICS ---
class AddCreatureType(Listener):
    """Turns the card into a creature"""
    listens_to = ModQueryEvent
    modifies = ('type', 'sub_type', 'pt')

    def __init__(self, power: int, toughness: int, sub_type: str = None):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source:
            return
        if event.query == 'type':
            event.mods.append(TypeMod(s=source, add_or_remove='add', card_type='Creature'))
        elif event.query == 'sub_type':
            event.mods.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type=self.sub_type))
        elif event.query == 'pt':
            event.mods.append(PTMod(s=source, p_adj=self.power, t_adj=self.toughness))

class AddCreatureTypePTManaValue(Listener):
    """Turns card into a creature with power and toughness each equal to its mana value"""
    listens_to = ModQueryEvent
    modifies = ('type', 'pt')

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source:
            return
        if event.query == 'type':
            event.mods.append(TypeMod(s=source, add_or_remove='add', card_type='Creature'))
        elif event.query == 'pt':
            event.mods.append(PTMod(s=source, p_adj=event.card.props.mana_value, t_adj=event.card.props.mana_value))

class KWAApplies(Listener):
    """If card is in applies_to_func (and the optional condition isn't False), KWAMod append/remove provided keyword"""
    listens_to = ModQueryEvent
    modifies = 'kwa'

    def __init__(self, applies_to_func: Callable, add_or_remove: str, kwa: str,
                 condition: Callable[[GameState, GameCard], bool] = None):
        self.applies_to_func = applies_to_func
        self.add_or_remove = add_or_remove
        self.kwa_added = kwa
        self.condition = condition

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if self.condition and not self.condition(gs, source):
            return
        applies_to = self.applies_to_func(gs, source)
        if not isinstance(applies_to, list):
            applies_to = [applies_to]
        if event.card in applies_to:
            event.mods.append(KWAMod(s=source, kwa=self.kwa_added, add_or_remove=self.add_or_remove))

class SelfPTEquals(Listener):
    """For that card, its pt = the len of the T_FUNC provided, append a PTMod for the len;
    you may provide p_only or t_only to only affect that value"""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def __init__(self, card_cnt_func: Callable[[GameState, GameCard], list[GameCard]],
                 p_only: bool = False, t_only: bool = False):
        self.card_cnt_func = card_cnt_func
        self.p_only = p_only
        self.t_only = t_only

        if self.p_only and self.t_only:
            raise ValueError("Both p_only & t_only may not be True for SelfPTEquals")

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source:
            return
        amt = len(self.card_cnt_func(gs, source))
        if not self.p_only and not self.t_only:
            event.mods.append(PTMod(s=source, p_adj=amt, t_adj=amt))
        elif self.p_only:
            event.mods.append(PTMod(s=source, p_adj=amt))
        elif self.t_only:
            event.mods.append(PTMod(s=source, t_adj=amt))

class PumpApplies(Listener):
    """If card is in applies_to_func (and the optional condition isn't False), append a PTMod for the provided pt_adj"""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def __init__(self, applies_to_func: Callable, pt_adj: tuple[int, int],
                 condition: Callable[[GameState, GameCard], bool] = None):
        self.applies_to_func = applies_to_func
        self.p_adj = pt_adj[0]
        self.t_adj = pt_adj[1]
        self.condition = condition

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if self.condition and not self.condition(gs, source):
            return
        applies_to = self.applies_to_func(gs, source)
        if not isinstance(applies_to, list):
            applies_to = [applies_to]
        if event.card in applies_to:
            event.mods.append(PTMod(s=source, p_adj=self.p_adj, t_adj=self.t_adj))

class PumpAppliesEOT(Listener):
    """If card is in applies_to_func (and the optional condition isn't False), append PTMod; expires = 'EOT'"""
    listens_to = ModQueryEvent
    modifies = 'pt'
    expires = 'EOT'

    def __init__(self, applies_to_func: Callable, pt_adj: tuple[int, int],
                 condition: Callable[[GameState, GameCard], bool] = None):
        self.applies_to_func = applies_to_func
        self.p_adj = pt_adj[0]
        self.t_adj = pt_adj[1]
        self.condition = condition

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if self.condition and not self.condition(gs, source):
            return
        applies_to = self.applies_to_func(gs, source)
        if not isinstance(applies_to, list):
            applies_to = [applies_to]
        if event.card in applies_to:
            event.mods.append(PTMod(s=source, p_adj=self.p_adj, t_adj=self.t_adj, expires='EOT'))

# --- CARD-SPECIFIC ---
class AngelicVoices(Listener):
    """Creatures you control get +1/+1 as long as you control no nonartifact, nonwhite creatures."""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        for my_creature in gs.card_filter.creatures().on_player_board(event.card.owner_id).result():
            if 'W' not in my_creature.props.colors or 'C' not in my_creature.props.colors:
                return
        event.mods.append(PTMod(s=source, p_adj=1, t_adj=1))

class AngryMobPT(Listener):
    """During your turn, Angry Mob's power & toughness are each = 2 plus the number of Swamps your opponents control.
    During turns other than yours, Angry Mob's power and toughness are each 2."""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source:
            return
        if gs.player_turn_idx != source.owner_id:
            mod = PTMod(s=source, p_adj=2, t_adj=2, expires='EOT')
        else:
            opp_swamp_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).swamps().result())
            mod = PTMod(s=source, p_adj=2 + opp_swamp_cnt, t_adj=2 + opp_swamp_cnt, expires='EOT')
        event.mods.append(mod)

class ArmyOfAllahEOT(Listener):
    """This will be called only by ArmyOfAllah(); this effect is stored in GameState and cleared at EOT;
    Attacking creatures get +2/+0 until end of turn"""
    listens_to = ModQueryEvent
    modifies = 'pt'
    expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card not in gs.card_filter.in_play().attackers().result():
            return
        event.mods.append(PTMod(s=source, p_adj=2, expires='EOT'))

class AspectOfWolfPT(Listener):
    """Enchant creature Enchanted creature gets +X/+Y, where X is half the number of Forests you control, rounded down,
    and Y is half the number of Forests you control, rounded up."""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source.host:
            return
        your_forest_cnt = len(gs.card_filter.on_player_board(source.owner_id).forests().result())
        p_adj = math.floor(your_forest_cnt / 2)
        t_adj = math.ceil(your_forest_cnt / 2)
        event.mods.append(PTMod(s=source, p_adj=p_adj, t_adj=t_adj))

class Conversion(Listener):
    """All Mountains are Plains"""
    listens_to = ModQueryEvent
    modifies = 'sub_type'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        event.mods.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type='Plains'))
        event.mods.append(SubTypeMod(s=source, add_or_remove='remove', card_sub_type='Mountain'))

class GaeasAvengerPT(Listener):
    """Gaea's Avenger's power and toughness are each equal to 1 plus the number of artifacts your opponents control"""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source:
            return None
        opp_artifact_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).artifacts().result())
        event.mods.append(PTMod(s=source, p_adj=opp_artifact_cnt + 1, t_adj=opp_artifact_cnt + 1))

class GaeasLiegePT(Listener):
    """As long as Gaea's Liege isn't attacking, its power & toughness are each = the number of Forests you control.
    If Gaea's Liege is attacking, its power & toughness are each = the # of Forests defending player controls."""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source:
            return None
        is_attacking = event.card in gs.card_filter.attackers().result()
        if is_attacking:
            cnt = len(gs.card_filter.on_player_board(flip(event.card.owner_id)).forests().result())
        else:
            cnt = len(gs.card_filter.on_player_board(event.card.owner_id).forests().result())
        event.mods.append(PTMod(s=source, p_adj=cnt, t_adj=cnt))

class IvoryGuardians(Listener):
    """Creatures named Ivory Guardians get +1/+1 as long as an opponent controls a nontoken red permanent; the pumps are
    cumulative. Ex: if there's two Ivory Guardians & opponent has a nontoken red permanent, each gets +2/+2"""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card.props.slug != 'ivory-guardians':
            return
        ivory_guardians_cnt = len(gs.card_filter.in_play().by_slug('ivory-guardians').result())
        if gs.card_filter.on_player_board(flip(event.card.owner_id)).non_token().red().permanents().result():
            event.mods.append(PTMod(s=event.card, p_adj=ivory_guardians_cnt, t_adj=ivory_guardians_cnt))

class JihadPT(Listener):
    """White creatures get +2/+1 as long as opponent controls a nontoken permanent of Jihad's declared color"""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        print('Checking JIHAD ...')
        if event.card not in gs.card_filter.in_play().white().creatures().result():
            return None
        declared_color = source.extras.get('color_declaration')
        opp = flip(source.owner_id)
        if gs.card_filter.on_player_board(opp).by_color(declared_color).non_token().permanents().result():
            event.mods.append(PTMod(s=source, p_adj=2, t_adj=1))
            return

class KormusBell(Listener):
    """All Swamps are 1/1 creatures that are still lands"""
    listens_to = ModQueryEvent
    modifies = ('type', 'pt')

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card not in gs.card_filter.in_play().by_sub_type('Swamp').result():
            return
        if event.query == 'type':
            event.mods.append(TypeMod(s=source, add_or_remove='add', card_type='Creature'))
        elif event.query == 'pt':
            event.mods.append(PTMod(s=source, p_adj=1, t_adj=1))

class LivingLands(Listener):
    """All Forests are 1/1 creatures that are still lands"""
    listens_to = ModQueryEvent
    modifies = ('type', 'pt')

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card not in gs.card_filter.in_play().by_sub_type('Forest').result():
            return
        if event.query == 'type':
            event.mods.append(TypeMod(s=source, add_or_remove='add', card_type='Creature'))
        elif event.query == 'pt':
            event.mods.append(PTMod(s=source, p_adj=1, t_adj=1))
        return None

class LivingPlane(Listener):
    """All lands are 1/1 creatures that are still lands"""
    listens_to = ModQueryEvent
    modifies = ('type', 'pt')

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card not in gs.card_filter.in_play().by_sub_type('Land').result():
            return
        if event.query == 'type':
            event.mods.append(TypeMod(s=source, add_or_remove='add', card_type='Creature'))
        elif event.query == 'pt':
            event.mods.append(PTMod(s=source, p_adj=1, t_adj=1))

class RabidWombat(Listener):
    """This creature gets +2/+2 for each Aura attached to it"""
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source:
            return
        aura_cnt = len(source.auras)
        if not aura_cnt:
            return
        event.mods.append(PTMod(s=source, p_adj=2 * aura_cnt, t_adj=2 * aura_cnt, expires='EOT'))

class Transmutation(Listener):
    """Switch target creature's power and toughness EOT"""
    listens_to = ModQueryEvent
    modifies = 'pt'
    expires = 'EOT'

    def __init__(self):
        self.target: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not self.target:
            return
        power_delta = event.card.toughness - event.card.power
        toughness_delta = event.card.power - event.card.toughness
        event.mods.append(PTMod(s=source, p_adj=power_delta, t_adj=toughness_delta, expires='EOT'))

class WallOfTombstonesPT(Listener):
    """At your upkeep, change this creature's base toughness to 1 + the number of creature cards in your graveyard."""
    # TODO: this changes at Upkeep, so it should listen to UpkeepEvent ...
    listens_to = ModQueryEvent
    modifies = 'pt'

    def on_event(self, gs: GameState, source: GameCard, event: ModQueryEvent) -> None:
        if event.card is not source or gs.player_turn_idx != source.owner_id:
            return
        cnt = len(gs.card_filter.in_player_graveyard(source.owner_id).creatures().result())
        event.mods.append(PTMod(s=source, t_adj=1 + cnt))
