from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import cast

from mdman.profiles import Profile, Schema


class JsonlError(ValueError):
    pass


@dataclass(frozen=True)
class Field:
    name: str
    kind: str
    value: object
    children: tuple[Field, ...] = ()


@dataclass(frozen=True)
class Entry:
    line: int
    fields: tuple[Field, ...]
    metadata: bool = False


def read_entries(source: str, *, profile: Profile) -> list[Entry]:
    entries = []
    lines = source.split("\n")
    if lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, start=1):
        record = parse_line(line, number)
        metadata = number == 1 and profile.meta is not False
        schema: Schema | None = profile.schema
        if metadata:
            schema = (
                profile.meta if isinstance(profile.meta, dict) else None
            )
        root = build_field("", record, schema, number, "$")
        entries.append(Entry(number, root.children, metadata))
    return entries


def parse_line(line: str, number: int) -> dict[str, object]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"ungültige JSON-Konstante {value}")

    try:
        record = json.loads(line, parse_constant=reject_constant)
    except ValueError as error:
        raise JsonlError(
            f"Zeile {number}: ungültiges JSON: {error}"
        ) from error
    if not isinstance(record, dict):
        raise JsonlError(f"Zeile {number}: muss ein JSON-Objekt sein")
    return cast(dict[str, object], record)


def build_field(
    name: str,
    value: object,
    schema: Schema | None,
    number: int,
    path: str,
) -> Field:
    if isinstance(schema, dict) or (
        schema is None and isinstance(value, dict)
    ):
        if not isinstance(value, dict):
            raise field_error(number, path, "Objekt")
        fields = value if schema is None else schema
        children = tuple(
            build_field(
                key,
                value[key],
                None if schema is None else schema[key],
                number,
                f"{path}[{json.dumps(key, ensure_ascii=False)}]",
            )
            for key in fields
            if key in value
        )
        return Field(name, "object", value, children)
    if isinstance(schema, list) or (
        schema is None and isinstance(value, list)
    ):
        if not isinstance(value, list):
            raise field_error(number, path, "Liste")
        children = tuple(
            build_field(
                "",
                item,
                None if schema is None else schema[0],
                number,
                f"{path}[{index}]",
            )
            for index, item in enumerate(value)
        )
        return Field(name, "list", value, children)
    if schema is None:
        return Field(name, "string", value)
    if schema == "number":
        if isinstance(value, bool) or not isinstance(
            value, (int, float)
        ):
            raise field_error(number, path, "number")
    elif not isinstance(value, str):
        raise field_error(number, path, str(schema))
    elif schema == "date":
        validate_date(value, number, path)
    return Field(name, str(schema), value)


def validate_date(value: str, number: int, path: str) -> None:
    try:
        date.fromisoformat(value)
        return
    except ValueError:
        pass
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise field_error(
            number, path, "ISO-Datum/Zeitstempel"
        ) from error


def field_error(number: int, path: str, expected: str) -> JsonlError:
    return JsonlError(
        f"Zeile {number}: Feld {path} erwartet {expected}"
    )
