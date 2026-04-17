from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Callable

from models.events_all import StateBasedEvent, DiesEvent, ZoneChangeEvent, CombatEndEvent, TapCardEvent, UpkeepEvent, \
    DrawCardEvent, EndStepEvent
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.game_card_filter import CardFilter
from models.choice_actions_all import PayManaOrSacUpkeepChoice, ErosionUpkeepChoice, \
    ForceOfNatureUpkeepChoice, PsychicAllergyUpkeepChoice, SacChoice, \
    DemonicHordesUpkeepChoice, OpponentDestroysLandChoice, MoldDemonChoice, CosmicHorrorUpkeepChoice, PayLifeOrSacChoice
from models.counter_tokens import PIN
from models.effects.base import Effect
from models.effects.piles import GraveyardToExile
from models.modifiers import RegenerationMod

# --- GENERICS --
class Destroy(Effect):
    def __init__(self, allow_regen: bool = True):
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.destroy(target, allow_regeneration=self.allow_regen)

class DestroyAll(Effect):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]], allow_regen: bool = True):
        self.card_filter_func = card_filter_func
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.destroy(c, allow_regeneration=self.allow_regen)

class DestroyAtCombatEnd(Effect):
    """Destroys target if it is still on the battlefield; unregisters itself"""
    listens_to = CombatEndEvent

    def __init__(self, source: GameCard, target: GameCard):
        self.source = source
        self.target = target

    def on_event(self, gs: GameState, s: GameCard, event: CombatEndEvent):
        if self.target.zone == Zone.BATTLEFIELD:
            gs.destroy(self.target)
        gs.event_mgr.unregister_specific_effect(self)

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
        gs.action_stack.push(PayManaOrSacUpkeepChoice(source.owner_id, gs, source, self.mana_cost), gs, False)

class Regenerate(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(RegenerationMod(s=source, expires='EOT'))

class SacAll(Effect):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.destroy(c, allow_regeneration=False)

# --- CARD-SPECIFIC ---
class AshesToAshes(Effect):
    """Exile two target nonartifact creatures. Ashes to Ashes deals 5 damage to you."""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.exile(t)
        gs.apply_damage(source, 5, source.owner_id)

class Blight(Effect):
    """Enchant land; When enchanted land becomes tapped, destroy it."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if not source.host or source.props.slug != 'blight' or event.card is not source.host:
            return
        gs.destroy(source.host)

class CosmicHorror(Effect):
    """At your upkeep, destroy unless you pay {3BBB}. If destroyed this way, it deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        if not gs.mana_pools[source.owner_id].can_pay('3BBB'):
            gs.destroy(source)
            gs.apply_damage(source, 7, source.owner_id)
            return
        gs.action_stack.push(CosmicHorrorUpkeepChoice(source.owner_id, gs, source), gs, False)

class CyclopeanMummy(Effect):
    """When this creature dies, exile it"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.exile(source)

class DemonicHordesUpkeep(Effect):
    """... At your upkeep, pay {BBB} or tap this creature and sacrifice a land of an opponent's choice"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            gs.tap_card(source)
        elif len(your_lands) == 1:
            gs.tap_card(source)
            gs.destroy(your_lands[0])
        elif not gs.mana_pools[source.owner_id].can_pay('BBB'):
            gs.action_stack.push(OpponentDestroysLandChoice(flip(source.owner_id), gs, source))
        else:
            gs.action_stack.push(DemonicHordesUpkeepChoice(source.owner_id, gs, source), gs, False)

class DustToDust(Effect):
    """Exile two target artifacts"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.exile(t)

class EaterOfTheDead(Effect):
    """Exile target creature card from a graveyard and untap this creature"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        GraveyardToExile().resolve(gs, source, target)
        gs.untap_card(source)

class EnergyFlux(Effect):
    """All artifacts have 'At your [the owner's] upkeep, sacrifice this artifact unless you pay {2}'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_artifact in gs.card_filter.on_player_board(gs.player_turn_idx).artifacts().result():
            gs.action_stack.push(PayManaOrSacUpkeepChoice(gs.player_turn_idx, gs, your_artifact, '2'), gs, False)

class ErosionUpkeep(Effect):
    """At upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(ErosionUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)

class ForceOfNatureUpkeep(Effect):
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(ForceOfNatureUpkeepChoice(s.owner_id, gs, s, 'GGGG', 8), gs, False)

class LandEquilibrium(Effect):
    """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
    that player instead puts that land onto the battlefield then sacrifices a land of their choice"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id == event.card.owner_id or event.card not in gs.card_filter.land().result():
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_lands = gs.card_filter.on_player_board(event.card.owner_id).lands().result()
        if len(opp_lands) < your_land_cnt:
            return
        gs.action_stack.push(SacChoice(event.card.owner_id, gs, source, opp_lands), gs, False)

class ManaVortexUpkeep(Effect):
    """At each player's upkeep, they sac a land. If no lands on entire battlefield, sac this enchantment."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if len(gs.card_filter.lands().in_play().result()) == 0:
            gs.destroy(source)
            return
        your_lands = gs.card_filter.on_player_board(gs.player_turn_idx).lands().result()
        gs.action_stack.push(SacChoice(gs.player_turn_idx, gs, source, your_lands), gs, False)

class Millstone(Effect):
    """{2}, {T}: Target player mills two cards"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a player to target')
        for _ in range(2):
            top_card = gs.libraries[target][0]  # Warning: if no cards, this pukes
            gs.move_card(top_card, Zone.GRAVEYARD, cause='mill')

class MoldDemonETB(Effect):
    """When this creature enters, sacrifice this creature unless you sacrifice two Swamps"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.to_zone != Zone.BATTLEFIELD:
            return
        your_swamps = gs.card_filter.on_player_board(source.owner_id).swamps().result()
        if len(your_swamps) < 2:
            gs.destroy(event.card, False)
        gs.action_stack.push(MoldDemonChoice(gs.player_turn_idx, gs, source, your_swamps), gs, False)

class PestilenceEndStep(Effect):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if not gs.card_filter.creatures().in_play().result():
            gs.destroy(source)

class PsychicAllergyUpkeep(Effect):
    """... At your upkeep, destroy this enchantment unless you sacrifice two Islands"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        your_island_cnt = len([i for i in gs.card_filter.on_player_board(source.owner_id).islands().result()])
        if your_island_cnt < 2:
            gs.destroy(source)
            return
        possible_actions = PsychicAllergyUpkeepChoice(gs.player_turn_idx, gs, source).get_actions()
        for action in possible_actions:
            gs.action_stack.push(action, gs, False)

class SandalsOfAbdallahIfCreatureDies(Effect):
    """When that creature [that Sandals gave Islandwalk to] dies this turn, destroy this artifact"""

    def __init__(self, target_creature: GameCard):
        self.target_creature = target_creature

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != self.target_creature:
            return
        gs.destroy(source)

class SeasonOfTheWitchEndStep(Effect):
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has no Attack"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.player_turn_idx != s.owner_id:
            return
        your_untapped_creatures = gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result()
        attackers = gs.card_filter.attackers().result()
        for creature in your_untapped_creatures:
            if creature in attackers:
                continue
            if creature.has_summoning_sickness or 'Attack' not in creature.keyword_abilities:
                continue
            gs.destroy(creature)

class SeasonOfTheWitchUpkeep(Effect):
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        gs.action_stack.push(PayLifeOrSacChoice(source.owner_id, gs, source, 2), gs, False)

class SerendibDjinnNoLands(Effect):
    """When you control no lands, sacrifice this creature"""
    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            print(f'Player #{source.owner_id} has no lands, so Serendib Djinn is destroyed')
            gs.destroy(source)

class StanggOnLeave(Effect):
    """Exile that Stangg Twin token when Stangg leaves the battlefield; sacrific Stangg when Stangg Twin LTB"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.card.props.slug not in ('stangg', 'stangg-twin') or event.card.owner_id != source.owner_id:
            return
        if event.from_zone != Zone.BATTLEFIELD:
            return
        other_slug = 'stangg-twin' if event.card.props.slug == 'stangg' else 'stangg'
        other_card = gs.card_filter.on_player_board(event.card.owner_id).by_slug(other_slug).result()[0]
        gs.destroy(other_card)

class TheTabernacleAtPendrellVale(Effect):
    """All creatures have 'At your upkeep, destroy this creature unless you pay {1}.'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_creature in gs.card_filter.on_player_board(gs.player_turn_idx).creatures().result():
            gs.action_stack.push(PayManaOrSacUpkeepChoice(gs.player_turn_idx, gs, your_creature, '1'))

class UnderworldDreams(Effect):
    """Whenever an opponent draws a card, this enchantment deals 1 damage to that player"""
    listens_to = DrawCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardEvent):
        if source.owner_id == event.player_id:
            return
        gs.apply_damage(source, 1, event.player_id)

class VoodooDollEndStep(Effect):
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        if source.is_tapped:
            return
        if pin_cnt := source.counters.get_count(PIN) > 0:
            gs.apply_damage(source, pin_cnt, source.owner_id)
        gs.destroy(source)
