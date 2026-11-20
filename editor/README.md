# mdman Browser-Editor

React-/TypeScript-Anwendung mit Vite für Markdown-Bearbeitung, HTML-Vorschau,
Mermaid und Drucken. Der normale Einstieg aus dem Repo ist `make setup`, danach
`mdman edit DATEI`. Terminal- und JSONL-Funktionen bleiben in der Python-CLI.

## Entwicklung

Node.js ≥ 22.12 und npm werden benötigt. Im `mdman`-Repo:

```bash
npm --prefix editor ci
npm --prefix editor run dev -- --file /absoluter/pfad/zur/datei.md
```

Vite meldet die lokale Adresse; `--open` öffnet zusätzlich den Browser.
`npm --prefix editor run check` prüft TypeScript,
ESLint und Formatierung; `npm --prefix editor test` prüft Verhalten und I/O.
`npm --prefix editor run build` prüft zusätzlich den Frontend-Build.
Für die Browserprüfungen einmal Chromium einrichten und anschließend prüfen:

```bash
npm --prefix editor exec -- playwright install chromium
npm --prefix editor run test:browser
```

Auf einem frischen Linux-System installiert `playwright install --with-deps chromium`
zusätzlich die benötigten Systembibliotheken. Diese Browserprüfung ist ein eigener
Entwicklungsweg und wird vom normalen Setup nicht vorausgesetzt.

Der Build
allein stellt keinen Dateiserver bereit; Dateizugriffe gehören zum Vite-Plugin.

## Aufbau

- `src/App.tsx`: Dokumentwechsel, Bearbeitungsstand und Benutzeraktionen.
- `src/components`: Editor, echte Markdown-Vorschau, Mermaid und Dateibaum.
- `src/fileApi.ts`: HTTP-Zugriffe und Fehler an der Browsergrenze.
- `shared/contracts.ts`: gemeinsame Zod-Verträge für Server und Browser.
- `server/plugin.ts`: HTTP-Grenze und explizit geöffnete Dateibereiche.
- `server/files.ts`, `links.ts`, `tree.ts`, `events.ts`: Dateizugriff, Baumdaten und SSE.
- `bin/serve.mjs`: Vite-Start über die öffentliche JavaScript-API, Loopback-Port
  und Beendigung bei Strg+C. Die Python-CLI erkennt diesen Server über `/api/status`.

Links werden relativ zum aktuellen Dokument aufgelöst. Ein Link darf zu einem
anderen erreichbaren lokalen Markdown-Dokument führen; dafür wird dessen
Dateibereich registriert. Direkte Lese-/Schreibzugriffe bleiben auf den jeweiligen
Bereich begrenzt. Symlinks werden vor der Bereichsprüfung aufgelöst. Der lokale
Server erlaubt bewusst Zugriff auf vom Benutzer gewählte und verlinkte Dateien;
er ist kein Hosting-Dienst für fremde Dokumente. Browseranfragen von anderen
Ursprüngen werden abgelehnt.

Speichern schreibt eine temporäre Datei im Zielordner, prüft den zuletzt geladenen
Inhalt und ersetzt die Datei per Rename. Das erkennt inzwischen gespeicherte
externe Änderungen; es ersetzt keine Dateisperre gegenüber anderen Programmen.

## Herkunft und Entscheidungen

Übernommen aus dem bereitgestellten Checkout `md-print-editor`, Stand
`72ecd9a7f617d294fb40819fa419eb75cee29cde`: Editor-/Preview-/Mermaid-Komponenten,
Druck-CSS und Basis der Vite-/TypeScript-Konfiguration. Die Dateien werden ab
dieser Übernahme in `mdman` gepflegt; zur Laufzeit wird der Referenz-Checkout
nicht benötigt. Im bereitgestellten Checkout war keine Lizenzdatei vorhanden.

Die allgemeinen Regeln aus den Architektur-/Programmier-, Technik- und
README-Leitlinien von `ki-dev` wurden auf dieses Node-Projekt angewandt:
kleine Zuständigkeiten, explizite I/O-Grenzen, ein gemeinsamer Datenvertrag,
sichtbare Fehler und ein gemeinsamer Setup-Weg. Python-spezifische Bibliotheken
und ki-dev-Ablaufmechanik werden nicht übernommen.

Vorbilder und verwendete Bibliotheken:

- [Vites JavaScript-API](https://vite.dev/guide/api-javascript.html) und
  [Plugin-Schnittstelle](https://vite.dev/guide/api-plugin.html) für Server und Middleware.
- [React Arborist](https://github.com/jameskerr/react-arborist) für den Dateibaum,
  Unterordner, Tastatur und Auswahl; keine eigene Bauminteraktion.
- [react-md-editor](https://github.com/uiwjs/react-md-editor) und
  [remark-gfm](https://github.com/remarkjs/remark-gfm) für Bearbeitung und GFM.
