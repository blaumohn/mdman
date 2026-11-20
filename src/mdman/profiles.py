from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

Schema = str | dict[str, "Schema"] | list["Schema"]


def profile_schema() -> dict[str, Any]:
    resource = files("mdman").joinpath("profile.schema.json")
    return cast(
        dict[str, Any], json.loads(resource.read_text(encoding="utf-8"))
    )


PROFILE_SCHEMA = profile_schema()
PROFILE_VALIDATOR = Draft202012Validator(PROFILE_SCHEMA)


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class Profile:
    schema: dict[str, Schema]
    meta: bool | dict[str, Schema] = cast(
        bool, PROFILE_SCHEMA["properties"]["meta"]["default"]
    )


def parse_profile(value: object) -> Profile:
    error = best_match(PROFILE_VALIDATOR.iter_errors(value))
    if error is not None:
        path = "$" + "".join(
            f"[{json.dumps(part, ensure_ascii=False)}]"
            for part in error.absolute_path
        )
        raise ProfileError(f"{path}: {error.message}")
    record = cast(dict[str, object], value)
    return Profile(
        cast(dict[str, Schema], record["schema"]),
        cast(
            bool | dict[str, Schema],
            record.get(
                "meta", PROFILE_SCHEMA["properties"]["meta"]["default"]
            ),
        ),
    )


def profile_directories() -> list[Path]:
    config_home = os.environ.get("XDG_CONFIG_HOME", "")
    home = Path(config_home)
    if not config_home or not home.is_absolute():
        home = Path.home() / ".config"
    directories = [home]
    config_dirs = os.environ.get("XDG_CONFIG_DIRS") or "/etc/xdg"
    directories.extend(
        Path(directory)
        for directory in config_dirs.split(os.pathsep)
        if Path(directory).is_absolute()
    )
    return list(
        dict.fromkeys(
            directory / "mdman" / "schemas" for directory in directories
        )
    )


def find_profiles() -> list[Path]:
    return [
        path
        for directory in profile_directories()
        if directory.is_dir()
        for path in sorted(directory.glob("*.json"))
        if path.is_file()
    ]


def profile_path(name: str) -> Path:
    # Explicit paths may point outside the configuration directory.
    if "/" in name or "\\" in name or name.endswith(".json"):
        return Path(name).expanduser()
    candidates = [
        directory / f"{name}.json"
        for directory in profile_directories()
    ]
    return next(
        (candidate for candidate in candidates if candidate.is_file()),
        candidates[0],
    )


def load_profile(name: str) -> Profile:
    path = profile_path(name)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return parse_profile(value)
    except (OSError, UnicodeError, ValueError) as error:
        raise ProfileError(f"Profil {path}: {error}") from error
