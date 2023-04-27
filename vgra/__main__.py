from typing import Any
from .lib.value_parsers import DEFAULT_PARSERS
from .parser import PythonicArgParser
from .cli import StaticCli, arg, cli, Cli

# DEFINE

parser = PythonicArgParser(DEFAULT_PARSERS)


@cli(argparser=parser)
class Global(StaticCli):
    """The command doc"""

    command: str = arg(default="", doc="The command to run [cmd1, cmd2]")
    help: bool = arg(default=False, kw_only=True)


@cli(argparser=parser)
def cmd1(
    x: int = arg(doc="The X var"),
    y: int = arg(doc="The Y var"),
) -> None:
    """Command 1"""

    print(f"CMD1: we got x={x} y={y}")


@cli(argparser=parser)
def cmd2(
    u: str = arg(doc="The U var"),
    v: str = arg(doc="The V var"),
) -> None:
    """Command 2"""

    print(f"CMD2: we got u={u} v={v}")


# map of name:command
cmds: dict[str, Cli[Any, Any]] = {
    "cmd1": cmd1,
    "cmd2": cmd2,
}

# RUN

g, argv = Global.exec()

cmd = cmds.get(g.command, Global)

if g.help:
    cmd.print_help()
elif isinstance(cmd, Global):
    Global.print_error(Exception(f"invalid command '{g.command}'"))
else:
    cmd.exec(argv)
# for cmd_str, cmd in cmds.items():
#     if cmd_str != g.command:
#         continue
#     if g.help:
#         cmd.print_help()
#         exit()
#     _, argv = cmd.exec(argv)
#     exit()

# if g.help:
#     Global.print_help()
# elif g.command == "":
#     Global.print_error(Exception(f"command not specified"))
# else:
#     Global.print_error(Exception(f"invalid command '{g.command}'"))
