import { promises as fs } from 'node:fs'
import path from 'node:path'
import { isMarkdown } from './files.ts'
import type { FileNode } from '../shared/contracts.ts'

export async function markdownTree(root: string, relative = ''): Promise<FileNode[]> {
  const entries = await fs.readdir(path.join(root, relative), { withFileTypes: true })
  const nodes: FileNode[] = []
  for (const entry of entries) {
    if (entry.name.startsWith('.') || entry.name === 'node_modules') continue
    const id = [relative, entry.name].filter(Boolean).join('/')
    if (entry.isDirectory()) {
      const children = await markdownTree(root, id)
      if (children.length) nodes.push({ id, name: entry.name, children })
    } else if (entry.isFile() && isMarkdown(entry.name)) {
      nodes.push({ id, name: entry.name })
    }
  }
  return nodes.sort(
    (left, right) =>
      Number(Boolean(right.children)) - Number(Boolean(left.children)) ||
      left.name.localeCompare(right.name),
  )
}
