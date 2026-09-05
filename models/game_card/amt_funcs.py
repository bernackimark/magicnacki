

class AmtF:
    """Collection of static methods that return a lambda GameState, GameCard, Target: int"""
    @staticmethod
    def t_hand_size(offset: int):
        return lambda gs, s, t: len(gs.pile_mgr.hands[t]) + offset

    @staticmethod
    def t_mv():
        return lambda gs, s, t: t.props.mana_value

    @staticmethod
    def t_swamp_cnt():
        return lambda gs, s, t: len(gs.card_filter.on_player_board(t).swamps().result())
