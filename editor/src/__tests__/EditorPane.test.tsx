import './setup-mocks'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import EditorPane from '../components/EditorPane'

describe('EditorPane', () => {
  it('zeigt den übergebenen Wert an', () => {
    render(<EditorPane value="# Test" onChange={vi.fn()} />)
    expect(screen.getByTestId('mock-editor-textarea')).toHaveValue('# Test')
  })

  it('ruft onChange auf, wenn der Nutzer tippt', async () => {
    const onChange = vi.fn()
    render(<EditorPane value="" onChange={onChange} />)
    await userEvent.type(screen.getByTestId('mock-editor-textarea'), 'Hallo')
    expect(onChange).toHaveBeenCalled()
  })

  it('ist im DOM als editor-pane markiert', () => {
    render(<EditorPane value="" onChange={vi.fn()} />)
    expect(screen.getByTestId('editor-pane')).toBeInTheDocument()
  })
})
