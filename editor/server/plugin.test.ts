// @vitest-environment node
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { createServer, type ViteDevServer } from 'vite'
import { markdownFiles } from './plugin.ts'
import { pathToFileURL } from 'node:url'
import { openedFileSchema, treeSchema } from '../shared/contracts.ts'

let server: ViteDevServer
let root: string
let base: string
let workspace: string

beforeAll(async () => {
  root = await fs.mkdtemp(path.join(os.tmpdir(), 'mdman-api-'))
  await fs.mkdir(path.join(root, 'docs'))
  await fs.writeFile(path.join(root, 'README.md'), '[Detail](docs/mit platz.md#ziel)')
  await fs.writeFile(path.join(root, 'docs/mit platz.md'), '# Ziel\n')
  await fs.writeFile(
    path.join(root, 'docs/picture.svg'),
    '<svg xmlns="http://www.w3.org/2000/svg"/>',
  )
  await fs.symlink(path.join(root, 'README.md'), path.join(root, 'docs/outside.md'))
  server = await createServer({
    configFile: false,
    root,
    plugins: [markdownFiles()],
    server: { host: '127.0.0.1', port: 0 },
  })
  await server.listen()
  const address = server.httpServer!.address()
  if (!address || typeof address === 'string') throw new Error('Kein HTTP-Port')
  base = `http://127.0.0.1:${address.port}`
  const response = await api('/open', { path: path.join(root, 'README.md') })
  workspace = openedFileSchema.parse(await response.json()).workspace.id
})

afterAll(async () => {
  await server?.close()
  await fs.rm(root, { recursive: true, force: true })
})

function api(endpoint: string, params: Record<string, string> = {}, options?: RequestInit) {
  return fetch(`${base}/api${endpoint}?${new URLSearchParams(params)}`, options)
}

describe('Lokaler Dateizugriff', () => {
  it('öffnet Markdown aus einem anderen Ordner ohne Serverneustart', async () => {
    const response = await api('/open', { path: path.join(root, 'docs/mit platz.md') })
    const opened = openedFileSchema.parse(await response.json())
    expect(response.status).toBe(200)
    expect(opened.workspace.directory).toBe(path.join(root, 'docs'))
    const content = await api('/file', { workspace: opened.workspace.id, name: opened.file })
    expect(await content.text()).toBe('# Ziel\n')
  })

  it('löst relative Links mit Leerzeichen und Sprungmarke auf', async () => {
    const response = await api('/resolve', {
      workspace,
      name: 'README.md',
      href: 'docs/mit%20platz.md#ziel',
    })
    expect(await response.json()).toEqual({
      workspace: { id: workspace, directory: root },
      file: 'docs/mit platz.md',
      hash: '#ziel',
    })
  })

  it('folgt einem Link zum übergeordneten Ordner', async () => {
    const opened = openedFileSchema.parse(
      await (await api('/open', { path: path.join(root, 'docs/mit platz.md') })).json(),
    )
    const response = await api('/resolve', {
      workspace: opened.workspace.id,
      name: opened.file,
      href: '../README.md',
    })
    expect(openedFileSchema.parse(await response.json()).file).toBe('README.md')
  })

  it('öffnet erreichbare file-URLs und meldet ungültige Kodierung', async () => {
    const response = await api('/resolve', {
      workspace,
      name: 'README.md',
      href: pathToFileURL(path.join(root, 'docs/mit platz.md')).href,
    })
    expect(response.status).toBe(200)
    expect(openedFileSchema.parse(await response.json()).file).toBe('docs/mit platz.md')
    expect((await api('/resolve', { workspace, name: 'README.md', href: '%ZZ.md' })).status).toBe(
      400,
    )
  })

  it('liefert Bilder relativ zur geöffneten Datei', async () => {
    const response = await api('/asset', { workspace, name: 'README.md', href: 'docs/picture.svg' })
    expect(response.headers.get('content-type')).toBe('image/svg+xml')
    expect(await response.text()).toContain('<svg')
  })

  it('stellt einen Dateibaum mit Unterordnern bereit', async () => {
    const response = await api('/tree', { workspace })
    const nodes = treeSchema.parse(await response.json())
    expect(nodes.find((node) => node.name === 'docs')?.children).toEqual([
      { id: 'docs/mit platz.md', name: 'mit platz.md' },
    ])
  })

  it('meldet nicht erreichbare Links und ungeeignete Dateitypen', async () => {
    expect((await api('/resolve', { workspace, name: 'README.md', href: 'fehlt.md' })).status).toBe(
      404,
    )
    expect((await api('/open', { path: path.join(root, 'docs/picture.svg') })).status).toBe(400)
  })

  it('lehnt direkten Dateizugriff außerhalb des gewählten Ordners ab', async () => {
    const opened = openedFileSchema.parse(
      await (await api('/open', { path: path.join(root, 'docs/mit platz.md') })).json(),
    )
    expect(
      (await api('/file', { workspace: opened.workspace.id, name: '../README.md' })).status,
    ).toBe(403)
    expect(
      (await api('/file', { workspace: opened.workspace.id, name: 'outside.md' })).status,
    ).toBe(403)
  })

  it('überschreibt keine erkannte externe Änderung', async () => {
    await fs.writeFile(path.join(root, 'save.md'), 'extern')
    const response = await api(
      '/file',
      { workspace, name: 'save.md' },
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: 'lokal', original: 'alt' }),
      },
    )
    expect(response.status).toBe(409)
    expect(await fs.readFile(path.join(root, 'save.md'), 'utf8')).toBe('extern')
  })

  it('speichert atomar und erhält Dateirechte', async () => {
    await fs.writeFile(path.join(root, 'save.md'), 'alt', { mode: 0o640 })
    await fs.chmod(path.join(root, 'save.md'), 0o640)
    const response = await api(
      '/file',
      { workspace, name: 'save.md' },
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: 'neu', original: 'alt' }),
      },
    )
    expect(response.status).toBe(204)
    expect(await fs.readFile(path.join(root, 'save.md'), 'utf8')).toBe('neu')
    expect((await fs.stat(path.join(root, 'save.md'))).mode & 0o777).toBe(0o640)
    expect((await fs.readdir(root)).filter((name) => name.startsWith('.mdman-'))).toEqual([])
  })

  it('validiert Schreibaufträge und blockiert fremde Browser-Ursprünge', async () => {
    const params = { workspace, name: 'README.md' }
    expect((await api('/file', params, { method: 'PUT', body: '{}' })).status).toBe(400)
    expect(
      (await api('/file', params, { headers: { Origin: 'https://example.com' } })).status,
    ).toBe(403)
  })
})
