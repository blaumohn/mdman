export type ViewMode = 'split' | 'preview'

interface Props {
  filename: string | null
  dirty: boolean
  busy: boolean
  externalUpdate: boolean
  viewMode: ViewMode
  onSave: () => void
  onReload: () => void
  onViewMode: (mode: ViewMode) => void
  onBrowse: () => void
}

export default function FileBar(props: Props) {
  return (
    <header className="file-bar">
      <button disabled={!props.filename || props.busy} onClick={props.onBrowse}>
        Dateien
      </button>
      <span className="filename">
        {props.filename ?? 'Datei mit mdman edit DATEI öffnen'}
        {props.dirty ? ' · ungespeichert' : ''}
      </span>
      <button disabled={!props.filename || props.busy || !props.dirty} onClick={props.onSave}>
        Speichern
      </button>
      <button disabled={!props.filename || props.busy} onClick={props.onReload}>
        Neu laden
      </button>
      {props.externalUpdate && (
        <span className="external-update" role="status">
          Extern geändert – vor dem Speichern abgleichen.
        </span>
      )}
      <div className="view-toggle">
        <button aria-pressed={props.viewMode === 'split'} onClick={() => props.onViewMode('split')}>
          Geteilt
        </button>
        <button
          aria-pressed={props.viewMode === 'preview'}
          onClick={() => props.onViewMode('preview')}
        >
          Vorschau
        </button>
        <button onClick={() => window.print()}>Drucken</button>
      </div>
    </header>
  )
}
