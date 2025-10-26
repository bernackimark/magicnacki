from dataclasses import dataclass, field, InitVar
from typing import Any, Self

import pygame as pg

@dataclass
class Font:
    name: str
    size: int
    bold: bool = False
    italic: bool = False

    def __call__(self, *args, **kwargs):
        return pg.font.SysFont(self.name, self.size, self.bold, self.italic)


@dataclass
class Table:
    surface: pg.Surface
    x: int
    y: int
    header_height: int
    row_height: int
    header_font: pg.Font
    row_font: pg.Font
    column_widths: list[int]
    header_names: list[str]
    rows: list[list[str]] = field(default_factory=list)
    items_to_blit: list = field(default_factory=list)

    def __post_init__(self):
        if len(self.column_widths) != len(self.header_names):
            raise ValueError("There must be the same number of column widths as header names; "
                             "use None where you don't want to have a column header")

        # Build header items and keep a copy, so we can restore it when clearing rows
        self._header_items = []
        x_pos = self.x
        for header, col_width in zip(self.header_names, self.column_widths):
            text = self.header_font.render(header, True, (255, 255, 255))
            self._header_items.append((text, (x_pos, self.y + 30)))
            x_pos += col_width

        self.items_to_blit = list(self._header_items)

    @property
    def row_cnt(self) -> int:
        return len(self.rows)

    @property
    def table_rect(self) -> pg.Rect:
        table_width = sum(self.column_widths)
        table_height = self.header_height + (self.row_height * self.row_cnt) + 60
        return pg.Rect(self.x, self.y, table_width, table_height)

    def clear_rows(self) -> None:
        self.rows.clear()
        self.items_to_blit = list(self._header_items)

    def add_row(self, values: list[str]) -> None:
        if len(values) != len(self.header_names):
            raise ValueError("There must be the same number of values as header names; "
                             "use None where you don't want to have a value")
        self.rows.append(values)
        x_pos = self.x
        y_pos = self.y + self.header_height + (self.row_cnt * self.row_height)
        for i, v in enumerate(values):
            text = self.row_font.render(v, True, (255, 255, 255))
            self.items_to_blit.append((text, (x_pos, y_pos + 30)))
            x_pos += self.column_widths[i]
