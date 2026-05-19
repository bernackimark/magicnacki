"""
- Scryfall package calls the API to obtain MTG card data; saves data to card_data.json
- card_data.json is used to build Card (a read-only [I think] class) that feeds GameCard.props

- Tokens.json is manually built (Scryfall admits that they don't have old tokens from early MTG);
GameCard can be constructed from the data in tokens.json (as opposed to non-token from card_data.json)

- card_effect_specs.py is a map from card slug to a list of effects
- card_filter_funcs.py (used by card_effect_specs.py) is a convenience map shrinking the already-huge card-effect map

- kwa_abilities.py is legacy now because scraping the Gatherer website didn't provide structured KWAs (Scryfall does);
however, I'm still relying on some manually keywording to simplify engine code (Goad, Rampage X, Landhome, etc.)

- GameCard is the engine's object that represents any given MTG Card, it gets data from:
  - Card -> .props
  - card_effect_specs.py -> .effects
  - kwa_abilities.py -> .keyword_abilities

- (GameCard receives a back-reference to GameState (not sold on the approach, but it was a ChatGPT recommendation))

- card_filter.py filters a CardUniverse (a collection of Card objects); used in deck building
"""