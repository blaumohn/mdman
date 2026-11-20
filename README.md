# mdman

Ein Kommandozeilenwerkzeug zum Lesen von Markdown im Terminal und zum
Bearbeiten mit HTML- und Druckvorschau im lokalen Browser.

```bash
mdman README.md          # monochrome Terminalausgabe
mdman edit README.md     # Browser-Editor mit GFM und Mermaid
```

Im Browser lassen sich Links zu weiteren Markdown-Dateien direkt verfolgen.
Ein weiterer Aufruf mit einer anderen Datei verwendet den laufenden Server.

## Installation

Voraussetzungen: Python ≥ 3.10 mit `venv`, Node.js ≥ 22.12 mit npm, Make und Git.
Im geklonten `mdman`-Repo genügt:

```bash
make setup
```

Das Setup (`scripts/setup.sh`) legt `.venv/` im Repo an, installiert `mdman` dort editable und
verknüpft den Befehl standardmäßig nach `~/.local/bin/mdman`. Der Symlink zeigt
direkt auf die Repo-venv. Ein anderer Installationsort kann mit
`MDMAN_BIN_DIR=/pfad/bin make setup` gewählt werden. Es installiert außerdem
die Node-Abhängigkeiten des mitgelieferten Editors aus `editor/package-lock.json`.
Die Installation bleibt an diesen Checkout gebunden; Node.js wird auch beim
Start des Editors benötigt.

`make setup` installiert UnicodeIt aus dem Branch `fix/symbol-mappings` von
[`blaumohn/unicodeit`](https://github.com/blaumohn/unicodeit/tree/fix/symbol-mappings).
Ist der Branch bereits unter `.local/unicodeit` ausgecheckt, installiert das
Setup UnicodeIt aus diesem Checkout.

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

`make` ohne Argument zeigt nur die verfügbaren Ziele.

## Im Browser bearbeiten

Der Editor startet mit einer einzelnen vorhandenen `.md`- oder `.markdown`-Datei:

```bash
mdman edit README.md
```

Der erste Aufruf startet Vite auf `127.0.0.1:5173` und gibt die Adresse aus.
Der Browser bleibt standardmäßig geschlossen; `--open` öffnet ihn automatisch.
Dieser Prozess läuft bis Strg+C. Aus einem weiteren Terminal lassen sich
beliebige weitere Dateien im selben Server öffnen, auch aus anderen Ordnern:

```bash
mdman edit /pfad/zu/docs/anleitung.md --open
```

Ein Wechsel von `MD_DIR` oder ein Serverneustart ist dafür nicht nötig.
`--port 5174` wählt einen anderen Port. Folgeaufrufe verwenden denselben Port.

In der HTML-Vorschau öffnen lokale Markdown-Links ihre Zielseite im Editor,
auch über Unterordner oder `../` und mit Sprungmarken. Zurück und Vorwärts
im Browser wechseln zwischen besuchten Dokumenten. Relative Bilder werden
vom Speicherort der Quelldatei aus aufgelöst. Weblinks bleiben Browserlinks;
PDFs, Bilder und Textdateien öffnet der Browser, andere Dateien lädt er herunter.
Fehlende Markdown-Ziele erscheinen als sichtbare Fehlermeldung.

Über **Dateien** steht ergänzend ein Dateibaum mit Unterordnern zur Verfügung,
umgesetzt mit [React Arborist](https://github.com/jameskerr/react-arborist).
Er zeigt Markdown-Dateien unter dem Ordner des geöffneten Einstiegsdokuments;
versteckte Ordner, Symlinks und `node_modules` werden nicht durchsucht.
**Aktualisieren** liest den Baum erneut ein.

**Geteilt** zeigt Editor und Vorschau, **Vorschau** nur das gerenderte Dokument.
**Drucken** nutzt die Druckansicht ohne Bedienelemente. GFM unterstützt Tabellen,
Aufgabenlisten, Durchstreichungen, automatische Links und Fußnoten; Mermaid
rendert Diagramme. Die Ausgabe ist keine garantierte Kopie aller GitHub-Funktionen.

**Speichern** schreibt die Quelldatei. Bei ungespeicherten Änderungen fragt der
Editor vor einem Dokumentwechsel nach. Erkannte externe Änderungen werden vor
dem Überschreiben gemeldet; **Neu laden** übernimmt den aktuellen Dateistand.

Die Browser-Anwendung stammt aus `md-print-editor` und liegt als eigenes
Node-Projekt unter [`editor/`](editor/README.md). Aufbau, Übernahme und lokale
Entwicklung sind dort beschrieben.

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
Bei hebräischen Absätzen hält die Vorschau kurze lateinische Einschübe
beim Umbruch mit dem vorangehenden Wort zusammen. Die interaktive
Vorschau kennzeichnet hebräische Zeilen für die Rechts-nach-links-Darstellung
des Terminals. `less` kann diese Richtungsangabe ab Version 529 weitergeben.
Mit `--toc` wird ein hierarchischer TOC ohne sprachabhängige Überschrift in
das Dokument eingefügt. `--format markdown` gibt das verarbeitete Markdown
direkt auf stdout aus. Markdown kann auch direkt über stdin kommen, zum
Beispiel mit `cat dokument.md | mdman`.
Mit `-i` wird die Markdown-Ausgabe zusammen mit `--toc` atomar in dieselbe
Datei zurückgeschrieben. Das funktioniert nur mit einer echten Datei und
nicht zusammen mit `--pager`; der erzeugte TOC-Bereich wird markiert und bei
weiteren Aufrufen ersetzt. Mit einem eigenen Marker-Paar kann die Position
vorgegeben werden, etwa nach einer Markdown-Navigation. Es werden nur die
Überschriften nach dem End-Marker in den TOC aufgenommen. Dieses
Marker-Paar wird bei jeder `--toc`-Ausgabe beachtet:

```markdown
<!-- mdman:toc:start -->
<!-- mdman:toc:end -->
```

### LaTeX-Formeln im Terminal

Die Terminalvorschau wandelt LaTeX mit dem eingebetteten Parser aus
pylatexenc 3.0b2 in lesbaren Unicode-Text um. Damit werden unter
anderem mathematische Symbole, griechische Buchstaben, Brüche, Wurzeln,
Summen, Integrale, Indizes und Matrizen dargestellt. Brüche erscheinen
linear mit passenden Klammern, zum Beispiel `\frac{a+b}{c}` als `(a + b)/c`.

```latex
\[ P(H\mid D) \propto P(D\mid H)\cdot P(H) \]
```

Das ergibt `P(H|D) ∝ P(D|H) · P(H)`.

Zusätzliche Symbolnamen wie `\iff`, `\implies` und `\impliedby`
stammen aus der Symboltabelle von [UnicodeIt](https://github.com/svenkreiss/unicodeit).
Auch mehrzeilige Formeln werden umgewandelt, beispielsweise
`h\sim h' \iff P(F\mid h)=P(F\mid h')` zu
`h ∼ h' ⇔ P(F|h) = P(F|h')`.
Quellen und Lizenztexte zu pylatexenc sind bei den
[eingebetteten Dateien](src/mdman/_vendor/README.md) dokumentiert.

[mdit-py-plugins](https://mdit-py-plugins.readthedocs.io/) erkennt
Formelblöcke mit `\[ … \]` oder `$$ … $$` und Inline-Formeln mit
`\( … \)` oder `$…$`. Mehrere Formelblöcke können direkt aufeinanderfolgen.
Für `\boxed{…}` wird zusätzlich die Schreibweise `[ … ]` erkannt.
Ein Inline-Rahmen erscheint als `⟦…⟧`.
Eine `minipage` innerhalb eines Formelblocks rendert ihren Text und ihre
Formeln innerhalb der verfügbaren Terminalbreite. Die LaTeX-Angaben für
Breite, Höhe und Ausrichtung entfallen dabei.

Hebräischer Text in `\text{…}` nutzt die vorhandene RTL-Darstellung:

```latex
\[
\boxed{ \text{מבנה סמנטי ב-}C \leftrightarrow \text{חוויה/רעיון}
        \leftrightarrow \text{המשך הדינמיקה של }C. }
\]
```

Im interaktiven Terminal erhalten hebräische Rahmen wie die JSONL-Felder
nur horizontale Begrenzungen, damit die Terminal-Leserichtung die
seitlichen Linien nicht verschiebt.

Unicode liefert eine Textannäherung und keinen vollständigen LaTeX-Satz.
Nicht alle Hoch- und Tiefstellungen existieren als Unicode-Zeichen.
Daher bleiben beispielsweise `\mathcal{S}=\{0,1\}^*` als
`𝒮 = {0, 1}^*` und `\mathcal{C}_{phys}` als `𝒞_phys` lesbar erhalten.
Außerhalb von Formelbegrenzungen werden Zeichenfolgen wie `𝒞_phys`
als normaler Markdown-Text behandelt.
Unbekannte Befehle und Umgebungen sowie syntaktisch ungültige Formeln
bleiben als Quelltext sichtbar. Codeblöcke, Inline-Code und
`--format markdown` behalten die ursprüngliche Schreibweise. Die
Formeldarstellung gilt für die Terminalvorschau einschließlich
Markdown-Feldern in JSONL.

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
Die Terminalvorschau zeigt hebräische Textwerte eingerückt unter dem
Feldnamen. Der Absatz selbst bestimmt seine Leserichtung.
Markdown-Felder mit hebräischem Text erhalten in der Terminalvorschau
eine beschriftete obere Linie und eine Abschlusslinie.
Die Terminalvorschau blendet interne Quellenmarker der Form
`<U+E200>cite…<U+E201>` und einzelne Marker von U+E200 bis U+E202 in
Markdown-Text und JSONL-Textfeldern aus. Markdown-Codebeispiele und der
Markdown-Export behalten den Quelltext.

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
