import random
from copy import copy
from typing import Callable, Any, Sequence

from models.action_stack import ActionStack
from models.card import Card
from deck_builder.build_deck import Deck
from models.event_manager import EventManager
from models.game_card_filter import CardFilter
from models.actions.activate_ability import ActivateAbility, BeginAbilityActivationAction
from models.actions.base import Action
from models.actions.cast import CastToBoard, CastCounter, BeginSpellCastAction
from models.choice_actions_all import ChoiceAction
from models.actions.stack_accept_counter import AcceptAction
from models.damage import PreventNextDamage, DamageEvent, DamageReplacement
from models.destroy_replacements import RegenerationShield
from models.effects.base import Effect
from models.effects.base_rules_queries import CanAttackRule, CanBlockRule, CanCastRule, CanTargetRule, CanDamageRule
from models.events_all import (TapCardEvent, UntapCardEvent, DamageResolvedEvent, StateBasedEvent, CastResolvedEvent,
                               DiesEvent, ZoneChangeEvent, DrawCardEvent, LifeLossEvent,
                               RandomEvent, Event, DiscardEvent)
from models.game_card import GameCard
from models.combat import Combat
from models.game_history import GameHistory
from models.hand import Hand
from models.mana import ManaPool
from models.mulligan import MulliganChoice
from models.score_manager import ScoreManager
from models.state_based_rules import StateBasedRule, STATE_BASED_RULES
from models.turn import Turn
from models.zone import Zone
from phase_fsm import Phase, PhaseManager
from models.utils import flip


class GameState:
    """All-knowing class responsible for everything after a new game is created;
    registers effects, emits events, runs queries;
    stores card piles & moves cards; contains stack & pending choice"""
    def __init__(self, player_cnt: int, player_turn_idx: int, rules: dict, decks: list[Deck]):
        # assign all arguments to attributes
        self.player_cnt = player_cnt
        self.player_turn_idx = player_turn_idx
        self.rules: dict = rules
        self.decks_all_cards = decks.copy()
        self.libraries = decks.copy()
        # give GameCard a reference to GameState (a ChatGPT suggestion, not sold on that design choice)
        for d in self.libraries:
            for c in d.cards:
                c.game_state = self
        # game over conditions
        self.score_mgr = ScoreManager()
        # self.life = [20, 20]
        # self._poison_counters = [0, 0]
        # action, turn, phase (game flow) concepts; not sure self.turn is being used
        self.action_on_idx: int = self.player_turn_idx
        self.turn = Turn(self.player_turn_idx, flip(self.player_turn_idx))
        self.turn_number = 1
        self.phase_mgr = PhaseManager(Phase.NEW_GAME)
        # piles, combats, mana pools
        self.boards: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.graveyards: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.exiles: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.hands: list[Hand] = [Hand(sort_pref=Hand.SortOrient.L_TO_R) for _ in range(self.player_cnt)]
        self.combats: list[Combat] = []
        self.mana_pools: list[ManaPool] = [ManaPool(self, i) for i in range(self.player_cnt)]

        self.action_stack = ActionStack()

        self.game_history = GameHistory()  # turn num, p_idx, Action; appended to in engine.play()

        self.card_filter = CardFilter(self)
        # only has knowledge of the current game; match info is handled in Engine's MatchManager
        self.is_game_over: bool = False
        self.winner: int | None = None

        self.query_effects: list[Effect] = [CanAttackRule(), CanBlockRule(), CanCastRule(),
                                            CanDamageRule(), CanTargetRule()]
        self.until_eot_effects_and_cards: list[tuple[Effect, GameCard]] = []
        self.state_based_rules: tuple[type[StateBasedRule]] = STATE_BASED_RULES

        self.destroy_replacements: list[RegenerationShield] = []
        self.damage_replacements: list[DamageReplacement] = []
        self.damage_preventions: list[PreventNextDamage] = []
        self.end_step_funcs: list[Callable] = []
        self.cards_that_died_this_turn: list[GameCard] = []

        # emits, registers, unregisters Effect that implement on_event()
        self.event_mgr = EventManager()

        for i in range(self.player_cnt):
            random.shuffle(self.libraries[i].cards)
            self.draw(i, 7)

        # used for forced actions that do not go onto the stack (ex: it's resolved that you must discard, select one)
        self.pending_choice: ChoiceAction | None = MulliganChoice(self.player_turn_idx, self, self.rules['mulligan'])

    def register_effect_until_eot(self, eff_and_card: tuple[Effect, GameCard]):
        """When GameCards look if they are effected by something, they check the cards in play;
        however, some card effects (such as instants cast & placed in graveyard) last throughout the turn"""
        self.until_eot_effects_and_cards.append(eff_and_card)

    def check_state_based_actions(self):
        """state_based_rules are invariant; they must repeat until stable; there is no player choice, no stack, etc.;
        (ex: creatures w 0 toughness or unattached auras must die, etc.)"""
        while True:
            changed = False
            for rule in self.state_based_rules:
                if rule.apply(self):
                    changed = True
            if not changed:
                break

    # --- QUERY SYSTEM ---
    def can_attack(self, card: GameCard) -> bool:
        return self._query_effects_by_event('can_attack', card)

    def can_block(self, blocker: GameCard, attacker: GameCard):
        return self._query_effects_by_event('can_block', blocker, attacker=attacker)

    def can_damage(self, target: GameCard, source: GameCard):
        return self._query_effects_by_event('can_damage', target, source=source)

    def can_target(self, target: GameCard | int, source: GameCard):
        if isinstance(target, int):
            return True
        result = self._query_effects_by_event('can_target', target, source=source)
        return False if result is False else True

    def can_untap(self, card: GameCard) -> bool:
        return self._query_effects_by_event('can_untap', card)

    def can_cast(self, card: GameCard, p_id: int) -> bool:
        return self._query_effects_by_event('can_cast', card, p_id=p_id)

    def can_be_destroyed(self, card: GameCard) -> bool:
        result = self._query_effects_by_event('can_be_destroyed', card)
        return False if result is False else True

    def _query_effects_by_event(self, event_str: str, card: GameCard, **kwargs) -> bool:
        """Ask all query-style effects (base, card, and until_eots) if they have an opinion;
        can be True (which is either hard permission or the lack of a hard-veto) or False (a hard veto);
        hard permission takes precedence over hard veto;
        hard permission ex: undertow & islandwalkers can be blocked;
        hard veto ex: meekstone preventing some untaps"""
        effects = (self.query_effects +
                   [a.effect for c in self.card_filter.in_play().result()
                    for a in c.static_abilities + c.triggered_abilities] +
                   [eff for eff, _ in self.until_eot_effects_and_cards])

        explicit_forbids = False
        for eff in effects:
            if not hasattr(eff, 'on_query'):
                continue

            result = eff.on_query(self, event_str, card=card, **kwargs)

            if result is True:
                return True
            if result is False:
                explicit_forbids = True
        return False if explicit_forbids else True

    # Pile Helpers & card movement
    @property
    def all_cards(self) -> list[GameCard]:
        """Returns all cards, including tokens"""
        return ([c for b in self.libraries for c in b.cards] + [c for h in self.hands for c in h.cards] +
                [c for g in self.graveyards for c in g] + [c for e in self.exiles for c in e] +
                [c for b in self.boards for c in b])

    # --- DAMAGE ---
    def apply_damage(self, source: GameCard | None, amount: int, target: GameCard | int, is_combat: bool = False):
        """Creates DamageEvent, triggers damage preventions, adds .combat_damage_received to card,
        decrements life to player, handles Trample combat damage"""
        event = DamageEvent(source, amount, target, is_combat)

        # 1. Give all effects a chance to prevent/redirect
        self.trigger_damage_prevention(event)

        # 2. Apply remaining damage
        if event.remaining <= 0:
            return

        resolved_events: list[DamageResolvedEvent] = []

        # 3. Apply damage
        if is_combat and source and 'Trample' in source.keyword_abilities and isinstance(target, GameCard):
            damage_to_card = min(target.toughness, event.remaining)
            target.damage_received_this_turn += damage_to_card
            resolved_events.append(DamageResolvedEvent(source, damage_to_card, target, True))

            damage_to_player = event.remaining - damage_to_card
            if damage_to_player > 0:
                self.score_mgr.decrement_life(target.owner_id, damage_to_player, source, self)
                resolved_events.append(DamageResolvedEvent(source, damage_to_player, target.owner_id, True))
        else:
            if isinstance(target, GameCard):
                target.damage_received_this_turn += event.remaining
            else:
                self.score_mgr.decrement_life(target, event.remaining, source, self)

            resolved_events.append(DamageResolvedEvent(source, event.remaining, target, is_combat))

        # 4. Emit resolved events
        for e in resolved_events:
            self.event_mgr.emit(e, self)
            self.check_state_based_actions()  # checks if damage_received_this_turn >= creature.toughness

    def trigger_damage_prevention(self, event: DamageEvent):
        # Replacement effects (statics + globals)
        for r in list(self.damage_replacements):
            if r.applies(self, event):
                r.replace(self, event)

        # One-shot prevention shields (ex: fog, COPs)
        for p in list(self.damage_preventions):
            if event.remaining <= 0:
                break
            prevented = p.apply(event)
            event.prevented += prevented
            if p.remaining == 0:
                self.damage_preventions.remove(p)

    # --- CARD MOVEMENT ---
    def move_card(self, card: GameCard, to_zone: Zone, *, cause: str | None = None, emit_zone_event: bool = True):
        if card.zone == to_zone:
            return

        from_zone = copy(card.zone)

        # Unregister effects, remove all mods if leaving battlefield
        if card.zone == Zone.BATTLEFIELD:
            self._leave_battlefield(card, to_zone)

        self._remove_from_zone(card, card.zone)
        self._add_to_zone(card, to_zone)
        card.zone = to_zone
        if emit_zone_event:
            self.event_mgr.emit(ZoneChangeEvent(card, from_zone, to_zone, cause), self)

        # Post-move hooks
        # self._after_zone_change(card, from_zone, to_zone)

    def destroy(self, card: GameCard, allow_regeneration: bool = True):
        # ask replacement system if destruction is prevented
        # as of now, this destruction replacement & damage are handled separately but could be unified later
        if allow_regeneration:
            for shield in list(self.destroy_replacements):
                if shield.applies_to(card):
                    shield.apply(self, card)
                    self.destroy_replacements.remove(shield)
                    return

        self.event_mgr.emit(DiesEvent(card), self)
        self.move_card(card, Zone.GRAVEYARD, cause="destroy")
        self.cards_that_died_this_turn.append(card)
        print(f'{card} is destroyed')
        self.game_history.append_non_action(self, card=card, text=f'{card} is destroyed')

    def exile(self, card: GameCard):
        self.move_card(card, Zone.EXILE, cause="exile")
        print(f'{card} is exiled')
        self.game_history.append_non_action(self, card=card, text=f'{card} is exiled')

    def bounce(self, card: GameCard):
        self.move_card(card, Zone.HAND, cause="bounce")
        print(f'{card} is bounced')
        self.game_history.append_non_action(self, card=card, text=f'{card} is bounced')

    def discard(self, card: GameCard, source: GameCard | None = None):
        self.event_mgr.emit(DiscardEvent(card.orig_owner_id, card, source), self)
        self.move_card(card, Zone.GRAVEYARD, cause="discard")
        print(f'{card} is discarded')
        self.game_history.append_non_action(self, card=card, text=f'{card} is bounced')

    def reanimate(self, card: GameCard):
        self.move_card(card, Zone.BATTLEFIELD, cause='reanimate')
        print(f'{card} is reanimated')
        self.game_history.append_non_action(self, card=card, text=f'{card} is renimated')

    def cast(self, card: GameCard):
        self.move_card(card, Zone.BATTLEFIELD, cause='cast')
        print(f'{card} is cast')
        self.game_history.append_non_action(self, card=card, text=f'{card} is cast')

    def draw(self, p_id: int, cnt: int = 1):
        for _ in range(cnt):
            self.move_card(self.libraries[p_id].cards[0], Zone.HAND, cause='draw')
            self.event_mgr.emit(DrawCardEvent(p_id), self)
            print(f'Player #{p_id} draws')
            self.game_history.append_non_action(self, text=f'Player #{p_id} draws')

    def _add_to_zone(self, card: GameCard, zone: Zone):
        if card.is_token and zone != Zone.BATTLEFIELD:
            return
        match zone:
            case Zone.BATTLEFIELD:
                self.boards[card.owner_id].append(card)
            case Zone.HAND:
                self.hands[card.orig_owner_id].cards.append(card)
                self.hands[card.orig_owner_id].sort_cards()
            case Zone.GRAVEYARD:
                self.graveyards[card.orig_owner_id].append(card)
            case Zone.EXILE:
                self.exiles[card.orig_owner_id].append(card)
            case Zone.LIBRARY:
                self.libraries[card.orig_owner_id].cards.insert(0, card)

    def _remove_from_zone(self, card: GameCard, zone: Zone):
        match zone:
            case Zone.BATTLEFIELD:
                self.boards[card.owner_id].remove(card)
                if card.is_tapped:
                    card.is_tapped = False
            case Zone.HAND:
                self.hands[card.orig_owner_id].cards.remove(card)
                self.hands[card.orig_owner_id].sort_cards()
            case Zone.GRAVEYARD:
                self.graveyards[card.owner_id].remove(card)
            case Zone.EXILE:
                self.exiles[card.owner_id].remove(card)
            case Zone.LIBRARY:
                self.libraries[card.owner_id].cards.remove(card)

    def _leave_battlefield(self, card: GameCard, to_zone: Zone):
        """Emit ZoneChangeEvent before unregistering its effects, doing so for the subject card;
        detach all attached GameCard auras; call GameCard.clear_all_mods()"""
        self.event_mgr.emit(ZoneChangeEvent(card, card.zone, to_zone, cause='leave'), self)
        self.event_mgr.unregister_effects(card)
        for aura in list(card.modifiers.auras):
            if isinstance(aura, GameCard):
                self.event_mgr.emit(ZoneChangeEvent(aura, aura.zone, Zone.GRAVEYARD, cause='detach_aura'), self)
                self.move_card(aura, Zone.GRAVEYARD, cause='detach_aura')
                self.event_mgr.unregister_effects(aura)
        card.clear_all_mods()
        self.event_mgr.emit(StateBasedEvent(), self)

    def create_token_creature(self, owner_id: int, name: str, power: int, toughness: int, kwa: list[str],
                              other_types: list[str], sub_types: list[str], colors: str):
        # TODO: all possible tokens seem knowable; why not just treat like normal cards but for an is_token indicator?
        #  creation of Card could be handled pre-game; all that left is GameCard creation
        card = Card(slug=name.replace(' ', '-').lower(),
                    name=name, casting_cost='', card_types=['Creature'] + other_types,
                    card_sub_types=sub_types,
                    card_super_types=[], rarity='', rules_text='', oracle_rules_text='',
                    power=power, toughness=toughness, set_codes=[], data_url='', images={'1E': ''}, rulings=[],
                    keyword_abilities=kwa)
        game_card = GameCard(card, owner_id, is_token=True, colors=colors)
        game_card.zone = Zone.BATTLEFIELD
        game_card.game_state = self
        self.boards[owner_id].append(game_card)

    @staticmethod
    def randomize_event(p_id: int, sequence: Sequence[Any]) -> Any:
        """Creates an event, but doesn't raise it (not sure why not); selects a random choice from the sequence"""
        event = RandomEvent(p_id, sequence)
        event.result = random.choice(sequence)
        return event.result

    def remove_from_combat(self, c: GameCard):
        """If attacker, delete that combat object, untap attacker; if blocker, remove blocker from the combat object"""
        for com in self.combats:
            if com.attacker is c:
                self.untap_card(com.attacker)
                self.combats.remove(com)
                return
            for blocker in com.blockers:
                if blocker is c:
                    com.blockers.remove(blocker)
                    return

    def tap_card(self, c: GameCard):
        """If card is already tapped, skip; emit TapCardEvent, tap card, tap all attached auras"""
        if c.is_tapped:
            return
        self.event_mgr.emit(TapCardEvent(card=c), self)
        c.is_tapped = True
        for a in c.modifiers.auras:
            a.is_tapped = True

    def untap_card(self, c: GameCard):
        """If card is already untapped, skip; emit UntapCardEvent, tap card, tap all attached auras"""
        if not c.is_tapped:
            return
        self.event_mgr.emit(UntapCardEvent(card=c), self)
        c.is_tapped = False
        for a in c.modifiers.auras:
            a.is_tapped = False

    def handle_untap_phase(self):
        """Untap all cards on in-turn player's board; remove summoning sickness;
        if a card has an optional untap, check if player has already decided to leave a card tapped"""
        for c in self.boards[self.player_turn_idx]:

            for record in self.game_history.items:
                if record.get('type') == 'CastToBoard' and record.get('card_id') == c.id_ and self.turn_number - record['turn_num'] == 2:
                    c.has_summoning_sickness = False
            if not c.is_tapped:
                continue

            for record in self.game_history.items:
                if record['turn_num'] == self.turn_number and (record.get('type') == 'UntapCardStackPop' or record.get('type') == 'LeaveTapped') and record.get('card_id') == c.id_:
                    print("You've already made an untap decision on this card this turn")
                    break
            else:
                if self.can_untap(c):
                    self.event_mgr.emit(UntapCardEvent(c), self)
                    self.untap_card(c)

    def get_available_activated_abilities(self, c: GameCard) -> list[ActivateAbility]:
        actions: list[ActivateAbility | BeginAbilityActivationAction] = []

        for ability in c.activated_abilities:
            spec = ability.eff_spec

            if not ability.can_activate(self):
                continue
            if spec.extra_costs and any(not cost.can_pay(self, c) for cost in spec.extra_costs):
                continue
            if c.has_summoning_sickness:
                continue

            # Determine potential targets
            target_spec = ability.eff_spec.target_spec

            # TODO: THIS IF CHAIN ARE WRONG
            #  EX: mana battery has no target_spec but does have a max_x_func and must enter BeginAbilityActivation ...

            if (target_spec and target_spec.min_cnt > 1) or ability.eff_spec.max_x_func:
                actions.append(BeginAbilityActivationAction(self.action_on_idx, self, ability))
                continue

            if not target_spec:
                actions.append(ActivateAbility(self.action_on_idx, self, ability, target=None))
                continue

            targets = target_spec.filter_func(self, c)
            # convert to list
            targets = [targets] if not isinstance(targets, (list, tuple)) else targets
            # remove illegal targets
            targets = [t for t in targets if self.can_target(t, c)]
            if len(targets) < target_spec.min_cnt:
                # Not enough legal targets → skip ability entirely
                continue

            actions.append(ActivateAbility(self.action_on_idx, self, ability, target=targets))

        return actions

    def add_activated_abilities_from_board(self) -> list[ActivateAbility] | list[None]:
        actions: list[ActivateAbility] = []
        for card in self.boards[self.action_on_idx]:
            actions.extend(self.get_available_activated_abilities(card))
            for aura in card.modifiers.auras:
                if not isinstance(aura, GameCard):  # some auras can be KWAModifier/PTModifiers (this is confusing)
                    continue
                actions.extend(self.get_available_activated_abilities(aura))
        return actions

    def available_actions_from_hand(self) -> list[Action]:
        actions: list[Action] = []
        p_id = self.action_on_idx

        for c in self.hands[self.action_on_idx].cards:
            if not self.can_cast(c, p_id):
                continue

            # Short-cutting these directly to the board for testing expedience
            if c.props.is_permanent and not c.props.is_aura:
                actions.append(CastToBoard(p_id, self, c))
                continue

            # Gather triggered abilities tied to casting
            cast_eff_specs = [e for e in c.triggered_abilities
                              if e.activation_type == 'triggered' and e.trigger_event is CastResolvedEvent]

            if not cast_eff_specs:
                actions.append(BeginSpellCastAction(p_id, self, c, eff_spec=None))
                continue

            # --- For each cast-triggered spec
            for eff_spec in cast_eff_specs:
                if 'X' in c.casting_cost and self.mana_pools[p_id].get_max_x(c.casting_cost) < eff_spec.min_x:
                    continue

                if eff_spec.target_spec and eff_spec.target_spec.filter_func:
                    candidates = eff_spec.target_spec.filter_func(self, c)
                    valid_targets = [t for t in candidates if self.can_target(t, c)]

                    if len(valid_targets) < eff_spec.target_spec.min_cnt:
                        continue

                actions.append(BeginSpellCastAction(p_id, self, c, eff_spec=eff_spec))

        return list({repr(x): x for x in actions}.values())  # Deduplicate by repr

    def get_available_actions(self, p_id: int) -> list[Action] | None:
        """This method is called by the engine; in order, check for:
            -   Pending Choice (selections that are forced & are not placed on stack)
            -   Check global state-based actions (game over, creatures w 0 weakness die, etc.)
                -   If game is over, ask player to sideboard
            -   Check the stack
            -   Get actions by phase"""

        if self.pending_choice:
            return self.pending_choice.get_actions()

        self.check_state_based_actions()

        # TODO: when the game ends, it just hangs, GameOverChoice is never presented
        #  PyGame just hangs at game over as well

        # TODO: if the match is over, it shouldn't go here but GameState has no knowledge of the match
        if self.is_game_over:
            print('YYY')
            if not self.pending_choice:
                from models.game_over import GameOverChoice
                self.pending_choice = GameOverChoice(p_id, self)
            return self.pending_choice.get_actions()

        # if there is something on the stack, respond & resolve, don't seek out other available actions
        if len(self.action_stack):
            available_actions: list[Action] = []
            hand = self.hands[p_id]
            if isinstance(self.action_stack.last_action, ChoiceAction):
                return self.action_stack.last_action.get_actions()

            available_actions.append(AcceptAction(p_id, self))

            # Check instants (or other spells allowed to respond)
            allowed_cards = hand.instants + hand.sorceries if p_id == self.player_turn_idx else hand.sorceries
            playable_cards: list[GameCard] = [c for c in allowed_cards if self.mana_pools[p_id].can_pay(c.casting_cost)]

            for c in playable_cards:
                # Handle counterspells separately; not thought through yet
                if c.props.slug in ('counterspell',):
                    target: Action = self.action_stack.last_action
                    available_actions.append(CastCounter(p_id, self, c, target))
                    continue

                # Handle other spells
                available_actions.extend(self.available_actions_from_hand())

                # Activated abilities can also respond
                available_actions.extend(self.add_activated_abilities_from_board())

            return available_actions

        # delegating to phase manager
        return self.phase_mgr.get_actions(p_id, self)


# TODO:
#  - When deciding which mana to tap, as a strategy, tap colorless mana where possible

# TODO:
#  Build a CardUniverseFilter (modeled after CardFilter)
#  - helpful when I'm trying to figure out what are good cards to test
#  - would be helpful to the User when Building a Deck

# TODO:
#  can_cast() must take into account multi-mana-color producers (dual lands, etc)

# TODO:
#  Black Knight (2/2) is killing Northern Palladin (3/3)
#  also, dealing one damage to a creature w a higher toughness is also killing it

# TODO:
#  Global Legendary Rule, only one legendary slug-board pair allowed

# TODO: currently, Destroy() is being placed on the stack, but there is no option to respond to that, only 'Accept'
# ChatGPT is saying this:
#   while True:
#     player = self.current_priority_player()
#
#     action = player.choose_action()
#
#     if action:
#         self.action_stack.push(action)
#         continue
#
#     self.mark_player_passed(player)
#
#     if both_players_passed():
#         resolve_top_of_stack()
#         reset_passes()
# Without this, regeneration can never be used correctly.
