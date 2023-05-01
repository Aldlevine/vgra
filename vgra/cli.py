import inspect
import sys
from dataclasses import KW_ONLY
from dataclasses import MISSING as DC_MISSING
from dataclasses import dataclass, fields, is_dataclass
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

from .args import EMPTY, MISSING, Arg, ArgDef, ArgKind, arg
from .std.arg_parsers.pythonic_arg_parser import PythonicArgParser
from .parser import ArgParser, ParseError, ParseResult_t

PArgs = ParamSpec("PArgs")
TRet = TypeVar("TRet", covariant=True)


def _parse_signature(fn: Callable[PArgs, Any], required: bool) -> list[Arg[Any]]:
    args: list[Arg[Any]] = []
    sig = inspect.signature(fn)
    kw_only_seen: bool = False
    for _k, param in sig.parameters.items():
        arg = param.default
        if param.annotation == KW_ONLY:
            kw_only_seen = True
        if arg is EMPTY:
            arg = ArgDef(MISSING, [], "", False, True, [])
        if not isinstance(arg, ArgDef):
            continue
        names = arg.names
        if names is MISSING:
            names = [param.name]
        args.append(
            Arg(
                ArgKind(ArgKind.KW if kw_only_seen or arg.kw_only else param.kind),
                param.name,
                cast(list[str], names),
                param.annotation,
                arg.default,
                arg.doc,
                arg.required and required,
                arg.choices
            )
        )
    return args

def _format_type(arg: Arg[Any]) -> str:
    if arg.choices:
        return ", ".join([str(c) for c in arg.choices])
    return inspect.formatannotation(arg.type)

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
        max_name = max(max_name, len(", ".join(arg.names)))
        max_t = max(
            max_t,
            len(_format_type(arg))
        )
        max_default = max(
            max_default,
            len("" if arg.default in (MISSING, Ellipsis) else repr(arg.default)),
        )
        max_doc = max(max_doc, len(arg.doc))

    label_name = f"\033[4m{label_name.ljust(max_name + 2)}\033[0m"
    label_t = f"\033[4m{label_t.ljust(max_t + 2)}\033[0m"
    label_default = f"\033[4m{label_default.ljust(max_default + 2)}\033[0m"
    label_doc = f"\033[4m{label_doc.ljust(max_doc)}\033[0m"

    print(f"{label_name}{label_t}{label_default}{label_doc}")
    for arg in args:
        default = "" if arg.default == MISSING else repr(arg.default)

        name = ", ".join(arg.names).ljust(max_name + 2)
        t = (_format_type(arg)).ljust(max_t + 2)
        default = (
            "" if arg.default in (MISSING, Ellipsis) else str(arg.default)
        ).ljust(max_default + 2)

        print(f"{name}{t}{default}{arg.doc}")


def _clean_fn(fn: Callable[PArgs, Any]) -> None:
    if inspect.isfunction(fn):
        fn.__defaults__ = tuple()
        fn.__kwdefaults__ = {}
    if is_dataclass(fn):
        fn.__init__.__defaults__ = tuple()  # type: ignore[misc, only called on classes from decorator, so we know we have correct __init__]
        fn.__init__.__kwdefaults__ = {}  # type: ignore[misc, only called on classes from decorator, so we know we have correct __init__]
        for f in fields(fn):
            f.default = DC_MISSING
            f.default_factory = DC_MISSING
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
        needs_default = arg.default is not MISSING or not arg.required
        if arg.kind == ArgKind.POS and needs_default:
            combined_args.append(arg.default)
            continue
        if arg.name not in combined_kwargs and needs_default:
            combined_kwargs[arg.name] = arg.default
    return fn(*combined_args, **combined_kwargs)  # type: ignore[missing, I dont know how to fix this, ParamSpec is too limited]


class DataCli:
    args: ClassVar[list[Arg[Any]]]
    cli: ClassVar["Cli[Any, Any]"]

    @classmethod
    def print_signature(cls) -> None:
        cls.cli.print_signature()

    @classmethod
    def print_help(cls) -> None:
        cls.cli.print_help()

    @classmethod
    def print_error(cls, e: Exception) -> None:
        cls.cli.print_error(e)

    @classmethod
    def check_missing(cls, **kwargs: Any) -> bool:
        return cls.cli.check_missing(**kwargs)

    @classmethod
    def exec(cls, argv: list[str] = sys.argv[1:]) -> ParseResult_t[Self]:
        raise NotImplementedError(cls.exec)

    def next(self, argv: list[str]) -> None:
        ...


class Cli(Generic[PArgs, TRet]):
    def __init__(
        self,
        fn: Callable[PArgs, TRet],
        /,
        required: bool,
        argparser: ArgParser,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args: list[Arg[Any]] = _parse_signature(fn, required)
        self._argparser = argparser
        _clean_fn(fn)
        if hasattr(fn, "cli"):
            setattr(fn, "cli", self)

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

    def check_missing(self, **kwargs: Any) -> bool:
        missing: list[str] = []
        for k,v in kwargs.items():
            if v == MISSING:
                missing += [k]
        if len(missing) > 0:
            self.print_error(Exception(f"Missing require arguments {', '.join(missing)}"))
            return True
        return False

    def exec(
        self, argv: list[str] = sys.argv[1:], **bind_kwargs: Any
    ) -> ParseResult_t[TRet]:
        try:
            (argvd, kwargvd), xs = self._argparser.parse(argv, self.args)
        except ParseError as e:
            self.print_error(e)
            exit()

        args = tuple(v for _, v in argvd)
        kwargs = {k: v for k, (_, v) in kwargvd.items()}

        try:
            result = self(*args, **kwargs, **bind_kwargs)
            if isinstance(result, DataCli):
                result.next(xs)
            return result, xs
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
    required: bool = ...,
    argparser: ArgParser = ...,
) -> Callable[[Callable[PArgs, TRet]], Cli[PArgs, TRet]]:
    ...


@overload
def cli(
    fn: Callable[PArgs, TRet] | None,
    *,
    required: bool = ...,
    argparser: ArgParser = ...,
) -> Cli[PArgs, TRet]:
    ...


@dataclass_transform(field_specifiers=(arg,), kw_only_default=False)
def cli(
    fn: Callable[PArgs, TRet] | None = None,
    *,
    required: bool = True,
    argparser: ArgParser = PythonicArgParser(),
) -> Cli[PArgs, TRet] | Callable[[Callable[PArgs, TRet]], Cli[PArgs, TRet]]:
    def call_for_fn(fn: Callable[PArgs, TRet]) -> Cli[PArgs, TRet]:
        orig_fn = fn
        if inspect.isclass(fn):
            fn = dataclass(fn)
        wrapper = Cli(fn, required, argparser)
        if inspect.isclass(orig_fn):
            if issubclass(orig_fn, DataCli):
                orig_fn.cli = wrapper
        # make sure we copy over all our extra stuff!
        for k in dir(fn):
            if k not in dir(Cli):
                setattr(wrapper, k, getattr(fn, k))
        for attr in ("__name__", "__doc__"):
            setattr(wrapper, attr, getattr(fn, attr))

        return wrapper

    if fn is None:
        return call_for_fn
    else:
        return call_for_fn(fn)
