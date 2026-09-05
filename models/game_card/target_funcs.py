from models.utils import flip

class ET:
    """Event -> Target.
    Target funcs that return a lambda accepting GameState, source: GameState, event: Event;
    returns a single target (int or GameCard)
    Currently used to convey target info from the event to the resolver via On.t()"""
    @staticmethod
    def attacker():
        return lambda gs, source, event: event.attacker

    @staticmethod
    def event_card():
        return lambda gs, source, event: event.card

    @staticmethod
    def event_card_owner():
        return lambda gs, source, event: event.card.owner_id

    @staticmethod
    def event_source_is_artifact():
        return lambda gs, source, event: event.source.is_artifact

    @staticmethod
    def host_owner():
        return lambda gs, source, event: source.host.owner_id

    @staticmethod
    def in_turn_p():
        return lambda gs, source, event: gs.turn_mgr.player_turn_idx

    @staticmethod
    def opp():
        return lambda gs, source, event: flip(source.owner_id)

    @staticmethod
    def s_owner():
        return lambda gs, source, event: source.owner_id
