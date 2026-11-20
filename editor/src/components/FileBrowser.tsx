import { useEffect, useState } from 'react'
import { Tree } from 'react-arborist'
import { treeSchema, type FileNode, type Workspace } from '../../shared/contracts'
import { request, errorMessage } from '../fileApi'

interface Props {
  workspace: Workspace
  onSelect: (filename: string) => void
  onClose: () => void
}

export default function FileBrowser({ workspace, onSelect, onClose }: Props) {
  const [data, setData] = useState<FileNode[]>([])
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let active = true
    request('/tree', { workspace: workspace.id })
      .then(async (res) => {
        const nodes = treeSchema.parse(await res.json())
        if (active) {
          setData(nodes)
          setError('')
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(errorMessage(reason))
      })
    return () => {
      active = false
    }
  }, [workspace.id, revision])

  return (
    <aside className="file-browser" aria-label="Markdown-Dateien">
      <div>
        <strong>Dateien</strong>{' '}
        <button onClick={() => setRevision((value) => value + 1)}>Aktualisieren</button>{' '}
        <button onClick={onClose}>Schließen</button>
      </div>
      <p>{workspace.directory}</p>
      {error && <p role="alert">{error}</p>}
      <Tree
        data={data}
        width={290}
        height={450}
        rowHeight={28}
        openByDefault={false}
        disableDrag
        disableDrop
        disableEdit
        disableMultiSelection
        onActivate={(node) => {
          if (node.isLeaf) onSelect(`${workspace.directory}/${node.id}`)
        }}
      >
        {({ node, style }) => (
          <div
            style={style}
            onClick={() => {
              if (node.isInternal) node.toggle()
            }}
          >
            {node.isInternal ? (node.isOpen ? '▾ ' : '▸ ') : '  '}
            {node.data.name}
          </div>
        )}
      </Tree>
    </aside>
  )
}
