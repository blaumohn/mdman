import './setup-mocks'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import PreviewPane from '../components/PreviewPane'

describe('PreviewPane', () => {
  it('gibt den Markdown-Quelltext an die Vorschau weiter', () => {
    render(<PreviewPane source="# Hallo" />)
    expect(screen.getByTestId('mock-markdown-preview')).toHaveTextContent('# Hallo')
  })

  it('ist im DOM als preview-pane markiert', () => {
    render(<PreviewPane source="" />)
    expect(screen.getByTestId('preview-pane')).toBeInTheDocument()
  })

  it('aktualisiert die Anzeige bei neuem source-Wert', () => {
    const { rerender } = render(<PreviewPane source="alt" />)
    rerender(<PreviewPane source="neu" />)
    expect(screen.getByTestId('mock-markdown-preview')).toHaveTextContent('neu')
  })

  it('übergibt GFM-Unterstützung für Tabellen an die Markdown-Vorschau', () => {
    render(
      <PreviewPane
        source={`### 3.2 Nicht-Ziele

| Nicht-Ziel | Folge |
|---|---|
| Scrum vollständig vorschreiben. | Keine Pflicht. |`}
      />,
    )

    expect(screen.getByTestId('mock-markdown-preview')).toHaveAttribute(
      'data-remark-plugins',
      'gfm',
    )
  })
})
