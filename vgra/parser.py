import abc
from dataclasses import dataclass
from typing import Any, Generic, Iterable, Literal, TypeAlias, TypeVar

from vgra.args import Arg

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


class Parser(abc.ABC, Generic[TRet]):
    """Abstract base for both arg and value parsers"""

    @abc.abstractmethod
    def parse(self, tokens: list[str]) -> ParseResult_t[TRet]:
        """Parse a list of tokens

        Args:
            tokens (list[str]): The tokens list

        Returns:
            tuple[TRet, list[str]]: tuple(TRet, unparsed tokens)
        """
        ...

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
    def __init__(
        self, argd: list[Arg[Any]], value_parsers: Iterable["ValueParser[Any]"]
    ) -> None:
        super().__init__()
        self.argd = argd
        self.value_parsers = list(value_parsers)
        self.default_value_parser = DefaultValueParser()

    def resolve_value_parser(
        self, arg: Arg[TValueType] | None
    ) -> "ValueParser[TValueType]":
        if arg is None or arg.type == ...:
            return self.default_value_parser

        candidates = [
            p for p in self.value_parsers if issubclass(arg.type, p.value_type)
        ]

        if len(candidates) == 0:
            return self.default_value_parser

        return candidates[0]


class ValueParser(Parser[TValueType]):
    value_type: type[TValueType]

    @classmethod
    def __init_subclass__(cls, value_type: type[TValueType]) -> None:
        cls.value_type = value_type


class DefaultValueParser(ValueParser[Any], value_type=object):
    def parse(self, tokens: list[str]) -> ParseResult_t[object]:
        return tokens[0], tokens[1:]


class StandardArgParser(ArgParser):
    def __init__(
        self,
        argd: list[Arg[Any]],
        value_parsers: Iterable[ValueParser[Any]],
        prefix: str = "--",
    ) -> None:
        super().__init__(argd, value_parsers)
        self.prefix = prefix

    def get_kwarg(
        self, args: list[Arg[Any]], name: str
    ) -> tuple[Arg[Any] | None, list[Arg[Any]]]:
        arg: Arg[Any] | None = None
        for a in args:
            if a.name == name:
                arg = a
                break
        return arg, [a for a in args if a is not arg]

    def get_arg(self, args: list[Arg[Any]]) -> tuple[Arg[Any] | None, list[Arg[Any]]]:
        if len(args) == 0:
            return None, args
        if args[0].kind not in (ArgKind.POS, ArgKind.POSKW, ArgKind.VPOS):
            return None, args
        return args[0], args[1:]

    def parse_value(
        self, tokens: list[str], arg: Arg[Any] | None, mode: Literal["pos", "kw"]
    ) -> ParseResult_t[Any | None]:
        if len(tokens) == 0:
            "oops, we don't have any tokens left to parse"
            return None, tokens
        value_parser = self.resolve_value_parser(arg)
        value, tokens = value_parser.parse(tokens)

        return value, tokens

    def parse(self, tokens: list[str]) -> ParseResult_t[ParsedArgs_t]:
        argd: list[Arg[Any]] = [a for a in self.argd]
        args: list[Any] = []
        kwargs: dict[str, Any] = {}
        
        while len(tokens) > 0:
            if self.peek(tokens).startswith(self.prefix):
                "we have a named arg"
                t, tokens = self.next(tokens)
                t = t.removeprefix(self.prefix)
                arg, argd = self.get_kwarg(argd, t)
                value, tokens = self.parse_value(tokens, arg, "kw")
                kwargs[t] = (arg, value)
            else:
                "we have a positional arg"
                arg, argd = self.get_arg(argd)
                value, tokens = self.parse_value(tokens, arg, "pos")
                args.append((arg, value))
        return (args, kwargs), tokens
