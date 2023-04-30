import sys

from vgra.args import MISSING, arg
from vgra.cli import cli


@cli(required=False)
def rot_cli(
    ifile: str = arg(
        names=["<ifile>", "if", "i"], doc="The input file, stdin if unspecified"
    ),
    ofile: str = arg(
        names=["<ofile>", "of", "o"], doc="The output file, stdout if unspecified"
    ),
    *,
    rot: int = arg(default=13, doc="The rotation amount"),
    help: bool = arg(names=["help", "h"], choices=[""], doc="Show this message"),
) -> None:
    """
    rot - performs a rotation cypher on an input
    """

    if help:
        rot_cli.print_help()
        return

    if ifile == MISSING:
        s = ""
        for line in sys.stdin:
            s += line
    else:
        with open(ifile, "r", encoding="utf-8") as f:
            s = f.read()
    lower = [chr(i) for i in range(ord("a"), ord("z") + 1)]
    upper = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
    out: list[str] = []
    for c in s:
        if c in lower:
            i = lower.index(c)
            c = lower[(i + rot) % len(lower)]
        elif c in upper:
            i = upper.index(c)
            c = upper[(i + rot) % len(upper)]
        out.append(c)

    s = "".join(out)
    if ofile is MISSING:
        sys.stdout.write(s)
    else:
        with open(ofile, "w", encoding="utf-8") as f:
            f.write(s)


rot_cli.exec()
