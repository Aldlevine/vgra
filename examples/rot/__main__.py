from vgra.args import MISSING, arg
from vgra.cli import cli


@cli(required=False)
def my_cli(
    ifile: str = arg(names=["<ifile>", "if", "i"], doc="The input file"),
    ofile: str = arg(names=["<ofile>", "of", "o"], doc="The output file, stdout if unspecified"),
    *,
    rot: int = arg(default=13, doc="The rotation amount"),
    help: bool = arg(names=["help", "h"], doc="Show this message"),
) -> None:
    """
    rot: performs an rot cypher on a file
    """
    if help:
        my_cli.print_help()
        return

    if my_cli.check_missing(ifile=ifile):
        return

    with open(ifile, "r", encoding="utf-8") as f:
        s = f.read()
    lower = [chr(i) for i in range(ord('a'), ord('z') + 1)]
    upper = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
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
        print(s)
    else:
        with open(ofile, "w", encoding="utf-8") as f:
            f.write(s)

my_cli.exec()
