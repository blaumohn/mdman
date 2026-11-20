#!/bin/sh
set -eu

script_dir=$(CDPATH='' cd -P "$(dirname "$0")" && pwd)
repo_root=$(CDPATH='' cd -P "$script_dir/.." && pwd)
venv_dir=${MDMAN_VENV_DIR:-"$repo_root/.venv"}
case "$venv_dir" in
    /*) ;;
    *) venv_dir="$repo_root/$venv_dir" ;;
esac
venv_python="$venv_dir/bin/python"
bin_dir=${MDMAN_BIN_DIR:-"$HOME/.local/bin"}
installed_mdman="$venv_dir/bin/mdman"

for required in node npm; do
    if ! command -v "$required" >/dev/null 2>&1; then
        printf '%s\n' "setup: $required wurde nicht gefunden (Node.js >= 22.12 erforderlich)" >&2
        exit 1
    fi
done
node <<'JS'
const [major, minor] = process.versions.node.split('.').map(Number)
if (major < 22 || (major === 22 && minor < 12)) {
    console.error('setup: Node.js >= 22.12 erforderlich')
    process.exit(1)
}
JS

if [ ! -x "$venv_python" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        printf '%s\n' "setup: python3 wurde nicht gefunden" >&2
        exit 1
    fi
    printf '%s\n' "Erzeuge virtuelle Umgebung: $venv_dir"
    python3 -m venv "$venv_dir"
fi

printf '%s\n' "Installiere mdman in der Repo-venv"
"$venv_python" -m pip install --editable "$repo_root"

if [ ! -x "$installed_mdman" ]; then
    printf '%s\n' "setup: Installation erzeugte keinen mdman-Befehl" >&2
    exit 1
fi

printf '%s\n' "Installiere Browser-Editor aus dem Lockfile"
npm --prefix "$repo_root/editor" ci --no-fund

mkdir -p "$bin_dir"
if [ -e "$bin_dir/mdman" ] && [ ! -L "$bin_dir/mdman" ]; then
    printf '%s\n' "setup: Zieldatei existiert bereits: $bin_dir/mdman" >&2
    exit 1
fi
if [ -L "$bin_dir/mdman" ]; then
    rm "$bin_dir/mdman"
fi
ln -s "$installed_mdman" "$bin_dir/mdman"

printf '\n'
printf '%s\n' "Fertig. mdman verwendet jetzt diese Repo-venv:"
printf '%s\n' "  $installed_mdman"
printf '\n'
printf '%s\n' "Falls $bin_dir noch nicht im PATH ist:"
printf '%s\n' "  export PATH=\"$bin_dir:\$PATH\""
