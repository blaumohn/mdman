#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
venv_dir="$repo_root/.venv"
venv_python="$venv_dir/bin/python"
bin_dir=${MDMAN_BIN_DIR:-"$HOME/.local/bin"}
installed_mdman="$venv_dir/bin/mdman"

if [ ! -x "$venv_python" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "setup: python3 wurde nicht gefunden" >&2
        exit 1
    fi
    echo "Erzeuge virtuelle Umgebung: $venv_dir"
    python3 -m venv "$venv_dir"
fi

echo "Installiere mdman in der Repo-venv"
"$venv_python" -m pip install --editable "$repo_root"

if [ ! -x "$installed_mdman" ]; then
    echo "setup: Installation erzeugte keinen mdman-Befehl" >&2
    exit 1
fi

mkdir -p "$bin_dir"
if [ -e "$bin_dir/mdman" ] && [ ! -L "$bin_dir/mdman" ]; then
    echo "setup: Zieldatei existiert bereits: $bin_dir/mdman" >&2
    exit 1
fi
ln -sfn "$installed_mdman" "$bin_dir/mdman"

echo
echo "Fertig. mdman verwendet jetzt diese Repo-venv:"
echo "  $installed_mdman"
echo
echo "Falls $bin_dir noch nicht im PATH ist:"
echo "  export PATH=\"$bin_dir:\$PATH\""
