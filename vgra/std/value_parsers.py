from typing import Any
from ..parser import ParseResult_t, ValueParser

class IntParser(ValueParser[int], value_type=int):
    def parse(self, tokens: list[str]) -> ParseResult_t[int]:
        return int(tokens[0]), tokens[1:]
    
class FloatParser(ValueParser[float], value_type=float):
    def parse(self, tokens: list[str]) -> ParseResult_t[float]:
        return float(tokens[0]), tokens[1:]
    
DEFAULT_PARSERS: list[ValueParser[Any]] = [
    IntParser(),
    FloatParser(),
]