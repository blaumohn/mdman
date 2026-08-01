# mdman

Ein kleiner, monochromer Markdown-Reader für das Terminal.

## Installation

```bash
./scripts/setup.sh
```

Das Skript legt `.venv/` im Repo an, installiert `mdman` dort editable und
verknüpft den Befehl standardmäßig nach `~/.local/bin/mdman`. Der Symlink zeigt
direkt auf die Repo-venv. Ein anderer Installationsort kann mit
`MDMAN_BIN_DIR=/pfad/bin ./scripts/setup.sh` gewählt werden.

Direkter Aufruf ohne Wrapper:

```bash
.venv/bin/mdman README.md
```

Wenn `~/.local/bin` im `PATH` liegt, genügt danach überall:

```bash
mdman README.md
```

Für die statische Typprüfung zusätzlich:

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m mypy src tests
```

## Verwendung

```bash
mdman README.md
mdman -w 80 dokument.md
mdman --pager dokument.md
mdman --toc dokument.md
cat dokument.md | mdman
```

Die Ausgabe ist standardmäßig ohne Farbe und auf 80 Spalten begrenzt. Mit
`--pager` wird der Inhalt über den eingestellten Pager (normalerweise `less`)
angezeigt.
Mit `--toc` wird vor dem Dokument ein hierarchisches Inhaltsverzeichnis aus
seinen Überschriften ausgegeben. Markdown kann auch direkt über stdin kommen,
zum Beispiel mit `cat dokument.md | mdman`.
