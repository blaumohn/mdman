import { Children, Fragment, useCallback, useEffect, useState, type ReactNode } from 'react'
import mermaid from 'mermaid'

interface Props {
  children?: ReactNode
  className?: string
  node?: MarkdownNode
}

interface MarkdownNode {
  type?: string
  value?: unknown
  children?: MarkdownNode[]
}

interface FailedRender {
  code: string
  message: string
}

mermaid.initialize({
  startOnLoad: false,
})

function MermaidCodeBlock({ children, className, node }: Props) {
  const [container, setContainer] = useState<HTMLElement | null>(null)
  const [failedRender, setFailedRender] = useState<FailedRender | null>(null)
  const isMermaid = /^language-mermaid\b/i.test(className ?? '')
  const code = mermaidSource(node, children)

  useEffect(() => {
    if (!container || !isMermaid || !code) {
      return
    }

    setFailedRender(null)
    return renderMermaidDiagram(container, code, (message) => setFailedRender({ code, message }))
  }, [code, container, isMermaid])

  const refElement = useCallback((node: HTMLElement | null) => {
    setContainer(node)
  }, [])

  if (!isMermaid) {
    return <code className={className}>{children}</code>
  }

  if (failedRender?.code === code) {
    return (
      <Fragment>
        <code className={className}>{children}</code>
        <span className="mermaid-error">{failedRender.message}</span>
      </Fragment>
    )
  }

  return <code className={`${className ?? ''} mermaid-diagram`} ref={refElement} />
}

export default MermaidCodeBlock

function renderMermaidDiagram(
  container: HTMLElement,
  code: string,
  onError: (message: string) => void,
) {
  let isCurrent = true
  const diagramId = randomId()

  container.replaceChildren()
  mermaid
    .render(diagramId, code)
    .then(({ svg, bindFunctions }) => {
      if (!isCurrent) {
        return
      }

      container.innerHTML = svg
      bindFunctions?.(container)
    })
    .catch((error: unknown) => {
      if (isCurrent) {
        onError(errorMessage(error))
      }
    })

  return () => {
    isCurrent = false
  }
}

function errorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return `Mermaid-Fehler: ${error.message}`
  }

  return 'Mermaid-Fehler: Diagramm konnte nicht gerendert werden.'
}

function mermaidSource(node: MarkdownNode | undefined, children: ReactNode) {
  return codeFromMarkdownNode(node) || codeFromReactChildren(children)
}

function codeFromMarkdownNode(node?: MarkdownNode): string {
  return textChildren(node?.children).trim()
}

function textChildren(children?: MarkdownNode[]): string {
  return children?.map(textFromMarkdownNode).join('') ?? ''
}

function textFromMarkdownNode(node: MarkdownNode): string {
  if (node.type === 'text' && typeof node.value === 'string') {
    return node.value
  }

  return textChildren(node.children)
}

function codeFromReactChildren(children: ReactNode) {
  return Children.toArray(children).map(textFromReactChild).join('').trim()
}

function textFromReactChild(child: ReactNode): string {
  if (typeof child === 'string' || typeof child === 'number') {
    return String(child)
  }

  return ''
}

function randomId() {
  return `mermaid-${Math.random().toString(36).slice(2)}`
}
