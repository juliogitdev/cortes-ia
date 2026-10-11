import assert from 'node:assert/strict'
import { chromium } from 'playwright-core'

const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_BROWSER_EXECUTABLE ||
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
})
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const base = process.env.CLIP_PANEL_URL || 'http://127.0.0.1:8501'
  const profiles = await (await page.request.get(`${base}/profiles`)).json()
  const projects = await (await page.request.get(`${base}/projects`)).json()
  await page.goto(base, { waitUntil: 'networkidle' })
  await page.getByRole('heading', { name: 'Escolha um perfil' }).waitFor()
  if (profiles.length) {
    const profile = profiles[0]
    await page.locator('.account-folder-wrap').filter({ hasText: profile.name }).getByRole('button').first().click()
    await page.getByRole('heading', { name: profile.name }).waitFor()
    assert.equal(await page.locator('.project-card').count(),
      projects.filter(item => item.profile_id === profile.profile_id).length)
    await page.getByRole('button', { name: 'Visão geral' }).click()
    assert.equal(await page.locator('.project-row').count(),
      Math.min(4, projects.filter(item => item.profile_id === profile.profile_id).length))
    await page.locator('.topbar-switch').click()
  }
  await page.getByRole('button', { name: /Lives sem perfil/ }).click()
  await page.getByRole('heading', { name: 'Lives sem perfil' }).waitFor()
  assert.equal(await page.locator('.project-card').count(), projects.filter(item => !item.profile_id).length)
  assert.deepEqual(errors, [])
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
  mobile.on('pageerror', error => errors.push(error.message))
  await mobile.goto(base, { waitUntil: 'networkidle' })
  await mobile.getByRole('button', { name: /Lives sem perfil/ }).click()
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
    'O espaço do perfil não deve ter rolagem horizontal no celular')
  await mobile.locator('.topbar-switch').click()
  await mobile.getByRole('heading', { name: 'Escolha um perfil' }).waitFor()
  assert.deepEqual(errors, [])
  console.log('Perfil isolado, troca explícita e lives sem perfil: OK')
} finally {
  await browser.close()
}
