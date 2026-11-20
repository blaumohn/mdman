import { vi } from 'vitest'
import React from 'react'

function MockEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return React.createElement('textarea', {
    'data-testid': 'mock-editor-textarea',
    value,
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => onChange(e.target.value),
  })
}

function MockMarkdown({ source, remarkPlugins }: { source: string; remarkPlugins?: unknown[] }) {
  return React.createElement(
    'div',
    {
      'data-testid': 'mock-markdown-preview',
      'data-remark-plugins': remarkPlugins?.length ? 'gfm' : undefined,
    },
    source,
  )
}

MockEditor.Markdown = MockMarkdown

vi.mock('@uiw/react-md-editor', () => ({
  default: MockEditor,
}))
