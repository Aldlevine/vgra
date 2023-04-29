from typing import Any

from ..parser import ParseError, ParseResult_t, ValueParser


class IntParser(ValueParser[int], value_type=int):
    def parse(self, tokens: list[str]) -> ParseResult_t[int]:
        try:
            t, tokens = self.next(tokens)
            base: int = 10
            if t.startswith("0x"):
                base = 16
            elif t.startswith("0o"):
                base = 8
            elif t.startswith("0b"):
                base = 2
            return int(t, base), tokens
        except ValueError as e:
            raise ParseError(str(e))


class FloatParser(ValueParser[float], value_type=float):
    def parse(self, tokens: list[str]) -> ParseResult_t[float]:
        try:
            return float(tokens[0]), tokens[1:]
        except ValueError as e:
            raise ParseError(str(e))


DEFAULT_VALUE_PARSERS: list[ValueParser[Any]] = [
    IntParser(),
    FloatParser(),
]
