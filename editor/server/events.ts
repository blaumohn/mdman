import path from 'node:path'
import type { IncomingMessage, ServerResponse } from 'node:http'
import type { ViteDevServer } from 'vite'
import type { Workspace } from '../shared/contracts.ts'
import { isMarkdown } from './files.ts'

export function fileEvents(server: ViteDevServer, workspaces: Map<string, Workspace>) {
  const clients = new Map<ServerResponse, string>()
  const changed = (filename: string) => {
    if (!isMarkdown(filename)) return
    for (const [response, workspaceId] of clients) {
      const workspace = workspaces.get(workspaceId)!
      const file = path.relative(workspace.directory, filename)
      if (file === '..' || file.startsWith(`..${path.sep}`) || path.isAbsolute(file)) continue
      response.write(
        `event: file-change\ndata: ${JSON.stringify({ file: file.split(path.sep).join('/') })}\n\n`,
      )
    }
  }
  server.watcher.on('add', changed).on('unlink', changed).on('change', changed)
  const heartbeat = setInterval(() => {
    for (const response of clients.keys()) response.write(': heartbeat\n\n')
  }, 30000)
  heartbeat.unref()
  server.httpServer?.once('close', () => {
    clearInterval(heartbeat)
    for (const response of clients.keys()) response.end()
    server.watcher.off('add', changed).off('unlink', changed).off('change', changed)
  })
  return (req: IncomingMessage, res: ServerResponse, workspace: Workspace) => {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    })
    res.write(': connected\n\n')
    clients.set(res, workspace.id)
    req.once('close', () => clients.delete(res))
  }
}
