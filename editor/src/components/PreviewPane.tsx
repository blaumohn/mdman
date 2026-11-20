import MDEditor from '@uiw/react-md-editor'
import remarkGfm from 'remark-gfm'
import MermaidCodeBlock from './MermaidCodeBlock'
import { defaultUrlTransform } from 'react-markdown'
import type { z } from 'zod'
import type { openedFileSchema } from '../../shared/contracts'

interface Props {
  source: string
  opened?: z.infer<typeof openedFileSchema>
  onNavigate?: (href: string) => void
}

function PreviewPane({ source, opened, onNavigate }: Props) {
  function assetUrl(href: string) {
    if (!opened || !isLocal(href)) return href
    return `/api/asset?${new URLSearchParams({ workspace: opened.workspace.id, name: opened.file, href })}`
  }
  return (
    <div className="preview-pane" data-testid="preview-pane">
      <MDEditor.Markdown
        source={source}
        urlTransform={(url) => (url.startsWith('file:') ? url : defaultUrlTransform(url))}
        remarkPlugins={[remarkGfm]}
        components={{
          code: MermaidCodeBlock,
          a: ({ href, children, node: _node, ...props }) => {
            const markdown = href && isLocal(href) && /\.(?:md|markdown)(?:[?#]|$)/i.test(href)
            const navigate = Boolean(markdown && opened && onNavigate)
            return (
              <a
                {...props}
                href={
                  navigate
                    ? `/?${new URLSearchParams({ workspace: opened!.workspace.id, name: opened!.file, link: href! })}`
                    : href
                      ? assetUrl(href)
                      : href
                }
                onClick={
                  navigate
                    ? (event) => {
                        if (
                          event.button !== 0 ||
                          event.ctrlKey ||
                          event.metaKey ||
                          event.shiftKey ||
                          event.altKey
                        )
                          return
                        event.preventDefault()
                        onNavigate!(href!)
                      }
                    : undefined
                }
              >
                {children}
              </a>
            )
          },
          img: ({ src, alt, node: _node, ...props }) => (
            <img {...props} src={src ? assetUrl(src) : src} alt={alt ?? ''} />
          ),
        }}
      />
    </div>
  )
}

export default PreviewPane

function isLocal(href: string) {
  if (href.startsWith('file:')) return true
  return !href.startsWith('#') && !href.startsWith('//') && !/^[a-z][a-z\d+.-]*:/i.test(href)
}
