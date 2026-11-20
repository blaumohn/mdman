import { openedFileSchema } from '../shared/contracts'

export async function openFile(filename: string) {
  const response = await request('/open', { path: filename })
  return openedFileSchema.parse(await response.json())
}

export async function resolveLink(workspace: string, name: string, href: string) {
  const response = await request('/resolve', { workspace, name, href })
  return openedFileSchema.parse(await response.json())
}

export async function request(
  endpoint: string,
  params: Record<string, string> = {},
  method = 'GET',
  body?: unknown,
) {
  const response = await fetch(`/api${endpoint}?${new URLSearchParams(params)}`, {
    method,
    ...(body === undefined
      ? {}
      : {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }),
  })
  if (!response.ok) {
    const result: unknown = await response.json()
    if (
      result &&
      typeof result === 'object' &&
      'error' in result &&
      typeof result.error === 'string'
    ) {
      throw new Error(result.error)
    }
    throw new Error(`Anfrage fehlgeschlagen (${response.status}).`)
  }
  return response
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Die Anfrage ist fehlgeschlagen.'
}
