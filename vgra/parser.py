import abc
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    Iterable,
    Literal,
    TypeAlias,
    TypeVar,
    get_args,
    get_origin,
)

from .args import Arg, ArgKind

TValueType = TypeVar("TValueType")
TRet = TypeVar("TRet")

ParseResult_t: TypeAlias = tuple[TRet, list[str]]


class ParseError(Exception):
    """Raise an input error during parsing"""


@dataclass
class ArgMissingError(ParseError):
    """Raise an argument missing error"""

    arg: Arg[Any]

    def __str__(self) -> str:
        return f"Missing argument '{self.arg.name}'"


@dataclass
class ArgUnexpectedPosError(ParseError):
    """Raise an argument unexpected pos error"""

    pos: int

    def __str__(self) -> str:
        return f"Unexpected argument at position '{self.pos}'"


@dataclass
class ArgUnexpectedKwError(ParseError):
    """Raise an argument unexpected kw error"""

    kw: str

    def __str__(self) -> str:
        return f"Unexpected argument with name '{self.kw}'"


@dataclass
class ArgSyntaxError(ParseError):
    """Raise an argument syntax error"""

    received: str
    expected: str

    def __str__(self) -> str:
        return (
            f"Syntax error received: '{self.received}' but expected '{self.expected}'"
        )


class Parser(abc.ABC, Generic[TRet]):
    """Abstract base for both arg and value parsers"""

    def next(self, tokens: list[str]) -> ParseResult_t[str]:
        """Consume a token from the args list.

        Args:
            args (list[str]): The tokens list

        Returns:
            ParseResult_t[str]: tuple(next token, tokens tail)
        """
        return tokens[0], tokens[1:]

    def peek(self, tokens: list[str]) -> str:
        """Peek at the next token

        Args:
            args (list[str]): The tokens list

        Returns:
            str: next token
        """
        return tokens[0]


ParsedArg_t = tuple[Arg[Any] | None, Any]
ParsedArgs_t = tuple[list[ParsedArg_t], dict[str, ParsedArg_t]]


class ArgParser(Parser[ParsedArgs_t]):
    def __init__(self, value_parsers: Iterable["ValueParser[Any]"]) -> None:
        super().__init__()
        self.value_parsers = list(value_parsers)
        self.default_value_parser = DefaultValueParser()

    def resolve_value_parser(
        self, arg: Arg[TValueType] | None
    ) -> "ValueParser[TValueType]":
        if arg is None:
            return self.default_value_parser

        assert arg.type is not ...  # why do I need this to satisfy mypy?
        if get_origin(arg.type) == Literal:
            targs = get_args(arg.type)
            t = type(targs[0])
            if not all([type(ta) == t for ta in targs]):
                raise TypeError(f"Multi-type Literals are not supported: {arg.type}")
        else:
            t = arg.type

        candidates = [p for p in self.value_parsers if issubclass(t, p.value_type)]

        if len(candidates) == 0:
            return self.default_value_parser

        return candidates[0]

    def get_kwarg(
        self, args: list[Arg[Any]], name: str
    ) -> tuple[Arg[Any] | None, list[Arg[Any]]]:
        arg: Arg[Any] | None = None
        for a in args:
            if name in a.names:
                arg = a
                break
        return arg, [a for a in args if a is not arg]

    def get_arg(self, args: list[Arg[Any]]) -> tuple[Arg[Any] | None, list[Arg[Any]]]:
        if len(args) == 0:
            return None, args
        if args[0].kind not in (ArgKind.POS, ArgKind.POSKW, ArgKind.VPOS):
            return None, args
        return args[0], args[1:]

    @abc.abstractmethod
    def parse(
        self, tokens: list[str], argd: list[Arg[Any]]
    ) -> ParseResult_t[ParsedArgs_t]:
        """Parse a list of tokens

        Args:
            tokens (list[str]): The tokens list
            argd (list[Arg[Any]]): The arguments

        Returns:
            tuple[ParsedArgs_t, list[str]]: tuple(ParsedArgs_t, unparsed tokens)
        """
        ...


class ValueParser(Parser[TValueType]):
    value_type: type[TValueType]

    @classmethod
    def __init_subclass__(cls, value_type: type[TValueType]) -> None:
        cls.value_type = value_type

    @abc.abstractmethod
    def parse(self, tokens: list[str]) -> ParseResult_t[TValueType]:
        """Parse value from a token

        Args:
            tokens (list[str]): The tokens list

        Returns:
            ParseResult_t[TValueType]: The parsed value
        """
        ...


class DefaultValueParser(ValueParser[Any], value_type=object):
    def parse(self, tokens: list[str]) -> ParseResult_t[object]:
        return tokens[0], tokens[1:]



