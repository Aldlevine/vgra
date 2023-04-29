import re
from typing import Any, Iterable

from ...args import Arg
from ...parser import (
    ArgParser,
    ArgSyntaxError,
    ParsedArgs_t,
    ParseResult_t,
    ValueParser,
)
from ..value_parsers import DEFAULT_VALUE_PARSERS


class PythonicArgParser(ArgParser):
    def __init__(
        self,
        value_parsers: Iterable[ValueParser[Any]] = DEFAULT_VALUE_PARSERS,
        kw_eq_char: str = "=",
        kw_flag_char: str = "-",
        list_chars: tuple[str, str] | None = ("[", "]"),
        dict_chars: tuple[str, str, str] | None = ("{", ":", "}"),
    ) -> None:
        super().__init__(value_parsers)

        self._kw_eq_char = kw_eq_char
        self._kw_flag_char = kw_flag_char
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

    def is_list_start(self, t: str) -> bool:
        return self._list_chars is not None and t == self._list_chars[0]

    def is_list_end(self, t: str) -> bool:
        return self._list_chars is not None and t == self._list_chars[-1]

    def is_dict_start(self, t: str) -> bool:
        return self._dict_chars is not None and t == self._dict_chars[0]

    def is_dict_end(self, t: str) -> bool:
        return self._dict_chars is not None and t == self._dict_chars[-1]

    def is_container_start(self, t: str) -> bool:
        return self.is_list_start(t) or self.is_dict_start(t)

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

    def eat_list(
        self, tokens: list[str], arg: Arg[Any] | None
    ) -> ParseResult_t[list[str]]:
        l: list[str] = []
        while len(tokens) > 0:
            t, tokens = self.next(tokens)
            if self.is_dict_end(t):
                assert self._list_chars is not None
                raise ArgSyntaxError(t, f"value or {self._list_chars[-1]}")
            if self.is_list_end(t):
                assert self._list_chars is not None
                l += [self._list_chars[-1]]
                break

            t, tokens = self.split_container_ends(t, tokens)
            tokens.insert(0, t)

            eaten, tokens = self.eat_value(tokens, arg)
            l += eaten
        return l, tokens

    def parse_list(self, tokens: list[str], arg: Arg[Any] | None) -> ParseResult_t[Any]:
        l: list[Any] = []
        while len(tokens) > 0:
            t, tokens = self.next(tokens)
            if self.is_dict_end(t):
                assert self._list_chars is not None
                raise ArgSyntaxError(t, f"value or {self._list_chars[-1]}")
            if self.is_list_end(t):
                break

            t, tokens = self.split_container_ends(t, tokens)
            tokens.insert(0, t)

            v, tokens = self.parse_value(tokens, arg)
            l.append(v)

        return l, tokens

    def eat_dict(
        self, tokens: list[str], arg: Arg[Any] | None
    ) -> ParseResult_t[list[str]]:
        d: list[str] = []
        while len(tokens) > 0:
            t, tokens = self.next(tokens)
            if self.is_list_end(t):
                assert self._dict_chars is not None
                raise ArgSyntaxError(t, f"key:value or {self._dict_chars[-1]}")
            if self.is_dict_end(t):
                assert self._dict_chars is not None
                d += [self._dict_chars[-1]]
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
            eaten, tokens = self.eat_value(tokens, arg)
            assert self._dict_chars is not None
            d += [k + self._dict_chars[1] + eaten[0]] + eaten[1:]

        return d, tokens

    def parse_dict(self, tokens: list[str], arg: Arg[Any] | None) -> ParseResult_t[Any]:
        d: dict[str, Any] = {}
        while len(tokens) > 0:
            t, tokens = self.next(tokens)
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
            d[k] = v

        return d, tokens

    def eat_value(
        self, tokens: list[str], arg: Arg[Any] | None
    ) -> ParseResult_t[list[str]]:
        if len(tokens) == 0:
            return [], tokens
        t = self.peek(tokens)
        if self._list_chars is not None and t.startswith(self._list_chars[0]):
            "list"
            tokens[0] = t.removeprefix(self._list_chars[0])
            xs, tokens = self.eat_list(tokens, arg)
            return [self._list_chars[0]] + xs, tokens
        if self._dict_chars is not None and t.startswith(self._dict_chars[0]):
            "dict"
            tokens[0] = t.removeprefix(self._dict_chars[0])
            if len(tokens[0]) == 0:
                tokens.pop(0)
            xs, tokens = self.eat_dict(tokens, arg)
            return [self._dict_chars[0]] + xs, tokens
        t, tokens = self.next(tokens)
        return [t], tokens

    def parse_value(
        self, tokens: list[str], arg: Arg[Any] | None
    ) -> ParseResult_t[Any]:
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
            if len(tokens[0]) == 0:
                tokens.pop(0)
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

            if t.startswith(self._kw_flag_char):
                "we have a name"
                t, tokens = self.next(tokens)
                k = t.removeprefix(self._kw_flag_char)
                kw, val = self.split_kw_val(k)
                if kw is not None:
                    "we have -kw=value"

                    if val is not None:
                        tokens.insert(0, val)
                    arg, argd = self.get_kwarg(argd, kw)
                    if arg is None:
                        xs, tokens = self.eat_value(tokens, arg)
                        xs_tokens += [self._kw_flag_char + kw + self._kw_eq_char] + xs
                        continue
                    val, tokens = self.parse_value(tokens, arg)
                    kwargs[arg.name] = (arg, val)
                else:
                    "we have -kw"
                    arg, argd = self.get_kwarg(argd, k)
                    if arg is None:
                        xs_tokens += [self._kw_flag_char + k]
                        continue
                    kwargs[arg.name] = (arg, True)
                    continue
            else:
                "we have a pos arg"
                arg, argd = self.get_arg(argd)
                if arg is None:
                    xs, tokens = self.eat_value(tokens, arg)
                    xs_tokens.extend(xs)
                    continue
                val, tokens = self.parse_value(tokens, arg)
                args.append((arg, val))

        return (args, kwargs), xs_tokens + tokens
