import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { z } from 'zod'
import EditorPane from './components/EditorPane'
import PreviewPane from './components/PreviewPane'
import FileBar, { type ViewMode } from './components/FileBar'
import FileBrowser from './components/FileBrowser'
import { errorMessage, openFile, request, resolveLink } from './fileApi'
import { fileEventSchema, openedFileSchema } from '../shared/contracts'
import './app.css'

type OpenedFile = z.infer<typeof openedFileSchema>
interface Document {
  opened: OpenedFile
  content: string
  saved: string
}

export default function App() {
  const [document, setDocument] = useState<Document | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('split')
  const [externalUpdate, setExternalUpdate] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [browse, setBrowse] = useState(false)
  const documentRef = useRef(document)
  const dirty = document !== null && document.content !== document.saved
  const workspaceId = document?.opened.workspace.id

  useLayoutEffect(() => {
    documentRef.current = document
  }, [document])

  const run = useCallback(async (operation: () => Promise<void>) => {
    setBusy(true)
    setError('')
    try {
      await operation()
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setBusy(false)
    }
  }, [])

  const load = useCallback(async (opened: OpenedFile) => {
    const response = await request('/file', { workspace: opened.workspace.id, name: opened.file })
    const content = await response.text()
    setDocument({ opened, content, saved: content })
    setExternalUpdate(false)
  }, [])

  useEffect(() => {
    let active = true
    const location = new URLSearchParams(window.location.search)
    const filename = location.get('file')
    if (filename || (location.has('workspace') && location.has('name') && location.has('link'))) {
      void run(async () => {
        const opened = filename
          ? await openFile(filename)
          : await resolveLink(
              location.get('workspace')!,
              location.get('name')!,
              location.get('link')!,
            )
        if (active) {
          const target = { ...opened, hash: window.location.hash || opened.hash }
          await load(target)
          history.replaceState(null, '', documentUrl(target))
        }
      })
    }
    return () => {
      active = false
    }
  }, [load, run])

  useEffect(() => {
    const onPopState = () => {
      const current = documentRef.current
      const filename = new URLSearchParams(window.location.search).get('file')
      if (current && filename === `${current.opened.workspace.directory}/${current.opened.file}`) {
        setDocument({ ...current, opened: { ...current.opened, hash: window.location.hash } })
        return
      }
      if (
        current &&
        current.content !== current.saved &&
        !window.confirm('Ungespeicherte Änderungen verwerfen?')
      ) {
        history.pushState(null, '', documentUrl(current.opened))
        return
      }
      if (filename)
        void run(async () => load({ ...(await openFile(filename)), hash: window.location.hash }))
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [load, run])

  const openedDocument = document?.opened
  useEffect(() => {
    if (!openedDocument) return
    window.document.title = `${openedDocument.file} – mdman`
    const anchor = openedDocument.hash.slice(1)
    if (anchor) {
      const frame = requestAnimationFrame(() => {
        window.document.getElementById(decodeURIComponent(anchor))?.scrollIntoView()
      })
      return () => cancelAnimationFrame(frame)
    }
  }, [openedDocument])

  useEffect(() => {
    if (!workspaceId) return
    const events = new EventSource(`/api/events?workspace=${encodeURIComponent(workspaceId)}`)
    events.addEventListener('file-change', (event) => {
      let data: unknown
      try {
        data = JSON.parse(event.data)
      } catch {
        setError('Ungültiges Dateiänderungsereignis.')
        return
      }
      const parsed = fileEventSchema.safeParse(data)
      const snapshot = documentRef.current
      if (!parsed.success || !snapshot || parsed.data.file !== snapshot.opened.file) return
      if (snapshot.content !== snapshot.saved) {
        setExternalUpdate(true)
        return
      }
      void request('/file', { workspace: workspaceId, name: parsed.data.file })
        .then((response) => response.text())
        .then((content) => {
          setDocument((current) =>
            current === snapshot ? { ...current, content, saved: content } : current,
          )
        })
        .catch((reason: unknown) => setError(errorMessage(reason)))
    })
    return () => events.close()
  }, [workspaceId])

  useEffect(() => {
    if (!dirty) return
    const beforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', beforeUnload)
    return () => window.removeEventListener('beforeunload', beforeUnload)
  }, [dirty])

  function discardChanges() {
    return !dirty || window.confirm('Ungespeicherte Änderungen verwerfen?')
  }

  function navigate(href: string) {
    if (!document || busy || !discardChanges()) return
    void run(async () => {
      const opened = await resolveLink(document.opened.workspace.id, document.opened.file, href)
      await load(opened)
      history.pushState(null, '', documentUrl(opened))
    })
  }

  async function save() {
    if (!document) return
    await request(
      '/file',
      { workspace: document.opened.workspace.id, name: document.opened.file },
      'PUT',
      {
        content: document.content,
        original: document.saved,
      },
    )
    setDocument((current) =>
      current && current.opened === document.opened
        ? { ...current, saved: document.content }
        : current,
    )
    setExternalUpdate(false)
  }

  return (
    <div className="app-layout">
      <FileBar
        filename={
          document ? `${document.opened.workspace.directory}/${document.opened.file}` : null
        }
        dirty={dirty}
        busy={busy}
        externalUpdate={externalUpdate}
        viewMode={viewMode}
        onSave={() => {
          void run(save)
        }}
        onReload={() => {
          if (document && discardChanges()) void run(() => load(document.opened))
        }}
        onViewMode={setViewMode}
        onBrowse={() => setBrowse((visible) => !visible)}
      />
      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}
      <div className="pane-layout" aria-busy={busy}>
        {browse && document && (
          <FileBrowser
            workspace={document.opened.workspace}
            onSelect={navigate}
            onClose={() => setBrowse(false)}
          />
        )}
        {viewMode === 'split' && (
          <EditorPane
            value={document?.content ?? ''}
            onChange={(content) =>
              setDocument((current) => (current ? { ...current, content } : null))
            }
          />
        )}
        <PreviewPane
          source={document?.content ?? ''}
          opened={document?.opened}
          onNavigate={navigate}
        />
      </div>
    </div>
  )
}

function documentUrl(opened: OpenedFile) {
  return `/?${new URLSearchParams({ file: `${opened.workspace.directory}/${opened.file}` })}${opened.hash}`
}
