import assert from 'node:assert/strict'
import { chromium } from 'playwright-core'

const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_BROWSER_EXECUTABLE ||
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
})
try {
  const base = process.env.CLIP_PANEL_URL || 'http://127.0.0.1:8501'
  const projects = await (await browser.newPage()).request.get(`${base}/projects`).then(response => response.json())
  const project = projects.find(item => item.asset_id && item.profile_id)
  assert.ok(project, 'Uma live com mídia e perfil é necessária para testar o formulário')
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(base, { waitUntil: 'networkidle' })
    const profile = await (await page.request.get(`${base}/profiles`)).json()
    const selected = profile.find(item => item.profile_id === project.profile_id)
    await page.locator('.account-folder-wrap').filter({ hasText: selected.name }).getByRole('button').first().click()
    await page.locator('.project-card').filter({ hasText: project.name }).getByRole('button', { name: 'Abrir live' }).click()
    await page.getByRole('button', { name: 'Nova análise' }).click()
    const dialog = page.getByRole('dialog', { name: 'Nova análise' })
    await dialog.getByRole('tab', { name: /Legendas/ }).click()
    assert.equal(await dialog.getByLabel('Legendas no vídeo').isChecked(), true)
    assert.equal(await dialog.getByLabel('Posição da legenda').inputValue(), 'bottom')
    await dialog.getByLabel('Cor da palavra ativa').fill('#00ff00')
    assert.equal(await dialog.locator('.subtitle-preview .active-word').evaluate(element =>
      getComputedStyle(element).color), 'rgb(0, 255, 0)')
    await dialog.getByLabel('Tamanho do texto').fill('1.3')
    assert.equal(await dialog.locator('.subtitle-preview-text').evaluate(element =>
      getComputedStyle(element).fontSize), '25px')
    assert.ok(await dialog.getByText('Prévia do estilo').isVisible())
    const modalBounds = await dialog.boundingBox()
    assert.ok(modalBounds && modalBounds.x >= 0 && modalBounds.x + modalBounds.width <= width + 1,
      `O formulário de legendas não cabe na viewport de ${width}px`)
    await dialog.screenshot({ path: `../runtime/subtitle-settings-${width}.png` })
    await dialog.getByRole('button', { name: 'Fechar' }).click()
    if (await page.locator('.clip-card').count()) {
      await page.locator('.clip-card').first().getByRole('button', { name: 'Ver detalhes' }).click()
      const details = page.getByRole('dialog', { name: 'Revise esta sugestão' })
      await details.getByRole('heading', { name: 'Legendas no vídeo' }).waitFor()
      await details.getByRole('button', { name: 'Ativar legendas neste corte' }).waitFor()
    }
    assert.deepEqual(errors, [])
    await page.close()
  }
  console.log('Configuração de legendas desktop/móvel: OK')
} finally {
  await browser.close()
}
