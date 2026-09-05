

class AmtF:
    """Collection of static methods that return a lambda GameState, GameCard, Target: int"""
    @staticmethod
    def t_mv():
        return lambda gs, s, t: t.props.mana_value

