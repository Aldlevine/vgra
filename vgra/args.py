import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar, cast


class ArgKind(Enum):
    POS = inspect._ParameterKind.POSITIONAL_ONLY  # type: ignore[private use, we will deal with this when necessary]
    POSKW = inspect._ParameterKind.POSITIONAL_OR_KEYWORD  # type: ignore[see above]
    KW = inspect._ParameterKind.KEYWORD_ONLY  # type: ignore[see above]
    VPOS = inspect._ParameterKind.VAR_POSITIONAL  # type: ignore[see above]
    VKW = inspect._ParameterKind.VAR_KEYWORD  # type: ignore[see above]


EMPTY = inspect._empty  # type: ignore[see above]


class _MISSING_TYPE:
    def __len__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "MISSING"


MISSING = _MISSING_TYPE()

TArg = TypeVar("TArg")


@dataclass
class Arg(Generic[TArg]):
    kind: ArgKind
    name: str
    names: list[str]
    type: type
    default: TArg | _MISSING_TYPE
    doc: str
    required: bool
    choices: list[TArg] | None

    def has_default(self) -> bool:
        return self.default is not MISSING


@dataclass(frozen=True)
class ArgDef(Generic[TArg]):
    default: TArg
    names: list[str] | _MISSING_TYPE
    doc: str
    kw_only: bool
    required: bool
    choices: list[TArg] | None


def arg(
    *,
    default: TArg | _MISSING_TYPE = MISSING,
    names: list[str] | _MISSING_TYPE = MISSING,
    doc: str = "",
    kw_only: bool = False,
    required: bool = True,
    choices: list[TArg] | None = None,
) -> TArg:
    return cast(
        TArg,
        ArgDef(
            default,
            names,
            doc,
            kw_only,
            required,
            choices, # type: ignore
        ),
    )
