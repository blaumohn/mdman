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

### JSONL-Vorschau

Benannte Darstellungsprofile wählen rekursiv Felder aus JSONL-Einträgen
und bestimmen ihre Darstellung. Ein Profil `web-sitzung` liegt unter
`$XDG_CONFIG_HOME/mdman/schemas/web-sitzung.json`. Ist `XDG_CONFIG_HOME`
leer, ungesetzt oder relativ, gilt `~/.config` als Basis. Weitere Profile
werden in `$XDG_CONFIG_DIRS` gesucht, standardmäßig `/etc/xdg`.
Die erste gefundene Datei wird verwendet, Benutzerprofile haben Vorrang.

```bash
mdman jsonl web-sitzung sitzung.jsonl
mdman jsonl web-sitzung < sitzung.jsonl
mdman jsonl ./web-sitzung.json sitzung.jsonl
mdman jsonl web-sitzung --width 100 --pager sitzung.jsonl
```

Profilordner, verfügbare Profile und das Profilformat lassen sich direkt
über die CLI anzeigen.

```bash
mdman profiles list
mdman profiles validate
mdman profiles validate web-sitzung
mdman profiles schema
mdman jsonl --help
mdman profiles --help
```

`list` zeigt die tatsächlich verwendeten Suchverzeichnisse auch dann,
wenn noch keine Profile existieren. Gleichnamige Profile in späteren
Suchverzeichnissen werden als überlagert gekennzeichnet. `validate` prüft
ohne Argument alle gefundenen Profildateien einschließlich überlagerter
Dateien. Mit Profilname prüft es das ausgewählte Profil, mit Dateipfad
die angegebene Datei. Bei ungültigen Profilen liefert es den Exitstatus 1
und prüft die übrigen Dateien weiter.

Das verbindliche [Konfigurationsschema](src/mdman/profile.schema.json)
wird mit dem Paket ausgeliefert. Profilvalidierung und die Erklärungen
in der CLI-Hilfe verwenden diese gemeinsame Definition. Beschreibungen,
Blatttypen, Metadatenvarianten und Beispiele stammen aus dem Schema.
`mdman profiles schema` gibt es als JSON aus, sodass es sich in eine
Datei umleiten und mit weiteren JSON-Schema-Werkzeugen verwenden lässt.

Ein Profil enthält ein `schema` und optional `meta`.

```json
{
  "schema": {
    "author": {"name": "string"},
    "created": "date",
    "message": {
      "body": "markdown",
      "attachments": [{"name": "string", "size": "number"}]
    }
  },
  "meta": true
}
```

Objekte im Schema wählen gleichnamige Felder rekursiv aus. Eine Liste
mit genau einem Schema beschreibt jedes Element der entsprechenden
Datenliste. Schlüssel werden in der Reihenfolge des Profils angezeigt.
Fehlende ausgewählte Felder werden ausgelassen. Vorhandene Felder müssen
den angegebenen Typ haben. Fehler nennen Dateizeile und Feldpfad.
Jede JSONL-Zeile muss ein JSON-Objekt sein, Leerzeilen sind ungültig.

Die Blatttypen sind `string`, `markdown`, `date` und `number`.
`string` zeigt Text wörtlich. `markdown` rendert Markdown in einem
beschrifteten Rahmen, sodass es auch ohne Farben von Datenfeldern
unterscheidbar bleibt. `date` akzeptiert ISO-Datumswerte und
ISO-Zeitstempel und erhält ihre Schreibweise. `number` akzeptiert
JSON-Zahlen. Objekte werden eingerückt, Listen wiederholen die Darstellung
ihrer Elemente. Leere Objekte und Listen erscheinen als `{}` und `[]`.

Bei fehlendem `meta` oder `meta: false` gilt `schema` für alle Zeilen.
`meta: true` stellt die erste Zeile vollständig und rekursiv als Metadaten
dar. Zeichenketten erscheinen dabei als Text. Ab Zeile 2 gilt `schema`.
Mit einem Objekt als `meta` erhält die erste Zeile ein eigenes
Darstellungsschema, beispielsweise für eine Markdown-Beschreibung.

```json
{
  "schema": {"message": {"body": "markdown"}},
  "meta": {
    "title": "string",
    "created": "date",
    "description": "markdown",
    "project": {"name": "string"}
  }
}
```

Das Profilformat ist mdmans Darstellungsschema. `--content` und der
bisherige Aufruf mit `--input jsonl` werden durch `mdman jsonl PROFIL`
ersetzt. `--meta` wird im Profil eingestellt. Der JSONL-Befehl unterstützt
`--width` und `--pager`. Ohne Dateiname oder mit `-` liest er stdin.
