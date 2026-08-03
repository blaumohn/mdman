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

Für die Entwicklungs- und Prüfwerkzeuge zusätzlich:

```bash
make dev-install
```

`make dev-install` legt bei Bedarf zunächst über `scripts/setup.sh` die
Repo-eigene `.venv` an und installiert anschließend das Projekt einschließlich
der Entwicklungsabhängigkeiten.

Die vollständige lokale Prüfung aller Formatierungs-, Linting-, Typ- und
Testprüfungen startet mit:

```bash
make check
```

## Verwendung

```bash
mdman README.md
mdman -w 80 dokument.md
mdman --pager dokument.md
mdman --toc dokument.md
mdman --format markdown --toc dokument.md > dokument.toc.md
mdman --toc -i dokument.md
cat dokument.md | mdman
```

Die Ausgabe ist standardmäßig ohne Farbe und auf 80 Spalten begrenzt. Mit
`--pager` wird der Inhalt über den eingestellten Pager (normalerweise `less`)
angezeigt.
Bei `less` wird die Option `-R` automatisch aktiviert, damit Richs
Formatierungen erhalten bleiben.
Mit `--toc` wird ein hierarchisches Inhaltsverzeichnis in das Dokument
eingefügt. `--format markdown` gibt das verarbeitete Markdown direkt auf
stdout aus. Markdown kann auch direkt über stdin kommen, zum Beispiel mit
`cat dokument.md | mdman`.
Mit `-i` wird die Markdown-Ausgabe zusammen mit `--toc` atomar in dieselbe
Datei zurückgeschrieben. Das funktioniert nur mit einer echten Datei und
nicht zusammen mit `--pager`; der erzeugte TOC-Bereich wird markiert und bei
weiteren Aufrufen ersetzt.
