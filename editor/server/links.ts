import { fileURLToPath, pathToFileURL } from 'node:url'
import { HttpError } from './files.ts'

export function localLink(current: string, href: string) {
  try {
    const link = new URL(href, pathToFileURL(current))
    if (link.protocol !== 'file:') throw new HttpError(400, 'Kein lokaler Dateilink.')
    return { filename: fileURLToPath(link), hash: link.hash }
  } catch (error) {
    if (error instanceof TypeError || error instanceof URIError) {
      throw new HttpError(400, 'Ungültiger lokaler Dateilink.')
    }
    throw error
  }
}
