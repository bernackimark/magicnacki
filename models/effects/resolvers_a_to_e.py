from __future__ import annotations
import math
from itertools import combinations
from typing import TYPE_CHECKING, Optional

from models.actions.draw_discard import DiscardCards
from models.actions.piles import Tutor
from models.actions.special import CopyCard
from models.choice_actions_all import ChoiceAction
from models.counter_tokens import STORAGE, PUPA, PLUS_ONE
from models.effects.base import Resolver
from models.effects.listeners_generic import DestroyAtEndStepIfItAttacked
from models.effects.listeners_mod_queries import ArmyOfAllahEOT
from models.effects.resolvers_generic import GraveyardToExile, CreateTokenCreature
from models.modifiers import OwnershipMod, SubTypeMod, PTMod, KWAMod
from models.systems.phase import Phase
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class ActiveVolcano(Resolver):
    """Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pile_mgr.bounce(t) if t.props.slug == 'island' else gs.pile_mgr.destroy(t)

class Amnesia(Resolver):
    """Target player reveals their hand and discards all nonland cards"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for c in gs.pile_mgr.hands[target][:]:
            c.reveal()
            if 'Land' not in c.card_types:
                gs.pile_mgr.discard(c, source)

class AnimateDead(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.pile_mgr.reanimate(target)
        target.modifiers.append(PTMod(s=source, p_adj=-1, t_adj=0))

class ArenaOfTheAncientsCast(Resolver):
    """When this artifact enters, tap all legendary creatures"""
    def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().untapped().legendary().result():
            c.tap()

class AshesToAshes(Resolver):
    """Exile two target nonartifact creatures. Ashes to Ashes deals 5 damage to you."""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.pile_mgr.exile(t)
        gs.apply_damage(source, 5, source.owner_id)

class AshnodsTransmogrant(Resolver):
    """{T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature.
    That creature becomes an artifact in addition to its other types."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise RuntimeError(f'{s.props.name} needs a target')
        t.counters.add_counter(PLUS_ONE)
        t.card_types.append('Artifact')

class Banshee(Resolver):
    """{X}, {T}: This creature deals half X damage, rounded down, to any target, and half X damage, rounded up to you"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        x = s.extras.get('x', 0)
        damage_to_target = x // 2
        damage_to_you = x - damage_to_target
        gs.apply_damage(s, damage_to_target, t)
        gs.apply_damage(s, damage_to_you, s.owner_id)
        del s.extras['x']

class BazaarOfBaghdad(Resolver):
    """Draw two cards, then discard three cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.pile_mgr.draw(source.owner_id, 2)
        cards = gs.pile_mgr.hands[source.owner_id]
        if len(cards) <= 2:
            for c in cards[:]:
                cards.remove(c)
            return
        options = [DiscardCards(source.owner_id, gs, list(combo))
                   for r in range(3, 4) for combo in combinations(cards, r)]
        gs.pending_choice = ChoiceAction(options)

class Berserk(Resolver):
    """Cast this spell only before the combat damage step.
    Target creature gains trample and gets +X/+0 until end of turn, where X is its power.
    At end step, destroy that creature if it attacked this turn."""
    def can_cast(self, gs: GameState, source: GameCard) -> bool:
        return gs.phase_mgr.phase < Phase.COMBAT_DAMAGE

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None) -> None:
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(PTMod(s=source, p_adj=target.power, expires='EOT'))
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Trample', expires='EOT'))
        gs.event_mgr.register(DestroyAtEndStepIfItAttacked(target), source)

class BloodLust(Resolver):
    """Target creature gains +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1."""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        new_toughness = max(1, target.toughness - 4)
        toughness_mod = new_toughness - target.toughness
        target.modifiers.append(PTMod(s=source, p_adj=4, t_adj=toughness_mod, expires='EOT'))

class BookOfRass(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.apply_damage(source, 2, source.owner_id)
        gs.pile_mgr.draw(source.owner_id)

class BottleOfSuleiman(Resolver):
    """{1}, Sac: Flip a coin. If you win the flip, create a 5/5 colorless Djinn artifact creature token with flying.
    If you lose the flip, this artifact deals 5 damage to you."""
    def resolve(self, gs: GameState, s: GameCard, _: GameCard = None):
        result: str = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        if result == 'heads':
            obj = CreateTokenCreature('djinn')
            obj.resolve(gs, s)
            # gs.create_token_creature(s.owner_id, 'Djinn', 5, 5, ['Flying', 'Attack'],
            #                          other_types=[], sub_types=['Djinn'], colors='C')
        else:
            gs.apply_damage(s, 5, s.owner_id)

class Braingeyser(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is not None:
            x = source.extras.get('x', 0)  # read X chosen when casting
            gs.pile_mgr.draw(target, x)

class ChaosOrb(Resolver):
    """{1}, {T}, Sac: Choose an opponent's non-token permanent. If random di roll is 1-4, destroy target."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        result: int = gs.randomize_event(s.owner_id, [1, 2, 3, 4, 5, 6])
        if result <= 4:
            gs.pile_mgr.destroy(t)

class CityOfShadowsAddCounter(Resolver):
    """{T}, Exile a creature you control: Put a storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        source.counters.add_counter(STORAGE)

class CityOfShadowsAddMana(Resolver):
    """{T}: Add {C} for each storage counter on this land"""
    def can_activate(self, gs: GameState, source: GameCard) -> bool:
        return source.counters.get_count(STORAGE) > 0

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        cnt = source.counters.get_count(STORAGE)
        gs.mana_pools[source.owner_id].add_floating('C', cnt)

class Clone(Resolver):
    """You may have this creature enter as a copy of any creature on the battlefield;
    pushes valid targets to the stack for user selection, which then calls an Action that copies select target attrs"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        options = [CopyCard(s.owner_id, gs, s, card) for card in card_options]
        gs.pending_choice = ChoiceAction(options)

class CocoonCast(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.tap()
        source.counters.add_counter(PUPA, 3)

class CopyArtifact(Resolver):
    """You may have this enchantment enter as a copy of any artifact on the battlefield,
    except it's an enchantment in addition to its other types"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().artifacts().result() if c is not s]
        if not card_options:
            return
        options = [CopyCard(s.owner_id, gs, s, card) for card in card_options]
        gs.pending_choice = ChoiceAction(options)

class Crumble(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.pile_mgr.destroy(target, allow_regeneration=False)
            gs.score_mgr.increment_life(target.owner_id, target.props.mana_value, source, gs)

class DemonicTutor(Resolver):
    """Search your library for a card, put that card into your hand, then shuffle"""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        p_id = source.owner_id
        library_cards = gs.pile_mgr.libraries[p_id]
        gs.add_presentation_request(p_id, 'search_library', {'cards': library_cards})
        options = [Tutor(p_id, gs, source, c, Zone.HAND) for c in library_cards]
        gs.pending_choice = ChoiceAction(options)

class Disharmony(Resolver):
    """Cast this spell only during combat before blockers are declared.
    Untap target attacking creature and remove it from combat. Gain control of that creature until end of turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.untap()
        gs.combat_mgr.remove_from_combat(target)
        target.modifiers.append(OwnershipMod(source.owner_id, s=source, expires='EOT'))

class DivineOffering(Resolver):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target")
        gs.pile_mgr.destroy(target)
        gs.score_mgr.increment_life(source.owner_id, target.props.mana_value, source, gs)

class DrainPower(Resolver):
    """Target player activates a mana ability of each land they control.
    Then that player loses all unspent mana & you add the mana lost this way."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose available mana will be targeted & given to the other player"""
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        land_giver_mana = gs.mana_pools[target].available_mana.copy()
        for color, amt in land_giver_mana.items():
            gs.mana_pools[source.owner_id].add_floating(color, amt)

class DustToDust(Resolver):
    """Exile two target artifacts"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.pile_mgr.exile(t)

class Earthbind(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.append(KWAMod(s=source, add_or_remove='remove', kwa='Flying'))
        if 'Flying' in target.keyword_abilities:
            gs.apply_damage(source, 2, target.owner_id)

class Earthquake(Resolver):
    """Earthquake deals X damage to each creature without flying and each player"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = source.extras.get('x', 0)  # read X chosen when casting
        for c in gs.card_filter.in_play().has('Flying', False).creatures().result():
            gs.apply_damage(source, x, c)
        for p_id in (0, 1):
            gs.apply_damage(source, x, p_id)

class EaterOfTheDead(Resolver):
    """Exile target creature card from a graveyard and untap this creature"""
    def can_activate(self, _: GameState, source: GameCard):
        return source.is_tapped

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        GraveyardToExile().resolve(gs, source, target)
        source.untap()

class ElectricEel(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.append(PTMod(s=source, p_adj=2, expires='EOT'))
        gs.apply_damage(source, 1, source.owner_id)

class ElvesOfTheDeepShadow(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.mana_pools[source.owner_id].add_floating('B')
        gs.apply_damage(source, 1, source.owner_id)

class EnchantmentAlteration(Resolver):
    """Attach target Aura attached to a creature or land to another permanent of that type"""
    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None) -> None:
        if target is None:
            raise ValueError(f'{s.props.name} needs a target')
        if target.host.is_creature:
            available_hosts = [c for c in gs.card_filter.in_play().creatures().result() if c is not target.host]
        elif target.host.is_land:
            available_hosts = [c for c in gs.card_filter.in_play().lands().result() if c is not target.host]
        else:
            return
        from models.actions.special import Attach
        options = [Attach(s.owner_id, gs, s, host) for host in available_hosts]
        gs.pending_choice = ChoiceAction(options)

class EnergyTap(Resolver):
    """Tap target untapped creature you control to add an amount of {C} equal to that creature's mana value."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            return
        target.tap()
        gs.mana_pools[source.owner_id].add_floating('C', source.props.mana_value)
        print(f"{source} taps to add {source.props.mana_value} colorless to your mana pool.")

class EternalFlame(Resolver):
    """X = # of mountains caster controls; deal x damage to opponent and round(x/2) to caster"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = len(gs.card_filter.on_player_board(gs.player_turn_idx).mountains().result())
        gs.apply_damage(source, x, flip(gs.player_turn_idx))
        gs.apply_damage(source, math.ceil(x/2), gs.player_turn_idx)

class EvilPresence(Resolver):
    """Enchant land Enchanted land is a Swamp"""

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        sub_types = target.card_sub_types.copy()
        target.modifiers.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type='Swamp'))
        for sub_type in sub_types:
            target.modifiers.append(SubTypeMod(s=source, add_or_remove='remove', card_sub_type=sub_type))

class ExchangeLifeTotals(Resolver):
    def resolve(self, gs: GameState, s: GameCard, _: Optional[GameCard] = None):
        your_life = gs.life[s.owner_id]
        opp_life = gs.life[flip(s.owner_id)]
        gs.life[s.owner_id], gs.life[flip(s.owner_id)] = opp_life, your_life

class EyeForAnEye(Resolver):
    """The next time a source of your choice would deal damage to you this turn, also deal damage to source's owner."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        """target = the GameCard doing the original damage"""
        from models.effects.listeners_damage import EyeForAnEyeEOT
        gs.event_mgr.register(EyeForAnEyeEOT(damage_dealer=t, damage_receiving_player=s.owner_id), s)
