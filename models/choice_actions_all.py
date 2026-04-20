from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING, Iterable, Optional

from models.actions.kwa import AddKWA
from models.actions.piles import HandToBattlefield, Shuffle, BattlefieldToGraveyard
from models.actions.target import AddTargetAction, FinishTargetsAction

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard
    from models.effects.base import EffSpec, ActivatedAbility

from models.constants import COLOR_LETTERS_W_COLORLESS, Target
from models.actions.base import Action, DoNothing
from models.actions.damage import DealDamageToYou, PayLife
from models.actions.destroy_sac_regen import Sac, DestroyAction, AllowOpponentToDestroyALand, SacCards, Reanimate
from models.actions.draw_discard import DrawCard, DiscardCard
from models.actions.mana import AddMana, PayMana
from models.actions.pump import VariablePTMod
from models.actions.special import SacCreatureAndAddMana, PayManaForLife, SkipDrawPhaseGainLife, SacTwoIslands, \
    RemoveCounterGainLife, DestroyAndForegoCombatDamage, CopyCard, PrimalClayA, PrimalClayB, PrimalClayC, HealingSalveA, \
    HealingSalveB, CyclonePayManaPerCounterDealDamage, YawgmothDemonUnpaidUpkeep, SelectXAction
from models.actions.tap_untap import UntapCardStackPop, LeaveTapped, UntapWithManaAction
from models.counter_tokens import CounterType
from models.utils import flip


# --- GENERIC CHOICE ACTIONS ---
@dataclass
class ChoiceAction(ABC):
    player_idx: int
    gs: GameState
    source: GameCard
    target: Optional[Target] = None

    @abstractmethod
    def get_actions(self) -> list[Action]:
        ...


class TargetChoiceAction(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)
        self.selected_targets: list[GameCard] = []

    @abstractmethod
    def get_actions(self) -> list[Action]:
        ...

class AddManaOfColorChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard,
                 possible_colors: Iterable[str] = COLOR_LETTERS_W_COLORLESS, amt: int = 1):
        super().__init__(p_id, gs, source)
        self.possible_colors = possible_colors
        self.amt = amt

    def get_actions(self) -> list[Action]:
        return [AddMana(self.player_idx, self.gs, self.source, color, self.amt) for color in self.possible_colors]

class CopyCardChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, card_options: list[GameCard],
                 additional_types: list[str] = None, copy_color: bool = True):
        super().__init__(p_id, gs, source)
        self.card_options = card_options
        self.additional_types = additional_types
        self.copy_color = copy_color

    def get_actions(self) -> list[Action]:
        return [CopyCard(self.player_idx, self.gs, self.source, t,
                         self.additional_types, self.copy_color) for t in self.card_options]

class DiscardChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, discarding_p_id: int,
                 min_cnt: int = 1, max_cnt: int = 1):
        super().__init__(p_id, gs, source)
        self.discarding_p_id = discarding_p_id
        self.min_cnt = min_cnt
        self.max_cnt = max_cnt
        print('AA')

    def get_actions(self) -> list[Action]:
        """Discard entire hand if hand size is <= the minimum discard count requirement;
        else, if there are options, present every combination of cards back to the user"""
        print('BB')
        cards = self.gs.hands[self.discarding_p_id].cards
        if len(cards) <= self.min_cnt:
            for c in cards[:]:
                cards.remove(c)
            return []
        return [DiscardCard(self.player_idx, self.gs, list(combo))
                for r in range(self.min_cnt, self.max_cnt + 1) for combo in combinations(cards, r)]

class DrawCardsOrDontChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cnt: int = 1):
        super().__init__(p_id, gs, source)
        self.cnt = cnt

    def get_actions(self) -> list[Action]:
        actions: list[Action] = [DrawCard(self.player_idx, self.gs) for _ in range(self.cnt)]
        actions.append(DoNothing(self.player_idx, self.gs))
        return actions

class BattlefieldToGraveyardChoice(ChoiceAction):
    """Doesn't count as 'destroy'; bypasses hexproof/indestructible; counts as "dying"; triggers any such abilities"""
    def __init__(self, p_id: int, gs: GameState, legends: list[GameCard]):
        super().__init__(p_id, gs, source=None)
        self.legends = legends

    def get_actions(self) -> list[Action]:
        return [BattlefieldToGraveyard(self.player_idx, self.gs, c) for c in self.legends]

class MultiTargetChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, eff_spec: EffSpec,
                 x_value_for_variable_cast: int | None = None):
        super().__init__(p_id, gs, source)
        self.eff_spec = eff_spec
        self.x_value_for_variable_cast = x_value_for_variable_cast
        self.selected_targets = []

    def get_actions(self) -> list[Action]:
        actions = []
        target_spec = self.eff_spec.target_spec

        candidates = target_spec.filter_func(self.gs, self.source)

        if target_spec.max_cnt is None or len(self.selected_targets) < target_spec.max_cnt:
            for c in candidates:
                if c not in self.selected_targets and self.gs.can_target(c, self.source, c.host if isinstance(c, GameCard) else None):
                    actions.append(AddTargetAction(self.player_idx, self.gs, self, c))

        if len(self.selected_targets) >= target_spec.min_cnt:
            actions.append(FinishTargetsAction(self.player_idx, self.gs, self))

        return actions

class OpponentDestroysLandChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        lands = self.gs.card_filter.on_player_board(self.source.owner_id).lands().result()
        return [DestroyAction(flip(self.player_idx), self.gs, self.source, t) for t in lands]

class PayLifeOrDiscardChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, life_amt: int, card_to_be_discarded: GameCard):
        super().__init__(p_id, gs, source)
        self.life_amt = life_amt
        self.card_to_be_discarded = card_to_be_discarded

    def get_actions(self) -> list[Action]:
        return [PayLife(self.player_idx, self.gs, self.source, self.life_amt),
                DiscardCard(self.player_idx, self.gs, self.card_to_be_discarded)]

class PayLifeOrSacChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, amt: int):
        super().__init__(p_id, gs, source)
        self.amt = amt

    def get_actions(self) -> list[Action]:
        return [PayLife(self.player_idx, self.gs, self.source, self.amt), Sac(self.player_idx, self.gs, self.source)]

class PayManaOrSacUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cost: str):
        super().__init__(p_id, gs, source)
        self.cost = cost

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.player_idx].can_pay(self.cost):
            actions.append(PayMana(self.player_idx, self.gs, self.source, self.cost))
        actions.append(Sac(self.player_idx, self.gs, self.source))
        return actions

class PayManaOrTakeDamage(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cost: str, damage_amt: int):
        super().__init__(p_id, gs, source)
        self.cost = cost
        self.damage_amt = damage_amt

    def get_actions(self) -> list[Action]:
        return [PayMana(self.player_idx, self.gs, self.source, self.cost),
                DealDamageToYou(self.source.owner_id, self.gs, self.source, self.damage_amt)]

class PayManaToDrawCardsChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayManaToDrawCardsChoice(self.player_idx, self.gs, self.source), DoNothing(self.player_idx, self.gs)]

class PayOneColorlessForOneLifeChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        if not self.gs.mana_pools[self.player_idx].can_pay('1'):
            return []
        return [PayManaForLife(self.player_idx, self.gs, '1', 1), DoNothing(self.player_idx, self.gs)]

class RemoveCounterForLifeChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard,
                 counter_type: CounterType, counter_cnt: int = 1, gain_life_amt: int = 1):
        super().__init__(p_id, gs, source)
        self.counter_type = counter_type
        self.counter_cnt = counter_cnt
        self.gain_life_amt = gain_life_amt

    def get_actions(self) -> list[Action]:
        return [RemoveCounterGainLife(self.player_idx, self.gs, self.source,
                                      self.counter_type, self.counter_cnt, self.gain_life_amt),
                DoNothing(self.player_idx, self.gs)]

class SacChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, card_options: list[GameCard]):
        super().__init__(p_id, gs, source)
        self.card_options = card_options

    def get_actions(self) -> list[Action]:
        print('Card Options:', self.card_options)
        return [Sac(self.player_idx, self.gs, c) for c in self.card_options]

class ShuffleOrDontChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cards: list[GameCard]):
        super().__init__(p_id, gs, source)
        self.cards = cards

    def get_actions(self) -> list[Action]:
        return [Shuffle(self.player_idx, self.gs, self.cards), DoNothing(self.player_idx, self.gs)]

class UntapChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [LeaveTapped(self.player_idx, self.gs, self.source), UntapCardStackPop(self.player_idx, self.gs, self.source)]

class UntapWithManaChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, mana_cost: str):
        super().__init__(p_id, gs, source)
        self.mana_cost = mana_cost

    def get_actions(self) -> list[Action]:
        return [LeaveTapped(self.player_idx, self.gs, self.source),
                UntapWithManaAction(self.player_idx, self.gs, self.source, self.mana_cost)]

class XValueChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, eff_spec: EffSpec, aa: ActivatedAbility = None):
        super().__init__(p_id, gs, source)
        self.eff_spec = eff_spec
        self.selected_x: int | None = None
        self.aa = aa

    def get_actions(self) -> list[Action]:
        min_x = self.eff_spec.min_x
        max_x = self.eff_spec.max_x_func(self.gs, self.source)
        return [SelectXAction(self.player_idx, self.gs, self.source, self, x, self.aa) for x in range(min_x, max_x + 1)]

# --- CARD-SPECIFIC ---
class CosmicHorrorUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.player_idx].can_pay('3BBB'):
            actions.append(PayMana(self.player_idx, self.gs, self.source, '3BBB'))
        actions.append(Sac(self.player_idx, self.gs, self.source, 7))
        return actions

class CurseArtifactUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayLife(self.source.host.owner_id, self.gs, self.source, 2),
                Sac(self.source.host.owner_id, self.gs, self.source.host)]

class CycloneChoice(ChoiceAction):
    """At your upkeep, pay {G} for each wind counter on it or sac.
    If you pay, Cyclone deals damage = its wind counters to each creature and each player."""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [CyclonePayManaPerCounterDealDamage(self.player_idx, self.gs, self.source),
                Sac(self.player_idx, self.gs, self.source)]

class DemonicHordesUpkeepChoice(ChoiceAction):
    """It is known that the owner can pay {BBB}, so present the choice to pay or not;
    if the choice is made to not pay, must give the opponent the choice of which land to destroy (a nested choice)"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayMana(self.player_idx, self.gs, self.source, 'BBB'),
                AllowOpponentToDestroyALand(flip(self.player_idx), self.gs, self.source)]

class ElderSpawnUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        for island in self.gs.card_filter.on_player_board(self.player_idx).islands().result():
            actions.append(Sac(self.player_idx, self.gs, island))
        actions.append(Sac(self.player_idx, self.gs, self.source, 6))
        return actions

class ErhnamDjinnChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        opp_id = flip(self.source.owner_id)
        return [AddKWA(self.source.owner_id, self.gs, self.source, c, 'Forestwalk')
                for c in self.gs.card_filter.on_player_board(opp_id).non_artifact_creatures().result()]

class ErosionUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.player_idx].can_pay('1'):
            actions.append(PayMana(self.player_idx, self.gs, self.source, '1'))
        actions.append(PayLife(self.player_idx, self.gs, self.source, 1))
        actions.append(Sac(self.player_idx, self.gs, self.source.host))
        return actions

class FastingChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [SkipDrawPhaseGainLife(self.player_idx, self.gs, 2), Sac(self.player_idx, self.gs, self.source)]

class FloralSpuzzemChoice(ChoiceAction):
    """Whenever this creature walks, you may destroy target opp artifact instead of dealing the combat damage."""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        opp_artifacts = self.gs.card_filter.on_player_board(flip(self.source.owner_id)).artifacts().result()
        return [DestroyAndForegoCombatDamage(self.player_idx, self.gs, self.source, art)
                for art in opp_artifacts] + [DoNothing(self.player_idx, self.gs)]

class ForceOfNatureUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cost: str, damage_amt: int):
        super().__init__(p_id, gs, source)
        self.cost = cost
        self.damage_amt = damage_amt

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.player_idx].can_pay(self.cost):
            actions.append(PayMana(self.player_idx, self.gs, self.source, self.cost))
        actions.append(DealDamageToYou(self.player_idx, self.gs, self.source, self.damage_amt))
        return actions

class HealingSalveChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        all_targets = self.gs.card_filter.in_play().creatures().result() + [0, 1]
        return ([HealingSalveA(self.player_idx, self.gs, self.source)] +
                [HealingSalveB(self.player_idx, self.gs, self.source, t) for t in all_targets])

class LeviathanUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        your_island_cnt = len([i for i in self.gs.card_filter.on_player_board(self.player_idx).islands().result()])
        if your_island_cnt < 2:
            return []
        return [LeaveTapped(self.player_idx, self.gs, self.source), SacTwoIslands(self.player_idx, self.gs, self.source)]

class LordOfThePitUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        your_other_creatures = [c for c in self.gs.card_filter.on_player_board(self.player_idx).creatures().result()
                                if c is not self.source]
        return [Sac(self.gs.player_turn_idx, self.gs, c) for c in your_other_creatures]

class MoldDemonChoice(ChoiceAction):
    """Is called from MoldDemonETB; When this creature ETB, sac it or two Swamps; guaranteed to have >= 2 swamps"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard, your_swamps: list[GameCard]):
        super().__init__(p_id, gs, source)
        self.your_swamps = your_swamps

    def get_actions(self) -> list[Action]:
        two_swamp_combos = list(combinations(self.your_swamps, 2))
        sac_swamps = [SacCards(self.player_idx, self.gs, self.source, two_swamps) for two_swamps in two_swamp_combos]
        return [Sac(self.player_idx, self.gs, self.source)] + sac_swamps

class PrimalClayChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PrimalClayA(self.player_idx, self.gs, self.source), PrimalClayB(self.player_idx, self.gs, self.source),
                PrimalClayC(self.player_idx, self.gs, self.source)]

class PsychicAllergyUpkeepChoice(ChoiceAction):
    """... At your upkeep, destroy this enchantment unless you sacrifice two Islands"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [SacTwoIslands(self.player_idx, self.gs, self.source), Sac(self.player_idx, self.gs, self.source)]

class SacrificeCastChoice(ChoiceAction):
    """This is used by the card named 'Sacrifice'; is not a generic class about the concept of sacrifice"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        p_id = self.gs.player_turn_idx
        return [SacCreatureAndAddMana(self.player_idx, self.gs, self.source, c, 'B', c.props.casting_weight)
                for c in self.gs.card_filter.on_player_board(p_id).creatures().result()]

class SeasonOfTheWitchUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayLife(self.source.host.owner_id, self.gs, self.source, 2),
                Sac(self.gs.player_turn_idx, self.gs, self.source)]

class SerendibDjinnUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [Sac(self.gs.player_turn_idx, self.gs, land, w_damage_amt=3 if land.props.slug == 'island' else 0)
                for land in self.gs.card_filter.on_player_board(self.gs.player_turn_idx).lands().result()]

class ShapeshifterChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [VariablePTMod(self.player_idx, self.gs, self.source, self.source, i, 7 - i) for i in range(8)]

class TheAbyssChoice(ChoiceAction):
    """At each upkeep, destroy target nonartifact creature that player controls of their choice. No regeneration."""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        p_id = self.gs.player_turn_idx
        your_creatures = [c for c in self.gs.card_filter.on_player_board(p_id).non_artifact_creatures().result()]
        return [DestroyAction(p_id, self.gs, self.source, c, allow_regen=False) for c in your_creatures]

class TriassicEggChoice(ChoiceAction):
    """Choose one:
    * You may put a creature card from your hand onto the battlefield.
    * Return target creature card from your graveyard to the battlefield."""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        actions = []
        for card_in_hand in self.gs.hands[self.source.owner_id].cards:
            if card_in_hand.is_creature:
                actions.append(HandToBattlefield(self.player_idx, self.gs, card_in_hand))
        for card_in_graveyard in self.gs.graveyards[self.source.owner_id]:
            if card_in_graveyard.is_creature:
                actions.append(Reanimate(self.player_idx, self.gs, card_in_graveyard))
        return actions

class YawgmothDemonChoice(ChoiceAction):
    """At your upkeep, Sac an artifact, or tap this creature & it deals 2 damage to you"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        your_artifacts = self.gs.card_filter.on_player_board(self.player_idx).artifacts().result()
        return [Sac(self.player_idx, self.gs, a) for a in your_artifacts] + \
               [YawgmothDemonUnpaidUpkeep(self.player_idx, self.gs, self.source)]
