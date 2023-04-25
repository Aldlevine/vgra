import inspect
from dataclasses import MISSING, dataclass, fields, is_dataclass
from types import EllipsisType
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
    dataclass_transform,
)

from vgra.args import Arg, ArgDef

from .args import EMPTY, ArgKind, TArg

PArgs = ParamSpec("PArgs")
TRet = TypeVar("TRet", covariant=True)


def _parse_signature(fn: Callable[PArgs, Any]) -> list[Arg[Any]]:
    args: list[Arg[Any]] = []
    sig = inspect.signature(fn)
    for _k, param in sig.parameters.items():
        arg = param.default
        if arg is EMPTY:
            arg = ArgDef(..., "")
        assert isinstance(arg, ArgDef)
        args.append(
            Arg(
                ArgKind(param.kind),
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
        max_name = max(max_name, len(arg.name) + 2)
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

        name = arg.name.ljust(max_name)
        t = ("" if arg.type == ... else inspect.formatannotation(arg.type)).ljust(
            max_t + 2
        )
        default = ("" if arg.default == ... else repr(arg.default)).ljust(
            max_default + 2
        )

        print(f"--{name}{t}{default}{arg.doc}")


def _clean_fn(fn: Callable[PArgs, Any]) -> None:
    if inspect.isfunction(fn):
        fn.__defaults__ = tuple()
    if is_dataclass(fn):
        fn.__init__.__defaults__ = tuple()  # type: ignore[misc, only called on classes from decorator, so we know we have correct __init__]
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


def arg(*, default: TArg | EllipsisType = Ellipsis, doc: str = "") -> TArg:
    return cast(TArg, ArgDef(default, doc))


class StaticCli:
    args: ClassVar[list[Arg[Any]]]

    @classmethod
    def print_signature(cls) -> None:
        ...


class Cli(Generic[PArgs, TRet]):
    def __init__(self, fn: Callable[PArgs, TRet], /) -> None:
        super().__init__()
        self._fn = fn
        self._args: list[Arg[Any]] = _parse_signature(fn)
        _clean_fn(fn)

    @property
    def args(self) -> list[Arg[Any]]:
        return self._args

    def print_signature(self) -> None:
        _print_signature(self._args)

    def __call__(self, *args: PArgs.args, **kwargs: PArgs.kwargs) -> TRet:
        return _call_cli(self._fn, self._args, *args, **kwargs)


@dataclass_transform(field_specifiers=(arg,))
def cli(fn: Callable[PArgs, TRet]) -> Cli[PArgs, TRet]:
    if inspect.isclass(fn):
        fn = dataclass(fn)
    wrapper = Cli(fn)
    for attr in ("__name__", "__doc__"):
        setattr(wrapper, attr, getattr(fn, attr))

    return wrapper
