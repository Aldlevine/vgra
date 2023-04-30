import json
import os
from dataclasses import KW_ONLY, asdict
from typing import Any

from vgra.args import MISSING, arg
from vgra.cli import DataCli, cli

DB_FILE = "examples/crud/db.json"


def load_data() -> list[dict[str, Any]]:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data: list[dict[str, Any]] = json.load(f)
    else:
        data = []
    return data


def save_data(data: list[dict[str, Any]]):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


_help: bool = arg(names=["help", "h"], required=False)


class BaseCommand(DataCli):
    def validate(self, argv: list[str]) -> bool:
        if len(argv) > 0:
            self.print_error(
                Exception(f"Woah, you've given me too many arguments: {' '.join(argv)}")
            )
            return False
        return True


@cli
class AddCommand(BaseCommand):
    """
    add: Add a person to the database
    """

    fname: str = arg(doc="first name")
    lname: str = arg(doc="last name")
    age: int = arg(default=-1)
    _: KW_ONLY
    help: bool = _help

    def next(self, argv: list[str]) -> None:
        if not self.validate(argv):
            return
        d = {k: v for k, v in asdict(self).items() if k not in ("help")}
        data = load_data()
        if len(data) > 0:
            id = max(r["id"] for r in data) + 1
        else:
            id = 0
        d["id"] = id
        data.append(d)
        save_data(data)
        print(f"Adding {d}")


@cli
class GetCommand(BaseCommand):
    """
    get: Get a person from the database
    """

    id: int = arg(doc="the person's id")
    format: str = arg(doc="optional format string", required=False)
    _: KW_ONLY
    help: bool = _help

    def next(self, argv: list[str]) -> None:
        if not self.validate(argv):
            return
        data = load_data()
        r = [r for r in data if r["id"] == self.id]
        if len(r) == 0:
            print(f"Cannot find person with id {self.id}")
            return

        if self.format is not MISSING:
            print(self.format.format(**r[0]))
        else:
            print(f"{r[0]}")


@cli
class ListCommand(BaseCommand):
    """
    list: List all persons in database
    """

    page: int = arg(default=0, doc="the page of records to list")
    _: KW_ONLY
    len: int = arg(default=10, doc="the number of records per page")
    help: bool = _help

    def next(self, argv: list[str]) -> None:
        if not self.validate(argv):
            return
        data = load_data()
        start = self.page * self.len
        end = start + self.len
        print(*data[start:end], sep="\n")


@cli(required=False)
class UpdCommand(BaseCommand):
    """
    upd: Update a person's record in the database
    """

    id: int = arg(doc="the person's id")
    fname: str = arg(doc="first name")
    lname: str = arg(doc="last name")
    age: int = arg(doc="age")
    _: KW_ONLY
    help: bool = _help

    def next(self, argv: list[str]) -> None:
        if not self.validate(argv):
            return

        if self.check_missing(id=self.id):
            return

        data = load_data()
        r = [r for r in data if r["id"] == self.id]
        if len(r) == 0:
            print(f"Cannot find person with id {self.id}")
            return

        for k, v in asdict(self).items():
            if k not in ("fname", "lname", "age"):
                continue
            if type(v) == type(MISSING):
                continue
            r[0][k] = v

        save_data(data)
        print(f"Updated person {self.id} to {r[0]}")


@cli
class DelCommand(BaseCommand):
    """
    del: Delete a person from the database
    """

    id: int = arg(doc="the person's id")
    _: KW_ONLY
    help: bool = _help

    def next(self, argv: list[str]) -> None:
        if not self.validate(argv):
            return
        data = load_data()
        r = [r for r in data if r["id"] == self.id]
        if len(r) == 0:
            print(f"Cannot find person with id {self.id}")
        else:
            data.remove(r[0])
            save_data(data)
            print(f"deleted {r[0]}")


@cli(required=False)
class CrudCli(DataCli):
    """
    crud - performs basic CRUD tasks on a fantasy database
    """

    command: str = arg(
        names=["<command>"], choices=["add", "del", "upd", "get", "list"]
    )
    _: KW_ONLY
    help: bool = arg(names=["help", "h"])

    def next(self, argv: list[str]) -> None:
        if self.command is MISSING:
            if self.help:
                self.print_help()
            else:
                self.print_error(Exception("please enter a command"))
            return

        Cmd: type[DataCli]
        match self.command:
            case "add":
                Cmd = AddCommand
            case "del":
                Cmd = DelCommand
            case "upd":
                Cmd = UpdCommand
            case "get":
                Cmd = GetCommand
            case "list":
                Cmd = ListCommand
            case _:
                self.print_error(Exception(f"Invalid command '{self.command}'"))
                return

        if self.help:
            self.print_help()
            Cmd.print_help()
        else:
            _, argv = Cmd.exec(argv)


CrudCli.exec()
