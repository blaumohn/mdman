import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PreviewPane from '../components/PreviewPane'

vi.mock('mermaid', () => ({ default: { initialize: vi.fn(), render: vi.fn() } }))

const opened = { workspace: { id: 'test', directory: '/docs' }, file: 'README.md', hash: '' }

describe('Echter Markdown-Renderer', () => {
  it('rendert Fußnoten, Tabellen und Aufgabenlisten', () => {
    const { container } = render(
      <PreviewPane
        source={'Text[^note]\n\n[^note]: Beleg\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n- [x] Fertig'}
      />,
    )
    expect(container.querySelector('[data-footnote-ref]')).toHaveTextContent('1')
    expect(container.querySelector('section.footnotes')).toHaveTextContent('Beleg')
    expect(screen.getByRole('table')).toHaveTextContent('A')
    expect(screen.getByRole('checkbox')).toBeChecked()
  })

  it('öffnet lokale Markdown-Links im Editor und erhält Sprungmarken', () => {
    const navigate = vi.fn()
    render(
      <PreviewPane
        source={
          '[Detail](unterordner/a.md#ziel)\n\n[Abschnitt](#hier)\n\n[Web](https://example.com)'
        }
        opened={opened}
        onNavigate={navigate}
      />,
    )
    fireEvent.click(screen.getByText('Detail'))
    expect(navigate).toHaveBeenCalledWith('unterordner/a.md#ziel')
    expect(screen.getByText('Abschnitt')).toHaveAttribute('href', '#hier')
    expect(screen.getByText('Web')).toHaveAttribute('href', 'https://example.com')
    expect(navigate).toHaveBeenCalledTimes(1)
  })

  it('löst Bilder und PDFs relativ zur Quelldatei auf', () => {
    render(
      <PreviewPane source={'![Bild](images/a.png)\n\n[PDF](files/test.pdf)'} opened={opened} />,
    )
    expect(screen.getByAltText('Bild').getAttribute('src')).toContain('href=images%2Fa.png')
    expect(screen.getByText('PDF').getAttribute('href')).toContain('href=files%2Ftest.pdf')
  })
})
