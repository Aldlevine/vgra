import sys
from typing import Any

from .cli import Cli, StaticCli, arg, cli
from .parser import StandardArgParser
from .std.value_parsers import DEFAULT_PARSERS


@cli
def my_fn(
    command: str = arg(doc="The command to run"),
    /,
    x: int = arg(default=1, doc="x ** 2"),
    y: int = arg(default=2, doc="** y"),
    *,
    arg3: str = arg(default="Damn", doc="Don't do it"),
    arg4: dict[str, int] = arg(default={"one": 1}, doc="Something"),
) -> int:
    """This is my documentation!"""
    print(f"running command {repr(command)} with x={x}, y={y}, arg3={arg3}, arg4={arg4}")
    x = (x * x) ** y
    return x


@cli
class MyData(StaticCli):
    x: int = arg(doc="The 'X' argument")
    y: int = arg(default=2, doc="The 'Y' argument")
    z: dict[str, int] = arg(default={"a": 1}, doc="The 'Z' argument")


def exec(clifn: Cli[[Any], Any] | type[StaticCli]):
    argparser = StandardArgParser(
        clifn.args, DEFAULT_PARSERS
    )
    (argvd, kwargvd), _xs = argparser.parse(sys.argv[1:])
    args = tuple(v for _, v in argvd)
    kwargs = {k: v for k, (_, v) in kwargvd.items()}

    try:
        print(clifn(*args, **kwargs))
    except Exception as e:
        print()
        clifn.print_signature()
        print()
        print(e)
        print()

exec(my_fn)

# pprint.pp([(v, a is not None) for a, v in args])
# pprint.pp({k: (v, a is not None) for k, (a, v) in kwargs.items()})
# print(argparser.parse(["hello", "world", "neat", "wow!", "--arg3", "fucking cool"])[0])


# @cli
# def var_fn(
#     *args: int,
#     **kwargs: int,
# ) -> None:
#     ...


# print("\nFN:\n")
# my_fn.print_signature()

# print("\nDATA:\n")
# MyData.print_signature()

# print("\nVAR FN\n")
# var_fn.print_signature()

# print()


# def fart(x: int, y: int, z: int) -> None:
#     ...
