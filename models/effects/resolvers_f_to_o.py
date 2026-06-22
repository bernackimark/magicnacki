from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

from models.choice_actions_all import FalseOrdersChoice, DiscardChoice, NaturalSelectionChoice, FastingChoice, \
    HealingSalveChoice, RemoveCounterForLifeChoice, NamelessRaceChoice
from models.counter_tokens import MINUS_ZERO_ONE, HUNGER, VITALITY
from models.effects.base import Resolver
from models.effects.listeners_card_specific import HazezonTamarTokenCreation
from models.effects.listeners_combat import GlyphOfDoomListener
from models.effects.listeners_damage import GlyphOfLifeListener
from models.effects.listeners_generic import PreventNextDamageByEOT, PreventNextDamageToCardEOT, PreventAllDamageToEOT, \
    DestroyAtEndStep
from models.effects.listeners_mod_queries import HellSwarmEOT, HolyLightEOT, MarshGasEOT, MoraleEOT
from models.effects.listeners_permission import NoAttacksAllowedEOT
from models.effects.resolvers_generic import GraveyardToExile
from models.modifiers import PTMod, KWAMod
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class FalseOrders(Resolver):
    """... Remove target blocker from a combat. You may have it block in a different legal combat."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        other_combats = [com for com in gs.combat_mgr.combats if target not in com.blockers]
        gs.combat_mgr.remove_from_combat(target)
        if other_combats:
            gs.pending_choice = FalseOrdersChoice(source.owner_id, gs, source)


class GlyphOfDoom(Resolver):
    """On cast, select a wall.  Register GlyphOfDoomListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.event_mgr.register(GlyphOfDoomListener(target), source)


class GlyphOfLife(Resolver):
    """On cast, select a wall.  Register GlyphOfLifeListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.event_mgr.register(GlyphOfLifeListener(target), source)


class HazezonTamar(Resolver):
    """When HT enters, create X 1/1 Sand Warrior RGW creature tokens at your NEXT upkeep;
    (from online rulings) whoever owns HT when cast will own the tokens, even if HT dies or transfers owners"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        gs.event_mgr.register(HazezonTamarTokenCreation(source.owner_id), source)


class JovialEvil(Resolver):
    """deals X damage to target opponent, where X is twice the number of white creatures that player controls"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        # target = opponent_id
        opp_white_creature_cnt = len(gs.card_filter.on_player_board(target).creatures().result())
        gs.apply_damage(source, opp_white_creature_cnt * 2, target)


class Millstone(Resolver):
    """{2}, {T}: Target player mills two cards"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a player to target')
        for _ in range(2):
            top_card = gs.pile_mgr.libraries[target][0]  # Warning: if no cards, this pukes
            gs.pile_mgr.move_card(top_card, Zone.GRAVEYARD, cause='mill')


class GlassesOfUrza(Resolver):
    """Look at opponent's hand"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        for c in gs.pile_mgr.hands[flip(source.owner_id)].cards:
            c.reveal()


class GwendlynDiCorci(Resolver):
    """{T}: Target player discards a card at random. Activate only during your turn"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        cards = gs.pile_mgr.hands[target].cards
        if not cards:
            return
        if len(cards) == 1:
            gs.pile_mgr.discard(cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(target, cards)
        gs.pile_mgr.discard(random_card, source)


class JalumTome(Resolver):
    """Draw a card, then discard a card"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.pile_mgr.draw(source.owner_id)
        gs.pending_choice = DiscardChoice(source.owner_id, gs, source, source.owner_id)


class MindTwist(Resolver):
    """Target player discards X cards at random"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = source.extras.get('x', 0)  # read X chosen when casting
        opp_id = flip(source.owner_id)
        opp_cards = gs.pile_mgr.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) <= x:
            for c in opp_cards:
                gs.pile_mgr.discard(c, source)
            return
        for _ in range(x):
            random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
            gs.pile_mgr.discard(random_card, source)


class NaturalSelection(Resolver):
    """Look at the top 3 cards of target player's library, put them back in any order. You may shuffle."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        top_3_cards = gs.pile_mgr.libraries[target][:3]
        gs.add_presentation_request(source.owner_id, 'show_library', {'cards': top_3_cards})
        gs.pending_choice = NaturalSelectionChoice(source.owner_id, gs, source, target, top_3_cards)


class GraveRobbersAA(Resolver):
    """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        GraveyardToExile().resolve(gs, source, target)
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)


class GreatDefender(Resolver):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        """Target creature gets +0/+X until end of turn, where X is its mana value."""
        if target:
            target.modifiers.append(PTMod(s=source, t_adj=target.props.mana_value, expires='EOT'))


class HellSwarm(Resolver):
    """All creatures get -1/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.event_mgr.register(HellSwarmEOT(), source)


class HolyLight(Resolver):
    """Nonwhite creatures get -1/-1 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.event_mgr.register(HolyLightEOT(), source)


class HowlFromBeyond(Resolver):
    """Target creature gets +X/+0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is not None:
            x = source.extras.get('x', 0)  # read X chosen when casting
            target.modifiers.append(PTMod(s=source, p_adj=x, expires='EOT'))


class LesserWerewolf(Resolver):
    """If this creature's power is >= 1, it gets -1/-0 until EOT & put a -0/-1 counter on
    target creature blocking/blocked by this creature. Activate only during the declare blockers step."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if source.power < 1:
            return
        source.modifiers.append(PTMod(s=source, p_adj=-1, expires='EOT'))
        target.counters.add_counter(MINUS_ZERO_ONE)


class MarshGas(Resolver):
    """All creatures get -2/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.event_mgr.register(MarshGasEOT(), source)


class Morale(Resolver):
    """Attacking creatures get +1/+1 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.event_mgr.register(MoraleEOT(), source)


class FallingStar(Resolver):
    """Select an opponent's creature. If a di roll is 1-5, deal 3 damage to it"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        result: int = gs.randomize_event(s.owner_id, [1, 2, 3, 4, 5, 6])
        print(f'The roll is a: {result}')
        if result <= 5:
            gs.apply_damage(s, 3, t)


class Fasting(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        source.counters.add_counter(HUNGER)
        if source.counters.get_count(HUNGER) > 4:
            gs.pile_mgr.destroy(source)
        gs.action_stack.push(FastingChoice(source.owner_id, gs, source), gs, False)


class Feint(Resolver):
    """Tap all creatures blocking target attacking creature.
        Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it."""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        """target = the attacker"""
        the_combat = [com for com in gs.combat_mgr.combats if com.attacker == target]
        if not the_combat:
            return
        the_combat = the_combat[0]
        gs.event_mgr.register(PreventNextDamageByEOT(s, combat_only=True))
        for b in the_combat.blockers:
            gs.event_mgr.register(PreventNextDamageToCardEOT(b, combat_only=True))
            b.tap()


class FeldonsCane(Resolver):
    """{T}, Exile this artifact: Shuffle your graveyard into your library."""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        gy = gs.pile_mgr.graveyards[s.owner_id]
        lib = gs.pile_mgr.libraries[s.owner_id]
        lib.extend(gy)
        gy.clear()
        random.shuffle(lib)


class Festival(Resolver):
    """... Creatures can't attack this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.event_mgr.register(NoAttacksAllowedEOT(), source)


class FlashFlood(Resolver):
    """Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pile_mgr.bounce(t) if t.props.slug == 'mountain' else gs.pile_mgr.destroy(t)


class GoblinKing(Resolver):
    """All of your other Goblins gain +1+/+1 and Mountainwalk"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        targets = gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Goblin').result()
        for t in targets:
            if source != t:
                t.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Mountainwalk'))
                t.modifiers.append(PTMod(s=source, p_adj=1, t_adj=1))


class Greed(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, source.owner_id)
        gs.pile_mgr.draw(source.owner_id)


class GlyphOfDestruction(Resolver):
    """Target blocking Wall you control gets +10/+0 until end of combat.
    Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.append(PTMod(s=s, p_adj=10, expires='EOT'))
        gs.event_mgr.register(PreventAllDamageToEOT(t), s)
        gs.event_mgr.register(DestroyAtEndStep(t), s)


class HealingSalve(Resolver):
    """Choose one - * You gain 3 life. * Prevent the next 3 damage that would be dealt to any target this turn."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pending_choice = HealingSalveChoice(s.owner_id, gs, s)


class HurkylsRecall(Resolver):
    """Return all artifacts target player owns to their hand"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target player")
        for artifact in gs.card_filter.on_player_board(target).artifacts().result():
            gs.pile_mgr.bounce(artifact)


class Inquisition(Resolver):
    """Target player reveals their hand. Deal damage to that player = number of white cards in their hand."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target player")
        opp_cards = gs.pile_mgr.hands[flip(source.owner_id)].cards
        for c in opp_cards:
            c.reveal()
        if white_cnt := len([c for c in opp_cards if c.is_white]):
            gs.apply_damage(source, white_cnt, flip(source.owner_id))


class KoboldDrillSergeant(Resolver):
    """Other Kobold creatures you control get +0/+1 and have trample"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        kobolds = gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Kobold').result()
        for k in kobolds:
            if source != k:
                k.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Trample'))
                k.modifiers.append(PTMod(s=source, p_adj=0, t_adj=1))


class KryShield(Resolver):
    """Prevent all damage that would be dealt this turn by target creature you control.
    That creature gets +0/+X until end of turn, where X is its mana value"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.event_mgr.register(PreventNextDamageByEOT(t), s)
        t.modifiers.append(PTMod(s=s, t_adj=t.props.mana_value, expires='EOT'))


class LivingArtifactUpkeep(Resolver):
    """... At your upkeep, you may remove a vitality counter from this Aura to gain 1 life"""
    def resolve(self, gs: GameState, s: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(RemoveCounterForLifeChoice(s.owner_id, gs, s, VITALITY), gs, False)


class ManaClash(Resolver):
    """You and target opponent each flip a coin. Mana Clash deals 1 damage to each player whose coin comes up tails.
    Repeat this process until both players' coins come up heads on the same flip."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        caster_id, opp_id = source.owner_id, flip(source.owner_id)
        while True:
            caster_result = gs.randomize_event(caster_id, ['heads', 'tails'])
            opp_result = gs.randomize_event(opp_id, ['heads', 'tails'])
            print(f"Caster's result is {caster_result}; opponent's result is {opp_result}")
            if caster_result == 'heads' and opp_result == 'heads':
                print('Since both flips were heads, there are no more flips')
                break
            if caster_result == 'tails':
                gs.apply_damage(source, 1, caster_id)
            if opp_result == 'tails':
                gs.apply_damage(source, 1, opp_id)


class MartyrsCry(Resolver):
    """Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for white_creature in gs.card_filter.in_play().white().creatures().result():
            gs.pile_mgr.exile(white_creature)
            gs.pile_mgr.draw(white_creature.owner_id)


class MazeOfIth(Resolver):
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        the_combat = next((com for com in gs.combat_mgr.combats if com.attacker is t), None)
        if not the_combat:
            return
        gs.event_mgr.register(PreventNextDamageByEOT(the_combat.attacker, combat_only=True))
        for b in the_combat.blockers:
            gs.event_mgr.register(PreventNextDamageToCardEOT(b, combat_only=True))
        t.untap()


class NamelessRace(Resolver):
    """Upon ETB, pay any amount of life (max = # of white nontoken permanents your opponents control +
    the total number of white cards in their graveyards). NR's PT are each = life paid as it entered."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.action_stack.push(NamelessRaceChoice(source.owner_id, gs, source), gs, False)


class ManaShort(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose lands should be tapped"""
        if target is None:
            return
        player_lands = gs.card_filter.on_player_board(target).lands().result()
        for land in player_lands:
            land.tap()
        print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")


class Forcefield(Resolver):
    """(1): Next time an unblocked creature of your choice would deal you combat damage this turn, reduce damage to 1"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        from models.effects.listeners_damage import ForcefieldPrevention
        gs.event_mgr.register(ForcefieldPrevention(creature=t, protected_player=s.owner_id), s)
