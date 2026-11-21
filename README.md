# mdman

Mit mdman liest du Markdown ohne Farben im Terminal, bearbeitest es im
lokalen Browser und bereitest es dort zum Drucken vor. Für JSONL-Dateien
kannst du auswählen, welche Felder im Terminal erscheinen.

## Ausprobieren

Du brauchst Python ≥ 3.10 mit `venv`, Node.js ≥ 22.12 mit npm, Make und Git.
Führe im geklonten Repo aus:

```bash
make setup
```

Das richtet den Browser-Editor ein und verknüpft den Befehl `mdman` mit
`~/.local/bin`. Liegt dieses Verzeichnis noch nicht im Suchpfad `PATH`,
folge dem Hinweis am Ende der Installation oder nutze im Repo
`.venv/bin/mdman`. Die Installation verwendet Dateien aus diesem Checkout.

```bash
mdman README.md
mdman edit README.md --open
```

Der erste Befehl zeigt diese Anleitung formatiert im Terminal. Der zweite
öffnet dieselbe Datei im Browser. In der Vorschau führt der Link zur
[Editor-Anleitung](editor/README.md) direkt zum nächsten Dokument.

Mit **Geteilt** siehst du Text und Vorschau nebeneinander. **Vorschau** zeigt
das formatierte Dokument mit Tabellen, Aufgabenlisten und Diagrammen aus
Mermaid-Code. **Drucken** öffnet die Druckansicht. Mit **Dateien** kannst du
weitere Markdown-Dateien im Dokumentordner und seinen Unterordnern öffnen.

**Speichern** schreibt in die Quelldatei. Bei einem Dokumentwechsel fragt der
Editor nach, wenn Änderungen offen sind. Hat sich die Datei seit dem Laden
auf der Platte geändert, meldet der Editor den Konflikt.

Weitere Aufrufe aus einem zweiten Terminal können andere Dateien im laufenden
Editor öffnen. Beende den Server mit Strg+C im ersten Terminal.

## Ein Inhaltsverzeichnis erzeugen

```bash
mdman --toc README.md
```

`--toc` steht für *table of contents*. Der Befehl zeigt das Dokument mit
Inhaltsverzeichnis im Terminal. Mit `-i` schreibt mdman das Ergebnis in die
Quelldatei und ersetzt den markierten Bereich bei späteren Aufrufen. Für eine
eigene Position setze `<!-- mdman:toc:start -->` und `<!-- mdman:toc:end -->`
jeweils auf eine eigene Zeile an der gewünschten Stelle. In das Verzeichnis
kommen die Überschriften nach dem Endmarker.

## Formeln im Terminal lesen

Die Formeldarstellung nutzt den in [pyproject.toml](pyproject.toml)
eingetragenen [pylatexenc-Fork](https://github.com/blaumohn/pylatexenc)
zum Lesen der LaTeX-Struktur und zum Umwandeln der Symbole in Unicode.

mdman wandelt LaTeX-Formeln in Unicode-Text um, etwa `\frac{a+b}{c}` in
`(a + b)/c`. Setze Formeln im Text zwischen `$…$` oder `\(…\)` und
eigenständige Formeln zwischen `$$…$$` oder `\[…\]`. Die Umwandlung gilt
auch für Markdown-Felder in der JSONL-Vorschau.

Die Ausgabe nähert Formeln als Text an. Beispielsweise bleiben manche
Tiefstellungen als Unterstrich sichtbar. Unbekannte Befehle und ungültige
Formeln bleiben als Quelltext erhalten. Hebräischen Text in `\text{…}`
zeigt das interaktive Terminal von rechts nach links, sofern das Terminal
diese Leserichtung unterstützt.

## JSONL-Dateien lesen

Bei JSONL enthält jede Zeile einen JSON-Datensatz. Ein Darstellungsprofil
bestimmt, welche Felder mdman anzeigt und welche es als Markdown formatiert.

```bash
mdman profiles list
mdman jsonl PROFIL DATEI
```

`list` zeigt die verfügbaren Profile und die Ordner, in denen mdman sucht.
Ersetze `PROFIL` durch einen Namen aus der Liste oder den Pfad zu deiner
Profildatei und `DATEI` durch deine JSONL-Datei. Für ein eigenes Profil
zeigt `mdman profiles --help` das Format und Beispiele aus dem verbindlichen
[Profilschema](src/mdman/profile.schema.json).

## Hilfe und Entwicklung

- `mdman --help` zeigt die Befehle und die Optionen für die Terminalansicht.
- `mdman edit --help` erklärt den Browseraufruf.
- `mdman jsonl --help` erklärt die JSONL-Vorschau und das Profilformat.
- `make dev-install` installiert die Entwicklungswerkzeuge. `make check`
  prüft Python-Code und Browser-Editor. Details zum Editor stehen in der
  [Editor-Anleitung](editor/README.md).
