from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Callable

from models.events.events_all import StateBasedEvent, DiesEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from card_filter import CardFilter
from models.choice_actions.choice_actions_all import PayManaOrSacUpkeepChoice, ErosionUpkeepChoice, \
    ForceOfNatureUpkeepChoice, SacALandChoice, SeasonOfTheWitchUpkeepChoice, PsychicAllergyUpkeepChoice
from models.counter_tokens import PIN
from models.effects.base import Effect
from models.effects.piles import GraveyardToExile

# --- GENERICS --
class AcidRain(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        for forest in CardFilter(gs).in_play().by_slug('forest').result():
            gs.destroy(forest)

class Destroy(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.destroy(target)

class DestroyAll(Effect):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.destroy(c)

class DestroyIfItAttacked(Effect):
    """Destroy creature if it attacked this turn."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for t in gs.card_filter.attackers().result():
            gs.destroy(t)

class ExileAllCreatures(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        for c in CardFilter(gs).in_play().creatures().result():
            gs.exile(c)

class PayManaOrSac(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, target=None):
        gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, self.mana_cost), gs, False)

# --- CARD-SPECIFIC ---
class CyclopeanMummy(Effect):
    """When this creature dies, exile it"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.exile(source)

class EaterOfTheDeadAA(Effect):
    """Exile target creature card from a graveyard and untap this creature"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        GraveyardToExile().resolve(gs, source, target)
        source.untap(gs)

class ErosionUpkeep(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.action_stack.push(ErosionUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)

class ForceOfNatureUpkeep(Effect):
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    def resolve(self, gs: GameState, s: GameCard, target=None):
        gs.action_stack.push(ForceOfNatureUpkeepChoice(s.orig_owner_id, gs, s, 'GGGG', 8), gs, False)

class ManaVortexUpkeep(Effect):
    """At each player's upkeep, they sac a land. If no lands on entire battlefield, sac this enchantment."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if len(CardFilter(gs).lands().in_play().result()) == 0:
            gs.destroy(source)
            return
        for land in CardFilter(gs).on_player_board(gs.player_turn_idx).lands().result():
            SacALandChoice(gs.player_turn_idx, gs, land)

class PestilenceEndStep(Effect):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if not gs.card_filter.creatures().in_play().result():
            gs.destroy(s)

class PsychicAllergyUpkeep(Effect):
    """... At your upkeep, destroy this enchantment unless you sacrifice two Islands"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.player_turn_idx != source.owner_id:
            return
        your_island_cnt = len([i for i in gs.card_filter.on_player_board(source.owner_id).by_slug('island').result()])
        if your_island_cnt < 2:
            gs.destroy(source)
            return
        possible_actions = PsychicAllergyUpkeepChoice(gs.player_turn_idx, gs, source).get_actions()
        for action in possible_actions:
            gs.action_stack.push(action, gs, False)

class SandalsOfAbdallahIfCreatureDies(Effect):
    """When that creature [that Sandals gave Islandwalk to] dies this turn, destroy this artifact.."""

    def __init__(self, target_creature: GameCard):
        self.target_creature = target_creature

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != self.target_creature:
            return
        gs.destroy(source)


class SeasonOfTheWitchEndStep(Effect):
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has no Attack"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if gs.player_turn_idx != s.orig_owner_id:
            return
        your_untapped_creatures = gs.card_filter.on_player_board(s.orig_owner_id).creatures().untapped().result()
        attackers = gs.card_filter.attackers().result()
        for creature in your_untapped_creatures:
            if creature in attackers:
                continue
            if creature.has_summoning_sickness or 'Attack' not in creature.keyword_abilities:
                continue
            gs.destroy(creature)

class SeasonOfTheWitchUpkeep(Effect):
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        # Pause the game and force a choice
        gs.action_stack.push(SeasonOfTheWitchUpkeepChoice(source.orig_owner_id, gs, source), gs, False)

class SerendibDjinnNoLands(Effect):
    """When you control no lands, sacrifice this creature"""
    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        your_lands = gs.card_filter.on_player_board(source.orig_owner_id).lands().result()
        if not your_lands:
            print(f'Player #{source.orig_owner_id} has no lands, so Serendib Djinn is destroyed')
            gs.destroy(source)

class VoodooDollEndStep(Effect):
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.player_turn_idx != source.orig_owner_id:
            return
        if source.is_tapped:
            return
        if pin_cnt := source.counters.get_count(PIN) > 0:
            gs.apply_damage(source, pin_cnt, source.orig_owner_id)
        gs.destroy(source)