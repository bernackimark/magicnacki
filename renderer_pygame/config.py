import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CARD_DATA_FILE_PATH = Path(os.getenv('CARD_DATA_FILE_PATH'))
IMAGES_OUTPUT_PATH = Path(os.getenv('IMAGES_OUTPUT_PATH'))

COLORS_W_COLORLESS = ('R', 'G', 'U', 'B', 'W', 'C')
COLOR_NAMES = ('brown3', 'darkgreen', 'royalblue1', 'gray23', 'lemonchiffon', 'burlywood4')

COLOR_DICT = {letter: name for letter, name in zip(COLORS_W_COLORLESS, COLOR_NAMES)}
