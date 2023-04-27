import abc
import re
from dataclasses import dataclass
from typing import Any, Generic, Iterable, TypeAlias, TypeVar

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
        if arg is None or arg.type == ...:
            return self.default_value_parser

        assert arg.type is not ...  # why do I need this to satisfy mypy?
        candidates = [
            p for p in self.value_parsers if issubclass(arg.type, p.value_type)
        ]

        if len(candidates) == 0:
            return self.default_value_parser

        return candidates[0]

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


class PythonicArgParser(ArgParser):
    def __init__(
        self,
        value_parsers: Iterable[ValueParser[Any]],
        kw_eq_char: str = "=",
        flag_char: str = "-",
        list_chars: tuple[str, str] | None = ("[", "]"),
        dict_chars: tuple[str, str, str] | None = ("{", ":", "}"),
    ) -> None:
        super().__init__(value_parsers)

        self._kw_eq_char = kw_eq_char
        self._flag_char = flag_char
        self._list_chars = list_chars
        self._dict_chars = dict_chars

        ident = r"[a-zA-Z_]+[a-zA-Z0-9_]*"

        self._kw_split_re = re.compile(rf"^({ident}){kw_eq_char}(.*)$")
        if dict_chars is not None:
            self._dict_kw_split_re = re.compile(rf"^({ident}){dict_chars[1]}(.*)$")

    def split_kw_val(self, token: str) -> tuple[str | None, str | None]:
        if self._kw_split_re.match(token):
            kv = [str(s) for s in self._kw_split_re.split(token) if len(s) > 0]
            if len(kv) == 1:
                kw, val = kv[0], None
            else:
                kw, val = kv
            return kw, val
        else:
            return None, token

    def split_dict_kw_val(self, token: str) -> tuple[str | None, str | None]:
        if self._dict_kw_split_re.match(token):
            kv = [str(s) for s in self._dict_kw_split_re.split(token) if len(s) > 0]
            if len(kv) == 1:
                kw, val = kv[0], None
            else:
                kw, val = kv
            return kw, val
        else:
            return None, token

    def is_list_end(self, t: str) -> bool:
        return self._list_chars is not None and t == self._list_chars[-1]

    def is_dict_end(self, t: str) -> bool:
        return self._dict_chars is not None and t == self._dict_chars[-1]

    def is_container_end(self, t: str) -> bool:
        return self.is_list_end(t) or self.is_dict_end(t)

    def split_container_ends(self, t: str, tokens: list[str]) -> ParseResult_t[str]:
        while (self._list_chars is not None and t.endswith(self._list_chars[-1])) or (
            self._dict_chars is not None and t.endswith(self._dict_chars[-1])
        ):
            if self._list_chars is not None and t.endswith(self._list_chars[-1]):
                t = t.removesuffix(self._list_chars[-1])
                tokens.insert(0, self._list_chars[-1])
            else:
                assert self._dict_chars is not None
                t = t.removesuffix(self._dict_chars[-1])
                tokens.insert(0, self._dict_chars[-1])
        return t, tokens

    def parse_list(self, tokens: list[str], arg: Arg[Any] | None) -> ParseResult_t[Any]:
        l: list[Any] = []
        while len(tokens) > 0:
            t, tokens = self.next(tokens)
            # if self.is_container_end(t):
            #     break
            if self.is_dict_end(t):
                assert self._list_chars is not None
                raise ArgSyntaxError(t, f"value or {self._list_chars[-1]}")
            if self.is_list_end(t):
                break

            t, tokens = self.split_container_ends(t, tokens)
            tokens.insert(0, t)

            v, tokens = self.parse_value(tokens, arg)
            # if len(v) > 0:
            l.append(v)

        return l, tokens

    def parse_dict(self, tokens: list[str], arg: Arg[Any] | None) -> ParseResult_t[Any]:
        d: dict[str, Any] = {}
        while len(tokens) > 0:
            t, tokens = self.next(tokens)
            # if self.is_container_end(t):
            #     break
            if self.is_list_end(t):
                assert self._dict_chars is not None
                raise ArgSyntaxError(t, f"key:value or {self._dict_chars[-1]}")
            if self.is_dict_end(t):
                break

            t, tokens = self.split_container_ends(t, tokens)

            "Now we have k:v ...}"
            k, vs = self.split_dict_kw_val(t)
            if k == None or vs == None:
                raise ArgSyntaxError(t, "Key:Value")
            assert (
                vs is not None and k is not None
            )  # why do I need this to satisfy mypy?
            tokens.insert(0, vs)
            v, tokens = self.parse_value(tokens, arg)
            # if len(v) == 0:
            #     raise ArgSyntaxError(t, "Key:Value")
            d[k] = v

        return d, tokens
    
    def parse_value(self, tokens: list[str], arg: Arg[Any] | None) -> ParseResult_t[Any]:
        if len(tokens) == 0:
            return "", tokens
        t = self.peek(tokens)
        if self._list_chars is not None and t.startswith(self._list_chars[0]):
            "list"
            tokens[0] = t.removeprefix(self._list_chars[0])
            return self.parse_list(tokens, arg)
        if self._dict_chars is not None and t.startswith(self._dict_chars[0]):
            "dict"
            tokens[0] = t.removeprefix(self._dict_chars[0])
            return self.parse_dict(tokens, arg)
        value_parser = self.resolve_value_parser(arg)
        return value_parser.parse(tokens)

    def parse(
        self, tokens: list[str], argd: list[Arg[Any]]
    ) -> ParseResult_t[ParsedArgs_t]:
        xs_tokens: list[str] = []
        args: list[Any] = []
        kwargs: dict[str, Any] = {}

        while len(tokens) > 0 and len(argd) > 0:
            t = self.peek(tokens)
            if t.startswith(self._flag_char):
                "we have a flag arg"
                t, tokens = self.next(tokens)
                k = t.removeprefix(self._flag_char)
                arg, argd = self.get_kwarg(argd, k)
                if arg is None:
                    xs_tokens += [t]
                    continue
                kwargs[k] = (arg, True)
                continue

            kw, val = self.split_kw_val(t)
            if kw is not None:
                "we have a kw arg"
                if val is not None:
                    tokens[0] = val  # we already took the kw
                else:
                    _, tokens = self.next(tokens)
                arg, argd = self.get_kwarg(argd, kw)
                if arg is None:
                    t, tokens = self.next(tokens)
                    xs_tokens += [kw + self._kw_eq_char + t]
                    continue
                    # raise ArgUnexpectedKwError(kw)
                val, tokens = self.parse_value(tokens, arg)
                kwargs[kw] = (arg, val)
            else:
                "we have a pos arg"
                arg, argd = self.get_arg(argd)
                if arg is None:
                    t, tokens = self.next(tokens)
                    xs_tokens.append(t)
                    continue
                    # raise ArgUnexpectedPosError(len(args))
                val, tokens = self.parse_value(tokens, arg)
                args.append((arg, val))

        return (args, kwargs), xs_tokens + tokens
