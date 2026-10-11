import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright-core'

const browserPath = process.env.PLAYWRIGHT_BROWSER_EXECUTABLE ||
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const base = process.env.CLIP_PANEL_URL || 'http://127.0.0.1:8501'
const output = resolve('../runtime/diagnostics')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ executablePath: browserPath, headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(base, { waitUntil: 'networkidle' })
  assert.match(await page.title(), /Cortes IA/)
  await page.getByRole('button', { name: 'Estúdio de cortes' }).click()
  await page.getByText('Cortes sugeridos').waitFor({ timeout: 15000 })
  const clips = await page.locator('.clip-card').count()
  assert.ok(clips > 0, 'A análise local deve apresentar cortes')
  const poster = await page.locator('.clip-card video').first().getAttribute('poster')
  assert.ok(poster?.includes('/thumbnail'))
  const image = await page.request.get(new URL(poster, base).toString())
  assert.equal(image.status(), 200)
  assert.match(image.headers()['content-type'], /image\/jpeg/)
  await page.screenshot({ path: resolve(output, 'frontend-desktop.png'), fullPage: true })
  await page.getByRole('button', { name: 'Ver detalhes' }).first().click()
  await page.getByText('Por que foi sugerido').waitFor()
  await page.getByRole('button', { name: 'Fechar detalhes' }).click()
  await page.getByRole('button', { name: 'Projetos', exact: true }).click()
  await page.getByRole('button', { name: 'Renomear' }).first().click()
  await page.getByRole('button', { name: 'Cancelar' }).click()
  assert.deepEqual(errors, [])

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
  mobile.on('pageerror', error => errors.push(error.message))
  await mobile.goto(base, { waitUntil: 'networkidle' })
  await mobile.getByRole('button', { name: 'Abrir menu' }).click()
  await mobile.getByRole('button', { name: 'Estúdio de cortes' }).click()
  await mobile.getByText('Cortes sugeridos').waitFor({ timeout: 15000 })
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'A tela móvel não deve ter rolagem horizontal')
  await mobile.screenshot({ path: resolve(output, 'frontend-mobile.png'), fullPage: true })
  assert.deepEqual(errors, [])
  console.log(`Frontend OK: ${clips} cortes, desktop e celular, sem erros JavaScript.`)
} finally {
  await browser.close()
}
