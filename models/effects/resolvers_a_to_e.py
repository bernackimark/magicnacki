from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from itertools import combinations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO, copy_card
from models.constants import KW, Zone
from models.game_card.counter_tokens import STORAGE, PUPA, PLUS_ONE
from models.effects.base import Resolver, RTarget, ResContext
from models.effects.listeners_generic import DestroyAtEndStepIfItAttacked, LTBTandem, ExileOnDeath
from models.effects.listeners_mod_queries import OwnershipModQuery
from models.effects.listeners_permission import PreventRegenerationEOT
from models.effects.resolvers_generic import GraveyardToExile, CreateTokenCreature
from models.game_card.modifiers import SubTypeMod, PTMod, KWAMod
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class Amnesia(Resolver):
    """Target player reveals their hand and discards all nonland cards"""

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for c in gs.pile_mgr.hands[t][:]:
            c.reveal()
            if 'Land' not in c.card_types:
                gs.pile_mgr.discard(c, source)

class ArenaOfTheAncientsCast(Resolver):
    """When this artifact enters, tap all legendary creatures"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for c in gs.card_filter.in_play().creatures().untapped().legendary().result():
            c.tap()

class AshesToAshes(Resolver):
    """Exile two target nonartifact creatures. Ashes to Ashes deals 5 damage to you."""

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for t in t:
            gs.pile_mgr.exile(t)
        gs.apply_damage(source, 5, source.owner_id)

class AshnodsTransmogrant(Resolver):
    """{T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature.
    That creature becomes an artifact in addition to its other types."""

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.counters.add_counter(PLUS_ONE)
        t.card_types.append('Artifact')

class Banshee(Resolver):
    """{X}, {T}: This creature deals half X damage, rounded down, to any target, and half X damage, rounded up to you"""

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        x = context.x_value
        damage_to_target = x // 2
        damage_to_you = x - damage_to_target
        gs.apply_damage(source, damage_to_target, t)
        gs.apply_damage(source, damage_to_you, source.owner_id)

class BazaarOfBaghdad(Resolver):
    """Draw two cards, then discard three cards"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.draw(source.owner_id, 2)
        cards = gs.pile_mgr.hands[source.owner_id]
        if len(cards) <= 3:
            gs.pile_mgr.discards(cards, source=source)
            return
        combos = [list(combo) for combo in combinations(cards, 3)]
        options = [CO(f"Discard {', '.join(combo)}", lambda: gs.pile_mgr.discards(combo)) for combo in combos]
        gs.choice_mgr.queue(ChoiceAction(options))

class Berserk(Resolver):
    """Cast this spell only before the combat damage step.
    Target creature gains trample and gets +X/+0 until end of turn, where X is its power.
    At end step, destroy that creature if it attacked this turn."""

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(PTMod(s=source, p_adj=t.power, expires='EOT'))
        t.modifiers.append(KWAMod(s=source, item=KW.TRAMPLE, expires='EOT'))
        gs.event_mgr.register(DestroyAtEndStepIfItAttacked(t), source)

class BloodLust(Resolver):
    """Target creature gains +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        new_toughness = max(1, t.toughness - 4)
        toughness_mod = new_toughness - t.toughness
        t.modifiers.append(PTMod(s=source, p_adj=4, t_adj=toughness_mod, expires='EOT'))

class BottleOfSuleiman(Resolver):
    """{1}, Sac: Flip a coin. If you win the flip, create a 5/5 colorless Djinn artifact creature token with flying.
    If you lose the flip, this artifact deals 5 damage to you."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        result: str = gs.randomize_event(source.owner_id, ['heads', 'tails'])
        if result == 'heads':
            obj = CreateTokenCreature('djinn')
            obj.resolve(gs, source)
        else:
            gs.apply_damage(source, 5, source.owner_id)

class Braingeyser(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        if t is not None:
            x = context.x_value
            gs.pile_mgr.draw(t, x)

class ChaosOrb(Resolver):
    """{1}, {T}, Sac: Choose an opponent's non-token permanent. If random di roll is 1-4, destroy target."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        result: int = gs.randomize_event(source.owner_id, [1, 2, 3, 4, 5, 6])
        if result <= 4:
            gs.pile_mgr.destroy(t)

class CityOfShadowsAddCounter(Resolver):
    """{T}, Exile a creature you control: Put a storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        source.counters.add_counter(STORAGE)

class CityOfShadowsAddMana(Resolver):
    """{T}: Add {C} for each storage counter on this land"""
    def can_activate(self, gs: GameState, source: GameCard) -> bool:
        return source.counters.get_count(STORAGE) > 0

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        cnt = source.counters.get_count(STORAGE)
        gs.mana_pools[source.owner_id].add_floating('C', cnt)

class Cleansing(Resolver):
    """For each land, destroy that land unless any player pays 1 life"""
    @dataclass
    class CleansingState:
        lands: list[GameCard]
        land_idx: int = 0
        player_cnt_acted_on_this_land: int = 0
        saved_lands: list[GameCard] = field(default_factory=list)

        @property
        def active_land(self) -> GameCard:
            return self.lands[self.land_idx]

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        lands = gs.card_filter.in_play().lands().result()
        if not lands:
            return

        state = Cleansing.CleansingState(lands)
        self.queue_next_choice(gs, source, state)

    def queue_next_choice(self, gs: GameState, source: GameCard, state: CleansingState):
        # Finished all lands
        if state.land_idx >= len(state.lands):
            print('Entering exit flow')
            for land in state.lands:
                if land not in state.saved_lands:
                    gs.pile_mgr.destroy(land)
            self.gs.choice_mgr.clear_current()
            return

        # Move to next land if both players declined to save or someone did save it
        if state.player_cnt_acted_on_this_land >= 2 or state.active_land in state.saved_lands:
            print('Moving to next card')
            state.land_idx += 1
            state.player_cnt_acted_on_this_land = 0
            self.queue_next_choice(gs, source, state)
            return

        options = [CO(f"Pay 1 life to save Player #{state.active_land.owner_id}'s {state.active_land}",
                      lambda: self.pay_cleansing(gs, source.owner_id, source, state)),
                   CO(f"Decline saving Player #{state.active_land.owner_id}'s {state.active_land}",
                      lambda: self.decline_cleansing(gs, source, state))]
        gs.choice_mgr.queue(ChoiceAction(options))

    def decline_cleansing(self, gs: GameState, s: GameCard, state: CleansingState):
        state.player_cnt_acted_on_this_land += 1
        # Ask the next player
        gs.action_on_idx = flip(gs.action_on_idx)
        self.queue_next_choice(gs, s, state)

    def pay_cleansing(self, gs: GameState, p_id: int, s: GameCard, state: CleansingState):
        gs.score_mgr.decrement_life(p_id, 1, s, gs)
        state.saved_lands.append(state.active_land)

        # Move immediately to next land
        state.land_idx += 1
        gs.action_on_idx = flip(gs.action_on_idx)
        self.queue_next_choice(gs, s, state)


class Clone(Resolver):
    """You may have this creature enter as a copy of any creature on the battlefield"""
    def resolve(self, gs: GameState, s: GameCard, t: RTarget = None, context: ResContext = None):
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        options = [CO(f'{s} copies {t}', lambda: copy_card(gs, s, t)) for t in card_options]
        gs.choice_mgr.queue(ChoiceAction(options))

class CocoonCast(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.tap()
        source.counters.add_counter(PUPA, 3)

class ConsecrateLand(Resolver):
    """Enchanted land has indestructible and can't be enchanted by other Auras"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        from models.effects.listeners_permission import CantBeTargetedByAuras
        gs.event_mgr.register(CantBeTargetedByAuras(protected_card=t), source)
        t.modifiers.append(KWAMod(s=source, item=KW.INDESTRUCTIBLE))

class CopyArtifact(Resolver):
    """You may have this enchantment enter as a copy of any artifact on the battlefield,
    except it's an enchantment in addition to its other types"""
    def resolve(self, gs: GameState, s: GameCard, t: RTarget = None, context: ResContext = None):
        card_options = [c for c in gs.card_filter.in_play().artifacts().result() if c is not s]
        if not card_options:
            return
        options = [CO(f'{s} copies {t}', lambda: copy_card(gs, s, t)) for t in card_options]
        gs.choice_mgr.queue(ChoiceAction(options))

class Crumble(Resolver):
    """Destroy target artifact. It can't be regenerated. That artifact's controller gains life = its MV."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.destroy(t, allow_regeneration=False)
        gs.score_mgr.increment_life(t.owner_id, t.props.mana_value, source, gs)

class CuombajjWitches(Resolver):
    """{T}: CW deals 1 damage to any target and 1 damage to any target of an opponent's choice"""
    @Resolver.target_required
    def resolve(self, gs: GameState, s: GameCard, t: RTarget = None, context: ResContext = None):
        gs.apply_damage(s, 1, t)
        targets = gs.card_filter.in_play().creatures().result() + [0, 1]
        options = [CO(f'{s.props.name} deals 1 damage to {target}',
                      lambda chosen_target=target: gs.apply_damage(s, 1, chosen_target)) for target in targets]
        gs.choice_mgr.queue(ChoiceAction(options))

class DanceOfMany(Resolver):
    """When DOM ETB, create a token copy of target nontoken creature -- copies its original props w/o mods ...
    When DOM LTB, exile the token. When the token LTB, sac DOM"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        from models.game_card.game_card import GameCard
        the_copy = GameCard(t.props, source.owner_id, is_token=True)
        the_copy.game_state = gs
        the_copy.zone = t.zone
        the_copy.turn_entered_for_owner = gs.turn_mgr.turn_number
        gs.pile_mgr.boards[source.owner_id].append(the_copy)
        gs.event_mgr.register_card(the_copy)
        gs.event_mgr.register(LTBTandem([source, the_copy]), source)

class DemonicTutor(Resolver):
    """Search your library for a card, put that card into your hand, then shuffle"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        p_id = source.owner_id
        lib = gs.pile_mgr.libraries[p_id]
        gs.add_presentation_request(p_id, 'search_library', {'cards': lib})
        options = [CO(f'Tutor {c}', lambda: self.tutor(gs, lib, c, Zone.HAND)) for c in lib]
        # options = [Tutor(p_id, gs, source, c, Zone.HAND) for c in lib]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def tutor(gs: GameState, lib: list[GameCard], card: GameCard, to_zone: Zone):
        gs.pile_mgr.move_card(card, to_zone)
        random.shuffle(lib)

class DiamondValley(Resolver):
    """{T}, Sacrifice a creature: You gain life equal to the sacrificed creature's toughness"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        amt = context.cost_result.paid_cards[0].toughness
        gs.score_mgr.increment_life(source.owner_id, amt, source, gs)

class Disharmony(Resolver):
    """Cast this spell only during combat before blockers are declared.
    Untap target attacking creature and remove it from combat. Gain control of that creature until end of turn."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.untap()
        gs.combat_mgr.remove_from_combat(t)
        gs.event_mgr.register(OwnershipModQuery(t, eot=True), source)

class Disintegrate(Resolver):
    """D deals X damage to any target. If it's a creature, no regen allow EOT, & if it would die EOT, exile instead."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        damage_amt = context.x_value
        if not damage_amt:
            raise ValueError(f'{source.props.name} needs an X value')
        if not isinstance(t, int):
            gs.event_mgr.register(ExileOnDeath(t, eot=True), source)
            gs.event_mgr.register(PreventRegenerationEOT(t), source)
        gs.apply_damage(source, damage_amt, t)

class DivineOffering(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.destroy(t)
        gs.score_mgr.increment_life(source.owner_id, t.props.mana_value, source, gs)

class DrainPower(Resolver):
    """Target player activates a mana ability of each land they control.
    Then that player loses all unspent mana & you add the mana lost this way."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        """target = player_id whose available mana will be targeted & given to the other player"""
        land_giver_mana = gs.mana_pools[t].available_mana.copy()
        for color, amt in land_giver_mana.items():
            gs.mana_pools[source.owner_id].add_floating(color, amt)

class DrafnasRestoration(Resolver):
    """Put any number of target artifact cards from target player's graveyard on top of their library in ANY ORDER"""
    @dataclass
    class DrafnasRestorationState:
        all_artifacts_in_target_gy: list[GameCard]
        selected_cards: list[GameCard] = field(default_factory=list)

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        all_cards = gs.card_filter.in_player_graveyard(t).artifacts().result()
        if not all_cards:
            return

        state = DrafnasRestoration.DrafnasRestorationState(all_cards)
        self.queue_next_choice(gs, state)

    def queue_next_choice(self, gs: GameState, state: DrafnasRestorationState):
        if len(state.selected_cards) >= len(state.all_artifacts_in_target_gy):
            options = [CO("Finish selecting artifacts", lambda: self.finish_selecting(gs, state))]
        else:
            remaining = [c for c in state.all_artifacts_in_target_gy if c not in state.selected_cards]
            options = [CO("Finish selecting artifacts", lambda: self.finish_selecting(gs, state))] + \
                      [CO(f"Move {c} to library; subsequent artifacts will be placed above this card",
                          lambda c=c: self.select_card(gs, state, c)) for c in remaining]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def finish_selecting(gs: GameState, state: DrafnasRestorationState):
        for card in state.selected_cards:
            gs.pile_mgr.move_card(card, Zone.LIBRARY)

    def select_card(self, gs: GameState, state: DrafnasRestorationState, card: GameCard):
        state.selected_cards.append(card)
        self.queue_next_choice(gs, state)

class DustToDust(Resolver):
    """Exile two target artifacts"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for target in t:
            gs.pile_mgr.exile(target)

class Earthbind(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(KWAMod(s=source, add_or_remove='remove', item=KW.FLYING))
        if KW.FLYING in t.keyword_abilities:
            gs.apply_damage(source, 2, t.owner_id)

class Earthquake(Resolver):
    """Earthquake deals X damage to each creature without flying and each player"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        x = context.x_value
        for c in gs.card_filter.in_play().has(KW.FLYING, False).creatures().result():
            gs.apply_damage(source, x, c)
        for p_id in (0, 1):
            gs.apply_damage(source, x, p_id)

class EaterOfTheDead(Resolver):
    """Exile target creature card from a graveyard and untap this creature"""
    def can_activate(self, _: GameState, source: GameCard):
        return source.is_tapped

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        GraveyardToExile().resolve(gs, source, t)
        source.untap()

class ElectricEel(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        source.modifiers.append(PTMod(s=source, p_adj=2, expires='EOT'))
        gs.apply_damage(source, 1, source.owner_id)

class ElvesOfTheDeepShadow(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.mana_pools[source.owner_id].add_floating('B')
        gs.apply_damage(source, 1, source.owner_id)

class EnchantmentAlteration(Resolver):
    """Attach target Aura attached to a creature or land to another permanent of that type"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        if t.host.is_creature:
            available_hosts = [c for c in gs.card_filter.in_play().creatures().result() if c is not t.host]
        elif t.host.is_land:
            available_hosts = [c for c in gs.card_filter.in_play().lands().result() if c is not t.host]
        else:
            return
        options = [CO(f'Attach {t} to {host}', lambda: self.attach(t, host)) for host in available_hosts]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def attach(aura: GameCard, host: GameCard):
        aura.host = host
        host.auras.append(aura)

class EnergyTap(Resolver):
    """Tap target untapped creature you control to add an amount of {C} equal to that creature's mana value."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.tap()
        gs.mana_pools[source.owner_id].add_floating('C', source.props.mana_value)
        print(f"{source} taps to add {source.props.mana_value} colorless to your mana pool.")

class EternalFlame(Resolver):
    """X = # of mountains caster controls; deal x damage to opponent and round(x/2) to caster"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        x = len(gs.card_filter.on_player_board(gs.player_turn_idx).mountains().result())
        gs.apply_damage(source, x, flip(gs.player_turn_idx))
        gs.apply_damage(source, math.ceil(x/2), gs.player_turn_idx)

class Eureka(Resolver):
    """Both players may take any permanent in their hand and put it directly into play.
    Players take turns playing one card from their hand until neither wants to play more permanents.
    No other spells/effects of any kind may be used while E is in effect. If a spell has an X in casting cost, X=0."""
    @dataclass
    class EurekaState:
        current_player: int
        players_who_are_done: list[int] = field(default_factory=list)

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        all_perms = [[c for c in h if c.is_permanent] for h in gs.hands]
        if not all_perms:
            return

        state = Eureka.EurekaState(gs.player_turn_idx)
        self.queue_next_choice(gs, state)

    def queue_next_choice(self, gs: GameState, state: EurekaState):
        if sorted(state.players_who_are_done) == [0, 1]:
            gs.choice_mgr.clear_current()
            return

        if state.current_player in state.players_who_are_done:
            state.current_player = flip(state.current_player)
            self.queue_next_choice(gs, state)
            return

        gs.action_on_idx = state.current_player

        perms_in_hand = [c for c in gs.hands[state.current_player] if c.is_permanent]
        options = [CO(f"Play {c} to your board", lambda c=c: self.play_card(gs, gs.action_on_idx, state, c))
                   for c in perms_in_hand] + \
                  [CO("Finish playing permanents to your board",
                      lambda: self.finish_playing(gs, gs.action_on_idx, state))]
        choice = ChoiceAction(options)
        gs.choice_mgr.queue(choice)

    def finish_playing(self, gs: GameState, p_id: int, state: EurekaState):
        state.players_who_are_done.append(p_id)
        state.current_player = flip(p_id)
        gs.choice_mgr.clear_current()
        self.queue_next_choice(gs, state)

    def play_card(self, gs: GameState, p_id: int, state: EurekaState, card: GameCard):
        gs.pile_mgr.move_card(card, Zone.BATTLEFIELD, cause='eureka', emit_zone_event=False)
        state.current_player = flip(p_id)
        gs.choice_mgr.clear_current()
        self.queue_next_choice(gs, state)

class EvilPresence(Resolver):
    """Enchant land Enchanted land is a Swamp"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        sub_types = t.card_sub_types.copy()
        t.modifiers.append(SubTypeMod(s=source, item='Swamp'))
        for sub_type in sub_types:
            t.modifiers.append(SubTypeMod(s=source, add_or_remove='remove', item=sub_type))

class ExchangeLifeTotals(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        your_life = gs.life[source.owner_id]
        opp_life = gs.life[flip(source.owner_id)]
        gs.life[source.owner_id], gs.life[flip(source.owner_id)] = opp_life, your_life
