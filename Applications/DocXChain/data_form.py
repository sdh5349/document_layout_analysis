from dataclasses import dataclass


@dataclass
class TextInfo:
    text: str
    bbox: BBox

@dataclass
class BBox:
    x0: int
    y0: int
    x1: int
    y1: int
