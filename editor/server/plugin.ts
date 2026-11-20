import { promises as fs } from 'node:fs'
import { randomUUID } from 'node:crypto'
import path from 'node:path'
import type { IncomingMessage, ServerResponse } from 'node:http'
import type { Plugin } from 'vite'
import { ZodError } from 'zod'
import { saveRequest, type Workspace } from '../shared/contracts.ts'
import { HttpError, markdownPath, saveMarkdown } from './files.ts'
import { fileEvents } from './events.ts'
import { markdownTree } from './tree.ts'
import { localLink } from './links.ts'

export function markdownFiles(): Plugin {
  return {
    name: 'mdman-files',
    configureServer(server) {
      const workspaces = new Map<string, Workspace>()
      const events = fileEvents(server, workspaces)

      server.middlewares.use('/api', (req, res) => {
        void handleRequest(req, res).catch((error: unknown) => sendError(res, error))
      })

      async function handleRequest(req: IncomingMessage, res: ServerResponse) {
        checkOrigin(req)
        res.setHeader('Cache-Control', 'no-store')
        const url = new URL(req.url!, 'http://localhost')
        if (url.pathname === '/status' && req.method === 'GET') {
          return json(res, { application: 'mdman-editor', protocol: 1 })
        }
        if (url.pathname === '/open' && req.method === 'GET') {
          const requested = url.searchParams.get('path')
          if (!requested || !path.isAbsolute(requested))
            throw new HttpError(400, 'Bitte einen absoluten Dateipfad angeben.')
          const filename = await fs.realpath(requested)
          const selected = await workspaceForFile(filename)
          return json(res, { workspace: selected, file: path.basename(filename), hash: '' })
        }
        const workspace = workspaces.get(url.searchParams.get('workspace') ?? '')
        if (!workspace) throw new HttpError(404, 'Ordner nicht verfügbar. Bitte erneut wählen.')
        if (req.method === 'GET' && url.pathname === '/events') return events(req, res, workspace)
        if (req.method === 'GET' && url.pathname === '/tree')
          return json(res, await markdownTree(workspace.directory))
        if (req.method === 'GET' && url.pathname === '/resolve') {
          const current = await markdownPath(
            workspace.directory,
            url.searchParams.get('name') ?? '',
          )
          const href = url.searchParams.get('href') ?? ''
          const link = localLink(current, href)
          const target = await fs.realpath(link.filename)
          const selected = await workspaceForFile(target, workspace)
          return json(res, {
            workspace: selected,
            file: path.relative(selected.directory, target).split(path.sep).join('/'),
            hash: link.hash,
          })
        }
        if (req.method === 'GET' && url.pathname === '/asset') {
          const current = await markdownPath(
            workspace.directory,
            url.searchParams.get('name') ?? '',
          )
          const href = url.searchParams.get('href') ?? ''
          const target = await fs.realpath(localLink(current, href).filename)
          const types: Record<string, string> = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.avif': 'image/avif',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain; charset=utf-8',
          }
          const type = types[path.extname(target).toLowerCase()]
          res.setHeader('Content-Type', type ?? 'application/octet-stream')
          res.setHeader('X-Content-Type-Options', 'nosniff')
          res.setHeader(
            'Content-Security-Policy',
            "default-src 'none'; style-src 'unsafe-inline'; sandbox",
          )
          if (!type) res.setHeader('Content-Disposition', 'attachment')
          return res.end(await fs.readFile(target))
        }
        if (url.pathname === '/file') {
          const name = url.searchParams.get('name') ?? ''
          if (req.method === 'GET') {
            const filename = await markdownPath(workspace.directory, name)
            res.setHeader('Content-Type', 'text/plain; charset=utf-8')
            return res.end(await fs.readFile(filename, 'utf8'))
          }
          if (req.method === 'PUT') {
            const request = saveRequest.parse(await readJson(req))
            await saveMarkdown(workspace.directory, name, request.content, request.original)
            res.statusCode = 204
            return res.end()
          }
        }
        throw new HttpError(405, 'Diese Anfrage wird nicht unterstützt.')
      }

      async function workspaceForFile(filename: string, preferred?: Workspace): Promise<Workspace> {
        const parent = path.dirname(filename)
        await markdownPath(parent, path.basename(filename))
        server.watcher.add(filename)
        if (preferred) {
          const relative = path.relative(preferred.directory, filename)
          if (
            relative !== '..' &&
            !relative.startsWith(`..${path.sep}`) &&
            !path.isAbsolute(relative)
          )
            return preferred
        }
        const existing = [...workspaces.values()].find((item) => item.directory === parent)
        if (existing) return existing
        const workspace = { id: randomUUID(), directory: parent }
        workspaces.set(workspace.id, workspace)
        return workspace
      }
    },
  }
}

function checkOrigin(req: IncomingMessage) {
  const hostname = new URL(`http://${req.headers.host}`).hostname
  if (!['localhost', '127.0.0.1', '[::1]'].includes(hostname)) {
    throw new HttpError(403, 'Der Editor ist nur über eine lokale Adresse erreichbar.')
  }
  const origin = req.headers.origin
  if (
    req.headers['sec-fetch-site'] === 'cross-site' ||
    (origin && origin !== `http://${req.headers.host}`)
  ) {
    throw new HttpError(403, 'Anfragen sind nur aus dem lokalen Editor erlaubt.')
  }
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = []
  let size = 0
  for await (const chunk of req) {
    size += chunk.length
    if (size > 8 * 1024 * 1024) throw new HttpError(413, 'Die Anfrage überschreitet 8 MiB.')
    chunks.push(Buffer.from(chunk))
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'))
  } catch (error) {
    if (error instanceof SyntaxError) throw new HttpError(400, 'Ungültiges JSON.')
    throw error
  }
}

function json(res: ServerResponse, data: unknown) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.end(JSON.stringify(data))
}

function sendError(res: ServerResponse, error: unknown) {
  let status = 500
  let message = 'Dateizugriff fehlgeschlagen. Details stehen im Serverprotokoll.'
  if (error instanceof HttpError) {
    status = error.status
    message = error.message
  } else if (error instanceof ZodError) {
    status = 400
    message = `Ungültige Anfrage: ${error.issues.map((issue) => issue.path.join('.')).join(', ')}.`
  } else if (error && typeof error === 'object' && 'code' in error) {
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') {
      status = 404
      message = 'Datei oder Ordner nicht gefunden.'
    } else if (error.code === 'EACCES' || error.code === 'EPERM') {
      status = 403
      message = 'Keine Berechtigung für diesen Pfad.'
    }
  }
  if (status === 500) console.error(error)
  res.statusCode = status
  json(res, { error: message })
}
