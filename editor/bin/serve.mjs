import { parseArgs } from 'node:util'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { createServer } from 'vite'

const { values } = parseArgs({
  allowNegative: true,
  options: {
    port: { type: 'string', default: '5173' },
    file: { type: 'string' },
    open: { type: 'boolean', default: false },
  },
})

const port = Number(values.port)
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error('mdman: Port muss zwischen 1 und 65535 liegen.')
  process.exit(2)
}
if (!values.file) {
  console.error('mdman: Bitte --file mit einer einzelnen Markdown-Datei angeben.')
  process.exit(2)
}
const filename = path.resolve(values.file)
const url = `/?file=${encodeURIComponent(filename)}`
let server
try {
  server = await createServer({
    root: fileURLToPath(new URL('..', import.meta.url)),
    server: { port, open: values.open ? url : false },
  })
  await server.listen()
  console.log(`mdman: http://127.0.0.1:${port}${url}`)
  server.printUrls()
} catch (error) {
  console.error(`mdman: ${error instanceof Error ? error.message : String(error)}`)
  await server?.close()
  process.exit(1)
}
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, async () => {
    await server.close()
    process.exit(0)
  })
}
