import inspect
import sys
from dataclasses import MISSING, dataclass, fields, is_dataclass
from types import EllipsisType
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    ParamSpec,
    Self,
    TypeVar,
    cast,
    dataclass_transform,
    overload,
)

from .args import EMPTY, Arg, ArgDef, ArgKind, TArg
from .lib.arg_parsers import StandardArgParser
from .lib.value_parsers import DEFAULT_PARSERS
from .parser import ArgParser, ParseResult_t

PArgs = ParamSpec("PArgs")
TRet = TypeVar("TRet", covariant=True)


def _parse_signature(fn: Callable[PArgs, Any]) -> list[Arg[Any]]:
    args: list[Arg[Any]] = []
    sig = inspect.signature(fn)
    for _k, param in sig.parameters.items():
        arg = param.default
        if arg is EMPTY:
            arg = ArgDef(..., "", False)
        # assert isinstance(arg, ArgDef)
        if not isinstance(arg, ArgDef):
            continue
        args.append(
            Arg(
                ArgKind(ArgKind.KW if arg.kw_only else param.kind),
                param.name,
                param.annotation,
                arg.default,
                arg.doc,
            )
        )
    return args


def _print_signature(args: list[Arg[Any]], /) -> None:
    label_name: str = "arg"
    label_t: str = "type"
    label_default: str = "default"
    label_doc: str = "comment"

    max_name: int = len(label_name)
    max_t: int = len(label_t)
    max_default: int = len(label_default)
    max_doc: int = len(label_doc)

    for arg in args:
        max_name = max(max_name, len(arg.name))
        max_t = max(
            max_t, len("" if arg.type == ... else inspect.formatannotation(arg.type))
        )
        max_default = max(
            max_default, len("" if arg.default == ... else repr(arg.default))
        )
        max_doc = max(max_doc, len(arg.doc))

    label_name = f"\033[4m{label_name.ljust(max_name + 2)}\033[0m"
    label_t = f"\033[4m{label_t.ljust(max_t + 2)}\033[0m"
    label_default = f"\033[4m{label_default.ljust(max_default + 2)}\033[0m"
    label_doc = f"\033[4m{label_doc.ljust(max_doc)}\033[0m"

    print(f"{label_name}{label_t}{label_default}{label_doc}")
    for arg in args:
        default = "" if arg.default == ... else repr(arg.default)

        name = arg.name.ljust(max_name + 2)
        t = ("" if arg.type == ... else inspect.formatannotation(arg.type)).ljust(
            max_t + 2
        )
        default = ("" if arg.default == ... else repr(arg.default)).ljust(
            max_default + 2
        )

        print(f"{name}{t}{default}{arg.doc}")


def _clean_fn(fn: Callable[PArgs, Any]) -> None:
    if inspect.isfunction(fn):
        fn.__defaults__ = tuple()
        fn.__kwdefaults__ = {}
    if is_dataclass(fn):
        fn.__init__.__defaults__ = tuple()  # type: ignore[misc, only called on classes from decorator, so we know we have correct __init__]
        fn.__init__.__kwdefaults__ = {}  # type: ignore[misc, only called on classes from decorator, so we know we have correct __init__]
        for f in fields(fn):
            f.default = MISSING
            f.default_factory = MISSING
            fn.__dataclass_fields__[f.name] = f


# TODO: How to get type system to recognize required args?
def _call_cli(
    fn: Callable[PArgs, TRet],
    dargs: list[Arg[Any]],
    *args: PArgs.args,
    **kwargs: PArgs.kwargs,
) -> TRet:
    combined_args: list[Any] = [a for a in args]
    combined_kwargs: dict[str, Any] = {k: v for k, v in kwargs.items()}
    for i in range(len(args), len(dargs)):
        arg = dargs[i]
        if arg.kind == ArgKind.POS and arg.default is not Ellipsis:
            combined_args.append(arg.default)
            continue
        if arg.name not in combined_kwargs and arg.default is not Ellipsis:
            combined_kwargs[arg.name] = arg.default
    return fn(*combined_args, **combined_kwargs)  # type: ignore[missing, I dont know how to fix this, ParamSpec is too limited]


def arg(
    *, default: TArg | EllipsisType = Ellipsis, doc: str = "", kw_only: bool = False
) -> TArg:
    return cast(TArg, ArgDef(default, doc, kw_only))


class StaticCli:
    args: ClassVar[list[Arg[Any]]]

    @classmethod
    def print_signature(cls) -> None:
        ...

    @classmethod
    def print_help(cls) -> None:
        ...

    @classmethod
    def print_error(cls, e: Exception) -> None:
        ...

    @classmethod
    def exec(cls, argv: list[str] = sys.argv[1:]) -> ParseResult_t[Self]:  # type: ignore
        ...


class Cli(Generic[PArgs, TRet]):
    def __init__(
        self,
        fn: Callable[PArgs, TRet],
        /,
        argparser: ArgParser,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args: list[Arg[Any]] = _parse_signature(fn)
        self._argparser = argparser
        _clean_fn(fn)

    @property
    def args(self) -> list[Arg[Any]]:
        return self._args

    def print_signature(self) -> None:
        _print_signature(self._args)

    def print_help(self) -> None:
        doc = inspect.cleandoc(self._fn.__doc__ or "")
        if len(doc) > 0:
            print()
            print(doc)
        print()
        self.print_signature()
        print()

    def print_error(self, e: Exception) -> None:
        self.print_help()
        print(e)
        print()

    def exec(self, argv: list[str] = sys.argv[1:], **bind_kwargs: Any) -> ParseResult_t[TRet]:
        try:
            (argvd, kwargvd), xs = self._argparser.parse(argv, self.args)
        except Exception as e:
            self.print_error(e)
            exit()

        args = tuple(v for _, v in argvd)
        kwargs = {k: v for k, (_, v) in kwargvd.items()}

        try:
            return self(*args, **kwargs, **bind_kwargs), xs
        except Exception as e:
            self.print_error(e)
            exit()

    def __call__(self, *args: PArgs.args, **kwargs: PArgs.kwargs) -> TRet:
        return _call_cli(self._fn, self._args, *args, **kwargs)
    
    def __instancecheck__(self, __instance: Any) -> bool:
        if isinstance(__instance, Cli):
            return __instance._fn == self._fn
        return False


@overload
def cli(
    *,
    argparser: ArgParser = StandardArgParser(DEFAULT_PARSERS),
) -> Callable[[Callable[PArgs, TRet]], Cli[PArgs, TRet]]:
    ...


@overload
def cli(
    fn: Callable[PArgs, TRet] | None,
    *,
    argparser: ArgParser = StandardArgParser(DEFAULT_PARSERS),
) -> Cli[PArgs, TRet]:
    ...


@dataclass_transform(field_specifiers=(arg,), kw_only_default=False)
def cli(
    fn: Callable[PArgs, TRet] | None = None,
    *,
    argparser: ArgParser = StandardArgParser(DEFAULT_PARSERS),
) -> Cli[PArgs, TRet] | Callable[[Callable[PArgs, TRet]], Cli[PArgs, TRet]]:
    def call_for_fn(fn: Callable[PArgs, TRet]) -> Cli[PArgs, TRet]:
        if inspect.isclass(fn):
            fn = dataclass(fn)
        wrapper = Cli(fn, argparser)
        for attr in ("__name__", "__doc__"):
            setattr(wrapper, attr, getattr(fn, attr))

        return wrapper

    if fn is None:
        return call_for_fn
    else:
        return call_for_fn(fn)
