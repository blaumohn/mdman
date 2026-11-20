import { test, expect } from '@playwright/test'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import os from 'node:os'

let directory: string

test.beforeAll(async () => {
  directory = await fs.mkdtemp(path.join(os.tmpdir(), 'mdman-browser-'))
  await fs.mkdir(path.join(directory, 'docs'))
  await fs.writeFile(
    path.join(directory, 'README.md'),
    '# Einstieg\n\n[Anleitung](docs/mit%20platz.md#ziel)\n\nText[^beleg]\n\n[^beleg]: Fußnotentext',
  )
  await fs.writeFile(
    path.join(directory, 'docs/mit platz.md'),
    '# Ziel\n\n[Zurück](../README.md)\n\n![Bild](bild.svg)',
  )
  await fs.writeFile(
    path.join(directory, 'docs/bild.svg'),
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>',
  )
})

test.afterAll(async () => {
  await fs.rm(directory, { recursive: true, force: true })
})

test('folgt Dokumentlinks, Sprungmarken und Browser-History ohne Neustart', async ({ page }) => {
  await page.goto(`/?${new URLSearchParams({ file: path.join(directory, 'README.md') })}`)
  await expect(page.getByRole('heading', { name: 'Einstieg', exact: true })).toBeVisible()
  await expect(page.locator('[data-footnote-ref]')).toHaveText('1')
  await page.getByRole('link', { name: 'Anleitung', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Ziel', exact: true })).toBeVisible()
  await expect(page).toHaveURL(/#ziel$/)
  await expect(page.getByRole('img', { name: 'Bild' })).toBeVisible()
  expect(
    await page
      .getByRole('img', { name: 'Bild' })
      .evaluate((img: HTMLImageElement) => img.naturalWidth),
  ).toBe(10)
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Einstieg', exact: true })).toBeVisible()
  await page.goForward()
  await expect(page.getByRole('heading', { name: 'Ziel', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Zurück', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Einstieg', exact: true })).toBeVisible()
})

test('öffnet Unterordner über den Bibliotheks-Dateibaum', async ({ page }) => {
  await page.goto(`/?${new URLSearchParams({ file: path.join(directory, 'README.md') })}`)
  await expect(page.getByRole('heading', { name: 'Einstieg', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Dateien', exact: true }).click()
  await expect(page.getByRole('tree')).toBeVisible()
  await page.getByRole('treeitem', { name: /docs/ }).click()
  await page.getByRole('treeitem', { name: /mit platz\.md/ }).dblclick()
  await expect(page.getByRole('heading', { name: 'Ziel', exact: true })).toBeVisible()
})

test('schützt ungespeicherte Änderungen und speichert die Quelldatei', async ({ page }) => {
  await page.goto(`/?${new URLSearchParams({ file: path.join(directory, 'README.md') })}`)
  await expect(page.getByRole('heading', { name: 'Einstieg', exact: true })).toBeVisible()
  const textarea = page.locator('textarea')
  await textarea.fill('# Bearbeitet\n\n[Anleitung](docs/mit%20platz.md)')
  page.once('dialog', (dialog) => dialog.dismiss())
  await page.getByRole('link', { name: 'Anleitung', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Bearbeitet', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Speichern', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Speichern', exact: true })).toBeDisabled()
  expect(await fs.readFile(path.join(directory, 'README.md'), 'utf8')).toContain('# Bearbeitet')
})

test('übernimmt externe Änderungen und erhält ungespeicherte Eingaben', async ({ page }) => {
  const filename = path.join(directory, 'extern.md')
  await fs.writeFile(filename, '# Anfang')
  await page.goto(`/?${new URLSearchParams({ file: filename })}`)
  await expect(page.getByRole('heading', { name: 'Anfang', exact: true })).toBeVisible()
  await fs.writeFile(filename, '# Extern')
  await expect(page.getByRole('heading', { name: 'Extern', exact: true })).toBeVisible()
  await page.locator('textarea').fill('# Lokal')
  await fs.writeFile(filename, '# Zweite Änderung')
  await expect(page.getByRole('status')).toContainText('Extern geändert')
  await expect(page.locator('textarea')).toHaveValue('# Lokal')
  await page.getByRole('button', { name: 'Speichern', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Extern geändert')
  expect(await fs.readFile(filename, 'utf8')).toBe('# Zweite Änderung')
})

test('rendert Mermaid als SVG', async ({ page }) => {
  const filename = path.join(directory, 'diagram.md')
  await fs.writeFile(filename, '# Diagramm\n\n```mermaid\ngraph TD\n  A[Anfang] --> B[Ende]\n```')
  await page.goto(`/?${new URLSearchParams({ file: filename })}`)
  await expect(page.locator('.mermaid-diagram svg')).toBeVisible()
})
