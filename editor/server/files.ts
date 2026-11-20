import { promises as fs } from 'node:fs'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

export class HttpError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function isMarkdown(filename: string): boolean {
  return /\.(md|markdown)$/i.test(filename)
}

export async function resolveInside(root: string, name: string): Promise<string> {
  const target = await fs.realpath(path.resolve(root, name))
  const relative = path.relative(root, target)
  if (relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new HttpError(403, 'Der Pfad liegt außerhalb des gewählten Ordners.')
  }
  return target
}

export async function markdownPath(root: string, name: string): Promise<string> {
  if (!isMarkdown(name)) throw new HttpError(400, 'Bitte eine Markdown-Datei wählen.')
  const target = await resolveInside(root, name)
  if (!(await fs.stat(target)).isFile()) throw new HttpError(400, 'Der Pfad ist keine Datei.')
  return target
}

export async function saveMarkdown(root: string, name: string, content: string, original: string) {
  const target = await markdownPath(root, name)
  const temporary = path.join(path.dirname(target), `.mdman-${randomUUID()}.tmp`)
  try {
    const metadata = await fs.stat(target)
    await fs.writeFile(temporary, content, { flag: 'wx', mode: metadata.mode & 0o777 })
    if ((await fs.readFile(target, 'utf8')) !== original) {
      throw new HttpError(
        409,
        'Extern geändert. Vor dem Speichern neu laden und Änderungen abgleichen.',
      )
    }
    await fs.chmod(temporary, metadata.mode & 0o777)
    await fs.rename(temporary, target)
  } finally {
    await fs.rm(temporary, { force: true })
  }
}
