import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

beforeEach(() => {
  vi.resetModules();
  // Each startup uses a fresh real i18next instance, rather than the instance
  // already initialized by the shared component-test setup.
  vi.doMock('i18next', async () => {
    const actual = await vi.importActual<typeof import('i18next')>('i18next');
    return { ...actual, default: actual.createInstance() };
  });
  localStorage.clear();
  sessionStorage.clear();
  document.cookie = 'i18next=; Max-Age=0; path=/';
});

afterEach(() => {
  sessionStorage.clear();
  document.cookie = 'i18next=; Max-Age=0; path=/';
});

describe('product language initialization', () => {
  it.each(['zh-CN', 'vi-VN', 'ru-RU', 'pt-BR'])('defaults fresh %s browsers to English', async (language) => {
    vi.spyOn(navigator, 'language', 'get').mockReturnValue(language);
    vi.spyOn(navigator, 'languages', 'get').mockReturnValue([language]);
    const { default: i18n, i18nReady } = await import('./index');
    expect(i18n.language).toBe('en');
    await i18nReady;
    expect(i18n.t('auth:login')).toBe('Login');
    expect(localStorage.getItem('i18nextLng')).toBe('en');
  });

  it.each([
    ['zh-Hant-TW', 'zh', '登录'],
    ['EN_us', 'en', 'Login'],
    ['vi-VN', 'vi', 'Đăng nhập'],
    ['ru-RU', 'ru', 'Войти'],
  ])('preserves saved %s preferences through initialization and transport', async (saved, language, login) => {
    localStorage.setItem('i18nextLng', saved);
    document.cookie = 'i18next=en; path=/';
    const { default: i18n, i18nReady } = await import('./index');
    // Locale selection is complete before lazy namespaces are ready.
    expect(i18n.language).toBe(language);
    const { withAuth, sseHeaders } = await import('@/api/transport');
    expect(new Headers(withAuth('/projects').headers).get('Accept-Language')).toBe(language);
    expect(new Headers(sseHeaders()).get('Accept-Language')).toBe(language);
    await i18nReady;
    expect(i18n.t('auth:login')).toBe(login);
  });

  it('uses a supported legacy cookie after an unsupported storage value', async () => {
    localStorage.setItem('i18nextLng', 'pt-BR');
    document.cookie = 'i18next=ru-RU; path=/';
    const { default: i18n, i18nReady } = await import('./index');
    await i18nReady;
    expect(i18n.language).toBe('ru');
    expect(i18n.t('auth:login')).toBe('Войти');
  });

  it('preserves a supported legacy session-storage locale', async () => {
    sessionStorage.setItem('i18nextLng', 'vi-VN');
    const { default: i18n, i18nReady } = await import('./index');
    await i18nReady;
    expect(i18n.language).toBe('vi');
    expect(i18n.t('auth:login')).toBe('Đăng nhập');
  });

  it('falls back to English translations and refreshes REST/SSE language after a selection', async () => {
    localStorage.setItem('i18nextLng', 'ru');
    const { default: i18n, i18nReady } = await import('./index');
    await i18nReady;
    i18n.removeResourceBundle('ru', 'auth');
    expect(i18n.t('auth:login')).toBe('Login');

    const { withAuth, sseHeaders } = await import('@/api/transport');
    await i18n.changeLanguage('vi-VN');
    expect(new Headers(withAuth('/projects').headers).get('Accept-Language')).toBe('vi');
    expect(new Headers(sseHeaders()).get('Accept-Language')).toBe('vi');
    await i18n.changeLanguage('pt-BR');
    expect(new Headers(withAuth('/projects').headers).get('Accept-Language')).toBe('en');
    expect(new Headers(sseHeaders()).get('Accept-Language')).toBe('en');
  });
});
