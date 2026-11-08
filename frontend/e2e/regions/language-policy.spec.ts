import { RECORDED_ACCESS_TOKEN } from '../support/recorded.ts';
import { expect, test } from '../support/test.ts';

test.use({ savedLanguage: null });

for (const browserLanguage of ['zh-CN', 'vi-VN', 'ru-RU', 'pt-BR']) {
  test.describe(`fresh ${browserLanguage} browser`, () => {
    test.use({ locale: browserLanguage });

    test('loads English metadata and UI and sends English login requests', async ({ page, api }) => {
      api.override({ 'POST /api/v1/auth/token': { status: 401, body: { detail: 'Invalid credentials' } } });
      await page.goto('/login?lng=zh');
      await expect(page.getByRole('button', { name: 'Login', exact: true })).toBeVisible();
      await expect(page.locator('html')).toHaveAttribute('lang', 'en');
      await expect(page).toHaveTitle('RafaCena · Agent-powered AI video creation workspace');
      await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', 'An AI video creation workspace for projects, scripts, storyboards, video generation and Agent conversations.');
      await page.getByLabel('Username', { exact: true }).fill('disposable');
      await page.getByLabel('Password', { exact: true }).fill('invalid');
      const request = page.waitForRequest('**/api/v1/auth/token');
      await page.getByRole('button', { name: 'Login', exact: true }).click();
      expect((await request).headers()['accept-language']).toBe('en');
      await expect(page.getByRole('alert')).toHaveText('Invalid credentials');
    });
  });
}

for (const [saved, language, login] of [
  ['zh-Hant-TW', 'zh', '登录'],
  ['en-US', 'en', 'Login'],
  ['vi-VN', 'vi', 'Đăng nhập'],
  ['ru-RU', 'ru', 'Войти'],
] as const) {
  test(`retains saved ${saved} with normalized document language`, async ({ page }) => {
    await page.addInitScript((value) => localStorage.setItem('i18nextLng', value), saved);
    await page.goto('/login');
    await expect(page.getByRole('button', { name: login, exact: true })).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('lang', language);
  });
}

for (const source of ['cookie', 'sessionStorage']) {
  test(`retains a supported ${source} preference after unsupported local storage`, async ({ page }) => {
    await page.addInitScript((storage) => {
      localStorage.setItem('i18nextLng', 'pt-BR');
      if (storage === 'cookie') document.cookie = 'i18next=ru-RU; path=/';
      else sessionStorage.setItem('i18nextLng', 'ru-RU');
    }, source);
    await page.goto('/login');
    await expect(page.getByRole('button', { name: 'Войти', exact: true })).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  });
}

test('updates document language and persisted preference after an explicit UI selection', async ({ page }) => {
  await page.addInitScript((token) => localStorage.setItem('arcreel_auth_token', token), RECORDED_ACCESS_TOKEN);
  await page.goto('/app/settings?section=general');
  const language = page.getByRole('combobox', { name: 'Interface language', exact: true });
  await language.click();
  await page.getByRole('option', { name: 'Русский', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await expect(page.getByRole('combobox', { name: 'Язык интерфейса', exact: true })).toContainText('Русский');
  expect(await page.evaluate(() => localStorage.getItem('i18nextLng'))).toBe('ru');
  await page.reload();
  await expect(page.getByRole('combobox', { name: 'Язык интерфейса', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
});
