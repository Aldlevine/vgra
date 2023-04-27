import inspect
from dataclasses import dataclass
from enum import Enum
from types import EllipsisType
from typing import Generic, TypeVar


class ArgKind(Enum):
    POS = inspect._ParameterKind.POSITIONAL_ONLY  # type: ignore[private use, we will deal with this when necessary]
    POSKW = inspect._ParameterKind.POSITIONAL_OR_KEYWORD  # type: ignore[see above]
    KW = inspect._ParameterKind.KEYWORD_ONLY  # type: ignore[see above]
    VPOS = inspect._ParameterKind.VAR_POSITIONAL  # type: ignore[see above]
    VKW = inspect._ParameterKind.VAR_KEYWORD  # type: ignore[see above]


EMPTY = inspect._empty  # type: ignore[see above]

TArg = TypeVar("TArg")

@dataclass
class Arg(Generic[TArg]):
    kind: ArgKind
    name: str
    type: type | EllipsisType
    default: TArg
    doc: str

    def has_default(self) -> bool:
        return self.default is not Ellipsis


@dataclass(frozen=True)
class ArgDef(Generic[TArg]):
    default: TArg
    doc: str
    kw_only: bool
